"""Classify tau2 compiler-lease task-loop recall gaps from saved artifacts.

This analysis is intentionally offline: it reads saved local task-loop prompts
and results only. It does not run models, execute tools, sync datasets, or read
hidden benchmark task files. The goal is to separate residual missing reference
actions into actionable buckets:

* the exact compiler hint was visible but not called;
* the tool and argument evidence were visible but no exact hint was minted;
* the argument evidence was visible but the tool was not exposed;
* the tool was exposed but the argument evidence was not visible; or
* neither tool nor argument evidence appeared in the saved prompts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_RUN_DIR = Path("results/eval/R099")

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "reference_actions",
    "executed_reference_actions",
    "missing_reference_actions",
    "missing_complete_compiler_hint_not_called",
    "missing_tool_visible_arg_evidence_not_called",
    "missing_tool_not_visible_arg_evidence",
    "missing_tool_visible_no_arg_evidence",
    "missing_tool_not_visible_no_arg_evidence",
    "missing_with_complete_compiler_hint",
    "missing_with_tool_visible",
    "missing_with_all_arg_evidence",
    "missing_with_any_arg_evidence",
    "task_gap_category",
    "tool_oracle_pass",
    "all_reference_actions_executed",
    "action_reward",
    "env_reward",
]

MISSING_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "reference_index",
    "event_id",
    "tool",
    "args_json",
    "arg_values",
    "complete_compiler_hint_steps",
    "partial_compiler_hint_steps",
    "tool_visible_steps",
    "all_arg_evidence_steps",
    "any_arg_evidence_steps",
    "task_arg_evidence",
    "missing_arg_values_from_prompt_evidence",
    "gap_class",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze tau2 compiler-lease recall gaps from saved prompts"
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Analysis run id to record in the summary; defaults to the output directory name.",
    )
    parser.add_argument(
        "--residual-dir",
        type=Path,
        default=None,
        help="Optional residual-analysis directory to include in input digests only.",
    )
    parser.add_argument(
        "--adjusted-dir",
        type=Path,
        default=None,
        help="Optional invalid-reference adjusted directory to include in input digests only.",
    )
    args = parser.parse_args()

    run_id = args.run_id or args.output_dir.name
    result = analyze_run(args.run_dir, run_id=run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "task_compiler_recall_gap.csv", result["task_rows"], TASK_FIELDS)
    _write_rows(
        args.output_dir / "missing_compiler_recall_gap.csv",
        result["missing_rows"],
        MISSING_FIELDS,
    )
    (args.output_dir / "tau2_compiler_recall_gap_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    digest_dirs = [args.run_dir]
    if args.residual_dir is not None:
        digest_dirs.append(args.residual_dir)
    if args.adjusted_dir is not None:
        digest_dirs.append(args.adjusted_dir)
    (args.output_dir / "input_digests.csv").write_text(_input_digest_csv(digest_dirs))
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_run(run_dir: Path, *, run_id: str = "R103") -> dict[str, Any]:
    records = _load_jsonl(run_dir / "samples.jsonl")
    source_run_id = _source_run_id(run_dir)
    task_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for record in records:
        task_result = analyze_task_record(source_run_id, record, run_dir=run_dir)
        task_rows.append(task_result["task_row"])
        missing_rows.extend(task_result["missing_rows"])

    summary = _summary(
        run_id=run_id,
        run_dir=run_dir,
        source_run_id=source_run_id,
        task_rows=task_rows,
        missing_rows=missing_rows,
    )
    return {"summary": summary, "task_rows": task_rows, "missing_rows": missing_rows}


def analyze_task_record(
    source_run_id: str,
    record: dict[str, Any],
    *,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    references = list(record.get("reference_actions") or [])
    executed_ids = {
        str(row.get("bound_reference_event_id", ""))
        for row in record.get("action_rows") or []
        if row.get("executed") and row.get("bound_reference_event_id")
    }
    prompt_contexts = _prompt_contexts_from_record(record, run_dir=run_dir)
    missing_rows = [
        _missing_row(source_run_id, record, index, ref, prompt_contexts)
        for index, ref in enumerate(references)
        if str(ref.get("event_id", "")) not in executed_ids
    ]
    gap_counts = Counter(str(row["gap_class"]) for row in missing_rows)
    task_row = dict(record.get("task_row") or {})
    task_summary = {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "reference_actions": len(references),
        "executed_reference_actions": len(references) - len(missing_rows),
        "missing_reference_actions": len(missing_rows),
        "missing_complete_compiler_hint_not_called": gap_counts[
            "complete_compiler_hint_not_called"
        ],
        "missing_tool_visible_arg_evidence_not_called": gap_counts[
            "tool_visible_arg_evidence_not_called"
        ],
        "missing_tool_not_visible_arg_evidence": gap_counts[
            "tool_not_visible_arg_evidence"
        ],
        "missing_tool_visible_no_arg_evidence": gap_counts[
            "tool_visible_no_arg_evidence"
        ],
        "missing_tool_not_visible_no_arg_evidence": gap_counts[
            "tool_not_visible_no_arg_evidence"
        ],
        "missing_with_complete_compiler_hint": sum(
            1 for row in missing_rows if row["complete_compiler_hint_steps"]
        ),
        "missing_with_tool_visible": sum(
            1 for row in missing_rows if row["tool_visible_steps"]
        ),
        "missing_with_all_arg_evidence": sum(
            1
            for row in missing_rows
            if row["all_arg_evidence_steps"] or row["task_arg_evidence"] == "true"
        ),
        "missing_with_any_arg_evidence": sum(
            1
            for row in missing_rows
            if row["any_arg_evidence_steps"] or row["task_arg_evidence"] == "true"
        ),
        "task_gap_category": _task_gap_category(missing_rows),
        "tool_oracle_pass": bool(task_row.get("tool_oracle_pass")),
        "all_reference_actions_executed": bool(task_row.get("all_reference_actions_executed")),
        "action_reward": float(task_row.get("action_reward", 0.0)),
        "env_reward": float(task_row.get("env_reward", 0.0)),
    }
    return {"task_row": task_summary, "missing_rows": missing_rows}


def _missing_row(
    source_run_id: str,
    record: dict[str, Any],
    reference_index: int,
    reference: dict[str, Any],
    prompt_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    tool = str(reference.get("tool", ""))
    args = dict(reference.get("arguments") or {})
    arg_values = _leaf_values(args)
    complete_hint_steps: list[str] = []
    partial_hint_steps: list[str] = []
    tool_visible_steps: list[str] = []
    all_arg_evidence_steps: list[str] = []
    any_arg_evidence_steps: list[str] = []
    task_arg_evidence = False
    prompt_evidence_text = ""

    for context in prompt_contexts:
        step = str(context.get("step", ""))
        available_tools = set(context.get("available_tools") or [])
        if tool in available_tools:
            tool_visible_steps.append(step)

        compiler_hint_match = _compiler_hint_match(
            tool,
            args,
            context.get("compiler_hints") or [],
        )
        if compiler_hint_match == "complete":
            complete_hint_steps.append(step)
        elif compiler_hint_match == "partial":
            partial_hint_steps.append(step)

        evidence_text = str(context.get("previous_gateway_results_text", ""))
        prompt_evidence_text += "\n" + evidence_text
        if _all_values_present(arg_values, evidence_text):
            all_arg_evidence_steps.append(step)
        if _any_values_present(arg_values, evidence_text):
            any_arg_evidence_steps.append(step)
        if _all_values_present(arg_values, str(context.get("task_text", ""))):
            task_arg_evidence = True

    has_all_arg_evidence = bool(all_arg_evidence_steps) or task_arg_evidence
    missing_values = [
        value for value in arg_values if value not in prompt_evidence_text
    ]
    gap_class = _gap_class(
        complete_hint=bool(complete_hint_steps),
        tool_visible=bool(tool_visible_steps),
        all_arg_evidence=has_all_arg_evidence,
    )
    return {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "reference_index": reference_index,
        "event_id": str(reference.get("event_id", "")),
        "tool": tool,
        "args_json": json.dumps(args, sort_keys=True),
        "arg_values": "|".join(arg_values),
        "complete_compiler_hint_steps": "|".join(complete_hint_steps),
        "partial_compiler_hint_steps": "|".join(partial_hint_steps),
        "tool_visible_steps": "|".join(tool_visible_steps),
        "all_arg_evidence_steps": "|".join(all_arg_evidence_steps),
        "any_arg_evidence_steps": "|".join(any_arg_evidence_steps),
        "task_arg_evidence": "true" if task_arg_evidence else "false",
        "missing_arg_values_from_prompt_evidence": "|".join(missing_values),
        "gap_class": gap_class,
    }


def _prompt_contexts_from_record(
    record: dict[str, Any],
    *,
    run_dir: Path | None = None,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    steps = (record.get("stepwise") or {}).get("steps") or []
    for step in steps:
        payload = step.get("prompt_payload")
        if payload is None:
            prompt_path = _resolve_prompt_path(step.get("prompt_path", ""), run_dir)
            payload = _read_prompt_payload(prompt_path) if prompt_path.exists() else {}
        if not isinstance(payload, dict):
            payload = {}
        compiler_hints = payload.get("active_compiler_lease_hints")
        if compiler_hints is None:
            compiler_hints = step.get("compiler_lease_hints") or []
        contexts.append(
            {
                "step": str(step.get("step") or payload.get("step_index") or ""),
                "available_tools": [
                    str(tool.get("name", ""))
                    for tool in payload.get("available_tools") or []
                    if isinstance(tool, dict)
                ],
                "compiler_hints": [
                    hint for hint in compiler_hints if isinstance(hint, dict)
                ],
                "previous_gateway_results_text": json.dumps(
                    payload.get("previous_gateway_results") or [],
                    sort_keys=True,
                    default=str,
                ),
                "task_text": json.dumps(
                    payload.get("task") or {},
                    sort_keys=True,
                    default=str,
                ),
            }
        )
    return contexts


def _resolve_prompt_path(raw_path: Any, run_dir: Path | None) -> Path:
    prompt_path = Path(str(raw_path or ""))
    if not str(raw_path or "") or prompt_path.is_absolute():
        return prompt_path

    candidates = [prompt_path]
    if run_dir is not None:
        candidates.append(run_dir / prompt_path)
        candidates.append(Path.cwd() / prompt_path)
        if len(run_dir.parents) >= 3:
            candidates.append(run_dir.parents[2] / prompt_path)
        if prompt_path.parts[:3] == ("results", "eval", run_dir.name):
            candidates.append(run_dir / Path(*prompt_path.parts[3:]))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return prompt_path


def _read_prompt_payload(prompt_path: Path) -> dict[str, Any]:
    try:
        text = prompt_path.read_text()
    except OSError:
        return {}
    marker = "Input JSON:\n"
    if marker not in text:
        return {}
    payload_text = text.split(marker, 1)[1]
    for end_marker in ("\nOutput JSON only:", "\nOutput JSON:"):
        if end_marker in payload_text:
            payload_text = payload_text.split(end_marker, 1)[0]
            break
    try:
        payload = json.loads(payload_text.strip())
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _compiler_hint_match(tool: str, args: dict[str, Any], hints: list[dict[str, Any]]) -> str:
    partial = False
    for hint in hints:
        if str(hint.get("tool", "")) != tool:
            continue
        hint_args = dict(hint.get("arguments") or {})
        if hint.get("complete_arguments") is True and hint_args == args:
            return "complete"
        if any(key in args and args.get(key) == value for key, value in hint_args.items()):
            partial = True
    return "partial" if partial else "none"


def _gap_class(
    *,
    complete_hint: bool,
    tool_visible: bool,
    all_arg_evidence: bool,
) -> str:
    if complete_hint:
        return "complete_compiler_hint_not_called"
    if tool_visible and all_arg_evidence:
        return "tool_visible_arg_evidence_not_called"
    if (not tool_visible) and all_arg_evidence:
        return "tool_not_visible_arg_evidence"
    if tool_visible:
        return "tool_visible_no_arg_evidence"
    return "tool_not_visible_no_arg_evidence"


def _task_gap_category(missing_rows: list[dict[str, Any]]) -> str:
    if not missing_rows:
        return "no_missing_references"
    priority = [
        "complete_compiler_hint_not_called",
        "tool_visible_arg_evidence_not_called",
        "tool_not_visible_arg_evidence",
        "tool_visible_no_arg_evidence",
        "tool_not_visible_no_arg_evidence",
    ]
    classes = {str(row["gap_class"]) for row in missing_rows}
    for gap_class in priority:
        if gap_class in classes:
            return gap_class
    return "unclassified"


def _leaf_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            values.extend(_leaf_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(_leaf_values(child))
    elif isinstance(value, bool) or value is None:
        return []
    else:
        text = str(value)
        if text:
            values.append(text)
    return values


def _all_values_present(values: list[str], text: str) -> bool:
    if not values:
        return True
    return all(value in text for value in values)


def _any_values_present(values: list[str], text: str) -> bool:
    if not values:
        return True
    return any(value in text for value in values)


def _summary(
    *,
    run_id: str,
    run_dir: Path,
    source_run_id: str,
    task_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    gap_counts = Counter(str(row["gap_class"]) for row in missing_rows)
    task_gap_counts = Counter(str(row["task_gap_category"]) for row in task_rows)
    return {
        "run_id": run_id,
        "analysis": "saved local-Qwen tau2 compiler-lease recall gap classification",
        "source_run": source_run_id,
        "run_dir": str(run_dir),
        "no_dataset_sync": True,
        "tasks": len(task_rows),
        "tool_oracle_pass_tasks": sum(1 for row in task_rows if row["tool_oracle_pass"]),
        "reference_actions": sum(int(row["reference_actions"]) for row in task_rows),
        "executed_reference_actions": sum(
            int(row["executed_reference_actions"]) for row in task_rows
        ),
        "missing_reference_actions": len(missing_rows),
        "missing_gap_class_counts": dict(sorted(gap_counts.items())),
        "task_gap_category_counts": dict(sorted(task_gap_counts.items())),
        "missing_with_complete_compiler_hint": sum(
            1 for row in missing_rows if row["complete_compiler_hint_steps"]
        ),
        "missing_with_tool_visible": sum(
            1 for row in missing_rows if row["tool_visible_steps"]
        ),
        "missing_with_all_arg_evidence": sum(
            1
            for row in missing_rows
            if row["all_arg_evidence_steps"] or row["task_arg_evidence"] == "true"
        ),
        "missing_with_any_arg_evidence": sum(
            1
            for row in missing_rows
            if row["any_arg_evidence_steps"] or row["task_arg_evidence"] == "true"
        ),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            f"This analysis reads existing {source_run_id} local tau2 task-gateway artifacts only.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or inspect hidden benchmark task files.",
            "Argument evidence means the exact reference argument leaf values appeared in saved prompt task text or prior gateway-result previews.",
            "Tool visibility means the saved step prompt exposed the tool under the current active compiler leases.",
            "A complete compiler hint means an active compiler lease yielded the exact tool and arguments as a prompt hint.",
        ],
    }


def _source_run_id(run_dir: Path) -> str:
    for filename in ("task_gateway_summary.json", "tau2_task_gateway_summary.json"):
        path = run_dir / filename
        if path.exists():
            try:
                saved_summary = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            return str(saved_summary.get("run_id") or run_dir.name)
    return run_dir.name


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(paths: list[Path]) -> str:
    rows = ["path,sha256,size_bytes"]
    seen: set[Path] = set()
    for root in paths:
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in files:
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            rows.append(f"{path},{_sha256(path.read_bytes())},{path.stat().st_size}")
    return "\n".join(rows) + "\n"


def _command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
