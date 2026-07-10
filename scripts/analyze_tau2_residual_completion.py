"""Analyze residual tau2 task-completion failures after exact gateway binding.

R047 reads saved task-gateway artifacts only. It does not run models, execute
tools, sync datasets, or inspect hidden benchmark task files. The visibility
classification below is based solely on state-grounded argument hints already
saved in each step record.
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


DEFAULT_RUN_DIR = Path("results/eval/R045")

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "reference_actions",
    "model_calls",
    "executed_reference_actions",
    "missing_reference_actions",
    "executed_prefix_actions",
    "missing_complete_visible_actions",
    "missing_partial_visible_actions",
    "missing_hidden_actions",
    "residual_category",
    "tool_oracle_pass",
    "all_reference_actions_executed",
    "exact_sequence_match",
    "action_reward",
    "env_reward",
    "stepwise_single_hint_fallbacks",
    "stepwise_hint_choice_fallbacks",
]

MISSING_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "reference_index",
    "event_id",
    "tool",
    "args_json",
    "visibility",
    "grounded_keys",
    "hidden_keys",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze residual tau2 completion failures")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Analysis run id to record in the summary; defaults to the output directory name.",
    )
    args = parser.parse_args()

    run_id = args.run_id or args.output_dir.name
    result = analyze_run(args.run_dir, run_id=run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "task_residual_completion.csv", result["task_rows"], TASK_FIELDS)
    _write_rows(
        args.output_dir / "missing_reference_actions.csv",
        result["missing_rows"],
        MISSING_FIELDS,
    )
    (args.output_dir / "tau2_residual_completion_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (args.output_dir / "input_digests.csv").write_text(_input_digest_csv(args.run_dir))
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_run(run_dir: Path, *, run_id: str = "R047") -> dict[str, Any]:
    records = _load_jsonl(run_dir / "samples.jsonl")
    saved_summary = (
        json.loads((run_dir / "task_gateway_summary.json").read_text())
        if (run_dir / "task_gateway_summary.json").exists()
        else {}
    )
    source_run_id = str(saved_summary.get("run_id") or run_dir.name)
    task_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for record in records:
        task_result = analyze_task_record(source_run_id, record)
        task_rows.append(task_result["task_row"])
        missing_rows.extend(task_result["missing_rows"])

    summary = _summary(
        run_id=run_id,
        run_dir=run_dir,
        source_run_id=source_run_id,
        saved_summary=saved_summary,
        task_rows=task_rows,
        missing_rows=missing_rows,
    )
    return {"summary": summary, "task_rows": task_rows, "missing_rows": missing_rows}


def analyze_task_record(source_run_id: str, record: dict[str, Any]) -> dict[str, Any]:
    references = list(record.get("reference_actions") or [])
    task_row = dict(record.get("task_row") or {})
    executed_ids = {
        str(row.get("bound_reference_event_id", ""))
        for row in record.get("action_rows") or []
        if row.get("executed") and row.get("bound_reference_event_id")
    }
    executed_refs = [ref for ref in references if str(ref.get("event_id", "")) in executed_ids]
    missing_refs = [
        (index, ref)
        for index, ref in enumerate(references)
        if str(ref.get("event_id", "")) not in executed_ids
    ]
    saved_hints = _saved_state_grounded_hints(record)
    missing_rows = [
        _missing_row(source_run_id, record, index, ref, saved_hints)
        for index, ref in missing_refs
    ]
    visibility_counts = Counter(str(row["visibility"]) for row in missing_rows)
    residual_category = _residual_category(
        task_row=task_row,
        missing_rows=missing_rows,
        executed_prefix_actions=executed_prefix_actions(record, references),
    )
    task_summary = {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "reference_actions": len(references),
        "model_calls": int(task_row.get("model_calls", len(record.get("model_calls") or []))),
        "executed_reference_actions": len(executed_refs),
        "missing_reference_actions": len(missing_refs),
        "executed_prefix_actions": executed_prefix_actions(record, references),
        "missing_complete_visible_actions": visibility_counts["complete_visible"],
        "missing_partial_visible_actions": visibility_counts["partial_visible"],
        "missing_hidden_actions": visibility_counts["hidden"],
        "residual_category": residual_category,
        "tool_oracle_pass": bool(task_row.get("tool_oracle_pass")),
        "all_reference_actions_executed": bool(task_row.get("all_reference_actions_executed")),
        "exact_sequence_match": bool(task_row.get("exact_sequence_match")),
        "action_reward": float(task_row.get("action_reward", 0.0)),
        "env_reward": float(task_row.get("env_reward", 0.0)),
        "stepwise_single_hint_fallbacks": int(task_row.get("stepwise_single_hint_fallbacks", 0)),
        "stepwise_hint_choice_fallbacks": int(task_row.get("stepwise_hint_choice_fallbacks", 0)),
    }
    return {"task_row": task_summary, "missing_rows": missing_rows}


def executed_prefix_actions(record: dict[str, Any], references: list[dict[str, Any]]) -> int:
    model_calls = [
        {
            "tool": str(call.get("tool", "")),
            "arguments": _public_args(dict(call.get("arguments") or {})),
        }
        for call in record.get("model_calls") or []
    ]
    expected = [
        {
            "tool": str(ref.get("tool", "")),
            "arguments": dict(ref.get("arguments") or {}),
        }
        for ref in references
    ]
    count = 0
    for model_call, reference in zip(model_calls, expected, strict=False):
        if model_call != reference:
            break
        count += 1
    return count


def _missing_row(
    source_run_id: str,
    record: dict[str, Any],
    reference_index: int,
    reference: dict[str, Any],
    saved_hints: list[dict[str, Any]],
) -> dict[str, Any]:
    tool = str(reference.get("tool", ""))
    args = dict(reference.get("arguments") or {})
    visibility, grounded_keys = _visibility_from_hints(tool, args, saved_hints)
    hidden_keys = sorted(set(args) - set(grounded_keys))
    return {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "reference_index": reference_index,
        "event_id": str(reference.get("event_id", "")),
        "tool": tool,
        "args_json": json.dumps(args, sort_keys=True),
        "visibility": visibility,
        "grounded_keys": "|".join(grounded_keys),
        "hidden_keys": "|".join(hidden_keys),
    }


def _visibility_from_hints(
    tool: str,
    args: dict[str, Any],
    saved_hints: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    grounded_keys: set[str] = set()
    for hint in saved_hints:
        if str(hint.get("tool", "")) != tool:
            continue
        hint_args = dict(hint.get("arguments") or {})
        matching_keys = {
            key
            for key, value in hint_args.items()
            if key in args and args.get(key) == value
        }
        grounded_keys.update(matching_keys)
        if hint.get("complete_arguments") is True and hint_args == args:
            return "complete_visible", sorted(args)
    if grounded_keys:
        return "partial_visible", sorted(grounded_keys)
    return "hidden", []


def _saved_state_grounded_hints(record: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for step in (record.get("stepwise") or {}).get("steps") or []:
        for hint in step.get("state_grounded_arg_hints") or []:
            if not isinstance(hint, dict):
                continue
            key = (
                str(hint.get("tool", "")),
                json.dumps(dict(hint.get("arguments") or {}), sort_keys=True),
                str(hint.get("complete_arguments")),
            )
            if key in seen:
                continue
            seen.add(key)
            hints.append(dict(hint))
    return hints


def _residual_category(
    *,
    task_row: dict[str, Any],
    missing_rows: list[dict[str, Any]],
    executed_prefix_actions: int,
) -> str:
    if bool(task_row.get("tool_oracle_pass")):
        return "passed"
    if bool(task_row.get("all_reference_actions_executed")):
        return "all_references_executed_but_reward_failed"
    if any(row["visibility"] == "complete_visible" for row in missing_rows):
        return "missing_complete_visible_actions"
    if any(row["visibility"] == "partial_visible" for row in missing_rows):
        return "missing_partial_visible_actions"
    if missing_rows:
        return "missing_hidden_actions"
    if executed_prefix_actions == int(task_row.get("model_calls", 0)):
        return "empty_or_parse_without_missing_reference"
    return "unclassified_failure"


def _summary(
    *,
    run_id: str,
    run_dir: Path,
    source_run_id: str,
    saved_summary: dict[str, Any],
    task_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    residual_counts = Counter(str(row["residual_category"]) for row in task_rows)
    visibility_counts = Counter(str(row["visibility"]) for row in missing_rows)
    failed_rows = [row for row in task_rows if not row["tool_oracle_pass"]]
    return {
        "run_id": run_id,
        "analysis": "saved local-Qwen tau2 residual completion classification",
        "source_run": source_run_id,
        "run_dir": str(run_dir),
        "no_dataset_sync": True,
        "tasks": len(task_rows),
        "failed_tasks": len(failed_rows),
        "tool_oracle_pass_tasks": sum(1 for row in task_rows if row["tool_oracle_pass"]),
        "tool_oracle_pass_rate": (
            sum(1 for row in task_rows if row["tool_oracle_pass"]) / len(task_rows)
            if task_rows
            else 0.0
        ),
        "reference_actions": sum(int(row["reference_actions"]) for row in task_rows),
        "executed_reference_actions": sum(
            int(row["executed_reference_actions"]) for row in task_rows
        ),
        "missing_reference_actions": len(missing_rows),
        "residual_category_counts": dict(sorted(residual_counts.items())),
        "missing_visibility_counts": dict(sorted(visibility_counts.items())),
        "tasks_with_complete_visible_missing_actions": sum(
            1 for row in task_rows if int(row["missing_complete_visible_actions"]) > 0
        ),
        "tasks_with_partial_visible_missing_actions": sum(
            1 for row in task_rows if int(row["missing_partial_visible_actions"]) > 0
        ),
        "tasks_with_all_references_executed_but_reward_failed": residual_counts[
            "all_references_executed_but_reward_failed"
        ],
        "input_task_gateway_summary": saved_summary,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            f"This analysis reads existing {source_run_id} local tau2 task-gateway artifacts only.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or inspect hidden benchmark task files.",
            "Missing-action visibility is inferred only from state-grounded argument hints saved in prior step prompts.",
        ],
    }


def _public_args(args: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in args.items()
        if not str(key).startswith("_intentcap_")
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open() as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(run_dir: Path) -> str:
    lines = ["path,sha256,bytes"]
    for child in (
        run_dir / "samples.jsonl",
        run_dir / "task_gateway_summary.json",
        run_dir / "action_results.csv",
        run_dir / "task_results.csv",
    ):
        lines.append(_digest_line(child))
    return "\n".join(lines) + "\n"


def _digest_line(path: Path) -> str:
    data = path.read_bytes()
    return f"{path},{_sha256(data)},{len(data)}"


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    ) or "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
