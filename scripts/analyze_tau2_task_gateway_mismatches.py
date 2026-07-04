"""Analyze local-Qwen tau2 task-gateway mismatch patterns.

R035 is a saved-result analysis over R031-R034. It does not run models, sync
datasets, or execute tau2 tools. It reads task-gateway samples and classifies
each model-proposed call by how it differs from the per-task reference-action
lease oracle.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_RUN_DIRS = (
    Path("results/eval/R031"),
    Path("results/eval/R032"),
    Path("results/eval/R033"),
    Path("results/eval/R034"),
)

CALL_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "round",
    "index",
    "model_tool",
    "model_args_json",
    "category",
    "arg_distance",
    "arg_missing_keys",
    "arg_extra_keys",
    "arg_wrong_value_keys",
    "closest_reference_event_id",
    "closest_reference_tool",
    "closest_reference_args_json",
    "bound_reference_event_id",
    "gateway_allowed",
    "executed",
    "gateway_reason",
]

TASK_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "reference_actions",
    "model_calls",
    "exact_executed_calls",
    "off_lease_calls",
    "same_tool_wrong_args_calls",
    "wrong_or_hallucinated_tool_calls",
    "repeated_or_consumed_exact_args_calls",
    "all_reference_actions_executed",
    "tool_oracle_pass",
    "first_off_lease_category",
]

RUN_FIELDS = [
    "run_id",
    "tasks",
    "unsupported_tasks",
    "reference_actions",
    "model_calls",
    "exact_executed_calls",
    "off_lease_calls",
    "same_tool_wrong_args_calls",
    "wrong_or_hallucinated_tool_calls",
    "repeated_or_consumed_exact_args_calls",
    "tool_oracle_pass_tasks",
    "tool_oracle_pass_rate",
    "dominant_off_lease_category",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze tau2 task-gateway mismatches")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-dir",
        dest="run_dirs",
        action="append",
        type=Path,
        default=None,
        help="Saved results/eval/Rxxx directory; may be repeated.",
    )
    args = parser.parse_args()

    run_dirs = tuple(args.run_dirs) if args.run_dirs else DEFAULT_RUN_DIRS
    result = analyze_runs(run_dirs)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "model_call_mismatches.csv", result["call_rows"], CALL_FIELDS)
    _write_rows(args.output_dir / "task_mismatch_summary.csv", result["task_rows"], TASK_FIELDS)
    _write_rows(args.output_dir / "run_mismatch_summary.csv", result["run_rows"], RUN_FIELDS)
    (args.output_dir / "tau2_task_gateway_mismatch_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (args.output_dir / "input_digests.csv").write_text(_input_digest_csv(run_dirs))
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_runs(run_dirs: tuple[Path, ...]) -> dict[str, Any]:
    call_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    input_summaries: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        run_id = run_dir.name
        summary_path = run_dir / "task_gateway_summary.json"
        saved_summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        input_summaries.append(saved_summary)
        records = _load_jsonl(run_dir / "samples.jsonl")
        run_call_rows: list[dict[str, Any]] = []
        run_task_rows: list[dict[str, Any]] = []

        for record in records:
            task_result = analyze_task_record(run_id, record)
            run_call_rows.extend(task_result["call_rows"])
            run_task_rows.append(task_result["task_row"])

        call_rows.extend(run_call_rows)
        task_rows.extend(run_task_rows)
        run_rows.append(_run_row(run_id, saved_summary, run_call_rows, run_task_rows))

    summary = _summary(run_rows, call_rows, task_rows, input_summaries, run_dirs)
    return {
        "summary": summary,
        "call_rows": call_rows,
        "task_rows": task_rows,
        "run_rows": run_rows,
    }


def analyze_task_record(run_id: str, record: dict[str, Any]) -> dict[str, Any]:
    references = list(record.get("reference_actions") or [])
    action_rows = list(record.get("action_rows") or [])
    task_row = dict(record.get("task_row") or {})
    call_rows = [
        classify_action_row(run_id=run_id, record=record, action_row=row, references=references)
        for row in action_rows
    ]
    categories = Counter(row["category"] for row in call_rows)
    first_off_lease = next(
        (row["category"] for row in call_rows if row["category"] != "exact_executed"),
        "",
    )
    task_summary = {
        "run_id": run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "reference_actions": len(references),
        "model_calls": len(call_rows),
        "exact_executed_calls": categories["exact_executed"],
        "off_lease_calls": len(call_rows) - categories["exact_executed"],
        "same_tool_wrong_args_calls": categories["off_lease_same_tool_wrong_args"],
        "wrong_or_hallucinated_tool_calls": categories["off_lease_wrong_or_hallucinated_tool"],
        "repeated_or_consumed_exact_args_calls": categories[
            "off_lease_repeated_or_consumed_exact_args"
        ],
        "all_reference_actions_executed": bool(task_row.get("all_reference_actions_executed")),
        "tool_oracle_pass": bool(task_row.get("tool_oracle_pass")),
        "first_off_lease_category": first_off_lease,
    }
    return {"call_rows": call_rows, "task_row": task_summary}


def classify_action_row(
    *,
    run_id: str,
    record: dict[str, Any],
    action_row: dict[str, Any],
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    model_tool = str(action_row.get("model_tool", ""))
    model_args = _json_dict(action_row.get("model_args_json", "{}"))
    bound_event_id = str(action_row.get("bound_reference_event_id", ""))
    gateway_allowed = bool(action_row.get("gateway_allowed"))
    executed = bool(action_row.get("executed"))
    exact_reference = _exact_reference(model_tool, model_args, references)
    same_tool_refs = [ref for ref in references if str(ref.get("tool", "")) == model_tool]
    closest_ref, diff = _closest_reference(model_tool, model_args, references)

    if bound_event_id and gateway_allowed and executed:
        category = "exact_executed"
    elif exact_reference is not None:
        category = "off_lease_repeated_or_consumed_exact_args"
        closest_ref = exact_reference
        diff = _arg_diff(model_args, dict(exact_reference.get("arguments") or {}))
    elif same_tool_refs:
        category = "off_lease_same_tool_wrong_args"
    else:
        category = "off_lease_wrong_or_hallucinated_tool"

    return {
        "run_id": run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "round": str(action_row.get("round", "initial")),
        "index": int(action_row.get("index", 0)),
        "model_tool": model_tool,
        "model_args_json": json.dumps(model_args, sort_keys=True),
        "category": category,
        "arg_distance": diff["distance"],
        "arg_missing_keys": "|".join(diff["missing_keys"]),
        "arg_extra_keys": "|".join(diff["extra_keys"]),
        "arg_wrong_value_keys": "|".join(diff["wrong_value_keys"]),
        "closest_reference_event_id": str((closest_ref or {}).get("event_id", "")),
        "closest_reference_tool": str((closest_ref or {}).get("tool", "")),
        "closest_reference_args_json": json.dumps(
            dict((closest_ref or {}).get("arguments") or {}),
            sort_keys=True,
        ),
        "bound_reference_event_id": bound_event_id,
        "gateway_allowed": gateway_allowed,
        "executed": executed,
        "gateway_reason": str(action_row.get("gateway_reason", "")),
    }


def _run_row(
    run_id: str,
    saved_summary: dict[str, Any],
    call_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    categories = Counter(row["category"] for row in call_rows)
    off_lease = [row for row in call_rows if row["category"] != "exact_executed"]
    off_lease_categories = Counter(row["category"] for row in off_lease)
    dominant = off_lease_categories.most_common(1)[0][0] if off_lease_categories else ""
    return {
        "run_id": run_id,
        "tasks": len(task_rows),
        "unsupported_tasks": int(saved_summary.get("unsupported_tasks", 0)),
        "reference_actions": sum(int(row["reference_actions"]) for row in task_rows),
        "model_calls": len(call_rows),
        "exact_executed_calls": categories["exact_executed"],
        "off_lease_calls": len(off_lease),
        "same_tool_wrong_args_calls": categories["off_lease_same_tool_wrong_args"],
        "wrong_or_hallucinated_tool_calls": categories["off_lease_wrong_or_hallucinated_tool"],
        "repeated_or_consumed_exact_args_calls": categories[
            "off_lease_repeated_or_consumed_exact_args"
        ],
        "tool_oracle_pass_tasks": sum(1 for row in task_rows if row["tool_oracle_pass"]),
        "tool_oracle_pass_rate": (
            sum(1 for row in task_rows if row["tool_oracle_pass"]) / len(task_rows)
            if task_rows
            else 0.0
        ),
        "dominant_off_lease_category": dominant,
    }


def _summary(
    run_rows: list[dict[str, Any]],
    call_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    input_summaries: list[dict[str, Any]],
    run_dirs: tuple[Path, ...],
) -> dict[str, Any]:
    categories = Counter(row["category"] for row in call_rows)
    round_categories: dict[str, Counter[str]] = defaultdict(Counter)
    for row in call_rows:
        round_categories[str(row["round"])][str(row["category"])] += 1
    return {
        "run_id": "R035",
        "analysis": "saved local-Qwen tau2 task-gateway mismatch classification",
        "source_runs": [path.name for path in run_dirs],
        "no_dataset_sync": True,
        "tasks": len(task_rows),
        "model_calls": len(call_rows),
        "reference_actions": sum(int(row["reference_actions"]) for row in task_rows),
        "exact_executed_calls": categories["exact_executed"],
        "off_lease_calls": len(call_rows) - categories["exact_executed"],
        "category_counts": dict(sorted(categories.items())),
        "round_category_counts": {
            round_name: dict(sorted(counter.items()))
            for round_name, counter in sorted(round_categories.items())
        },
        "tool_oracle_pass_tasks": sum(1 for row in task_rows if row["tool_oracle_pass"]),
        "tool_oracle_pass_rate": (
            sum(1 for row in task_rows if row["tool_oracle_pass"]) / len(task_rows)
            if task_rows
            else 0.0
        ),
        "run_rows": run_rows,
        "input_task_gateway_summaries": input_summaries,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This analysis reads existing R031-R034 local tau2 task-gateway artifacts only.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or reveal hidden reference actions to a model.",
            "Mismatch categories compare model-proposed tool calls against the saved per-task reference-action lease oracle.",
        ],
    }


def _exact_reference(
    model_tool: str,
    model_args: dict[str, Any],
    references: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for ref in references:
        if str(ref.get("tool", "")) == model_tool and dict(ref.get("arguments") or {}) == model_args:
            return ref
    return None


def _closest_reference(
    model_tool: str,
    model_args: dict[str, Any],
    references: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    best_ref: dict[str, Any] | None = None
    best_diff = _arg_diff(model_args, {})
    best_score = 10**9
    for ref in references:
        ref_args = dict(ref.get("arguments") or {})
        diff = _arg_diff(model_args, ref_args)
        tool_penalty = 0 if str(ref.get("tool", "")) == model_tool else 100
        score = tool_penalty + int(diff["distance"])
        if score < best_score:
            best_ref = ref
            best_diff = diff
            best_score = score
    return best_ref, best_diff


def _arg_diff(model_args: dict[str, Any], ref_args: dict[str, Any]) -> dict[str, Any]:
    model_keys = set(model_args)
    ref_keys = set(ref_args)
    missing = sorted(ref_keys - model_keys)
    extra = sorted(model_keys - ref_keys)
    wrong = sorted(
        key for key in (model_keys & ref_keys) if model_args.get(key) != ref_args.get(key)
    )
    return {
        "missing_keys": missing,
        "extra_keys": extra,
        "wrong_value_keys": wrong,
        "distance": len(missing) + len(extra) + len(wrong),
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open() as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or not value:
        return {}
    parsed = json.loads(value)
    return dict(parsed) if isinstance(parsed, dict) else {}


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(paths: tuple[Path, ...]) -> str:
    lines = ["path,sha256,bytes"]
    for path in paths:
        for child in (
            path / "samples.jsonl",
            path / "task_gateway_summary.json",
            path / "action_results.csv",
            path / "task_results.csv",
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
