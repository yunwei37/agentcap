"""Build an E1 saved-online trajectory wrapper comparison.

This script consolidates already executed local-Qwen tau2 task-loop runs into
one paper-facing trajectory matrix. Unlike the saved proposal replay, this
reads task/action trajectories from actual model-environment runs. It still
does not run a model, execute tools, clone repositories, sync datasets, or
inspect hidden benchmark state.
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


DEFAULT_RUN_DIRS = (
    Path("results/eval/R034"),
    Path("results/eval/R036"),
)
DEFAULT_MISMATCH_CSVS = (
    Path("results/eval/R035/model_call_mismatches.csv"),
    Path("results/eval/R038/model_call_mismatches.csv"),
)

CATEGORY_EXACT = "exact_executed"
CATEGORY_SAME_TOOL_WRONG_ARGS = "off_lease_same_tool_wrong_args"
CATEGORY_WRONG_OR_HALLUCINATED_TOOL = "off_lease_wrong_or_hallucinated_tool"
CATEGORY_REPEATED_OR_CONSUMED_EXACT = "off_lease_repeated_or_consumed_exact_args"

RUN_FIELDS = [
    "run_id",
    "trajectory_family",
    "source_run_dir",
    "command_summary",
    "model_family",
    "tool_exposure",
    "task_count",
    "task_ids",
    "model_calls",
    "exact_executed_calls",
    "off_reference_calls",
    "same_tool_wrong_args_calls",
    "wrong_or_hallucinated_tool_calls",
    "repeated_or_consumed_exact_args_calls",
    "gateway_allowed_calls",
    "gateway_blocked_calls",
    "executed_calls",
    "tool_error_calls",
    "off_lease_calls_blocked",
    "tool_oracle_pass_tasks",
    "tool_oracle_pass_rate",
    "all_reference_actions_executed_tasks",
    "action_reward_pass_tasks",
    "env_reward_pass_tasks",
    "mean_tool_schema_count",
    "max_tool_schema_count",
    "trajectory_note",
]

TASK_FIELDS = [
    "run_id",
    "trajectory_family",
    "domain",
    "task_id",
    "tool_exposure",
    "tool_schema_count",
    "model_calls",
    "exact_executed_calls",
    "off_reference_calls",
    "same_tool_wrong_args_calls",
    "wrong_or_hallucinated_tool_calls",
    "gateway_allowed",
    "gateway_blocked",
    "executed_calls",
    "tool_error_calls",
    "bound_reference_calls",
    "all_reference_actions_executed",
    "action_reward",
    "env_reward",
    "tool_oracle_pass",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 saved-online trajectory matrix")
    parser.add_argument("--run-id", default="R208E1T")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-dir",
        dest="run_dirs",
        action="append",
        type=Path,
        default=None,
        help="Saved task-loop run directory; may be repeated.",
    )
    parser.add_argument(
        "--mismatch-csv",
        dest="mismatch_csvs",
        action="append",
        type=Path,
        default=None,
        help="Saved model_call_mismatches.csv path; may be repeated.",
    )
    args = parser.parse_args()

    run_dirs = tuple(args.run_dirs) if args.run_dirs else DEFAULT_RUN_DIRS
    mismatch_csvs = tuple(args.mismatch_csvs) if args.mismatch_csvs else DEFAULT_MISMATCH_CSVS
    result = build_matrix(run_id=args.run_id, run_dirs=run_dirs, mismatch_csvs=mismatch_csvs)
    write_outputs(args.output_dir, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def build_matrix(
    *,
    run_id: str,
    run_dirs: tuple[Path, ...] = DEFAULT_RUN_DIRS,
    mismatch_csvs: tuple[Path, ...] = DEFAULT_MISMATCH_CSVS,
) -> dict[str, Any]:
    mismatch_rows = _read_mismatch_rows(mismatch_csvs)
    mismatch_by_run = _group_mismatches_by_run(mismatch_rows)
    run_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        run_result = _run_rows_from_dir(run_dir, mismatch_by_run.get(run_dir.name, []))
        run_rows.append(run_result["run_row"])
        task_rows.extend(run_result["task_rows"])
    summary = _summary(run_id, run_dirs, mismatch_csvs, run_rows, task_rows)
    inputs = _input_paths(run_dirs, mismatch_csvs)
    return {
        "summary": summary,
        "run_rows": run_rows,
        "task_rows": task_rows,
        "input_digests": [_file_digest(path) for path in inputs],
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "e1_online_trajectory_wrapper_matrix.csv", result["run_rows"], RUN_FIELDS)
    _write_rows(output_dir / "e1_online_trajectory_task_matrix.csv", result["task_rows"], TASK_FIELDS)
    _write_rows(output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "e1_online_trajectory_wrapper_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())


def _run_rows_from_dir(run_dir: Path, mismatch_rows: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = run_dir.name
    tasks = _read_csv(run_dir / "task_results.csv")
    actions = _read_csv(run_dir / "action_results.csv")
    task_keys = [(str(row["domain"]), str(row["task_id"])) for row in tasks]
    mismatch_by_task: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in mismatch_rows:
        mismatch_by_task.setdefault((str(row.get("domain", "")), str(row.get("task_id", ""))), []).append(row)

    task_rows: list[dict[str, Any]] = []
    for task in tasks:
        key = (str(task["domain"]), str(task["task_id"]))
        categories = Counter(str(row.get("category", "")) for row in mismatch_by_task.get(key, []))
        task_rows.append(
            {
                "run_id": run_id,
                "trajectory_family": _trajectory_family(run_id, tasks, run_dir),
                "domain": task["domain"],
                "task_id": task["task_id"],
                "tool_exposure": _tool_exposure(tasks, run_dir),
                "tool_schema_count": task.get("tool_schema_count", ""),
                "model_calls": _int(task.get("model_calls")),
                "exact_executed_calls": categories[CATEGORY_EXACT],
                "off_reference_calls": sum(categories.values()) - categories[CATEGORY_EXACT],
                "same_tool_wrong_args_calls": categories[CATEGORY_SAME_TOOL_WRONG_ARGS],
                "wrong_or_hallucinated_tool_calls": categories[CATEGORY_WRONG_OR_HALLUCINATED_TOOL],
                "gateway_allowed": _int(task.get("gateway_allowed")),
                "gateway_blocked": _int(task.get("gateway_blocked")),
                "executed_calls": _int(task.get("executed_calls")),
                "tool_error_calls": _int(task.get("tool_error_calls")),
                "bound_reference_calls": _int(task.get("bound_reference_calls")),
                "all_reference_actions_executed": _bool(task.get("all_reference_actions_executed")),
                "action_reward": _float(task.get("action_reward")),
                "env_reward": _float(task.get("env_reward")),
                "tool_oracle_pass": _bool(task.get("tool_oracle_pass")),
            }
        )

    categories = Counter(str(row.get("category", "")) for row in mismatch_rows)
    model_calls = len(actions) if actions else sum(_int(row.get("model_calls")) for row in tasks)
    allowed = sum(_bool(row.get("gateway_allowed")) for row in actions)
    blocked = sum(not _bool(row.get("gateway_allowed")) for row in actions)
    executed = sum(_bool(row.get("executed")) for row in actions)
    tool_errors = sum(_bool(row.get("tool_error")) for row in actions)
    schema_counts = [_int(row.get("tool_schema_count")) for row in tasks if str(row.get("tool_schema_count", ""))]
    run_row = {
        "run_id": run_id,
        "trajectory_family": _trajectory_family(run_id, tasks, run_dir),
        "source_run_dir": str(run_dir),
        "command_summary": _command_summary(run_dir / "command.txt"),
        "model_family": _model_family(run_dir / "command.txt"),
        "tool_exposure": _tool_exposure(tasks, run_dir),
        "task_count": len(tasks),
        "task_ids": "|".join(f"{domain}:{task_id}" for domain, task_id in task_keys),
        "model_calls": model_calls,
        "exact_executed_calls": categories[CATEGORY_EXACT],
        "off_reference_calls": sum(categories.values()) - categories[CATEGORY_EXACT],
        "same_tool_wrong_args_calls": categories[CATEGORY_SAME_TOOL_WRONG_ARGS],
        "wrong_or_hallucinated_tool_calls": categories[CATEGORY_WRONG_OR_HALLUCINATED_TOOL],
        "repeated_or_consumed_exact_args_calls": categories[CATEGORY_REPEATED_OR_CONSUMED_EXACT],
        "gateway_allowed_calls": allowed,
        "gateway_blocked_calls": blocked,
        "executed_calls": executed,
        "tool_error_calls": tool_errors,
        "off_lease_calls_blocked": sum(_int(row.get("off_lease_calls_blocked")) for row in tasks),
        "tool_oracle_pass_tasks": sum(_bool(row.get("tool_oracle_pass")) for row in tasks),
        "tool_oracle_pass_rate": _rate(sum(_bool(row.get("tool_oracle_pass")) for row in tasks), len(tasks)),
        "all_reference_actions_executed_tasks": sum(
            _bool(row.get("all_reference_actions_executed")) for row in tasks
        ),
        "action_reward_pass_tasks": sum(_float(row.get("action_reward")) >= 1.0 for row in tasks),
        "env_reward_pass_tasks": sum(_float(row.get("env_reward")) >= 1.0 for row in tasks),
        "mean_tool_schema_count": _mean(schema_counts),
        "max_tool_schema_count": max(schema_counts) if schema_counts else "",
        "trajectory_note": _trajectory_note(run_id, tasks, run_dir),
    }
    return {"run_row": run_row, "task_rows": task_rows}


def _summary(
    run_id: str,
    run_dirs: tuple[Path, ...],
    mismatch_csvs: tuple[Path, ...],
    run_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_family = {str(row["trajectory_family"]): row for row in run_rows}
    all_tools = by_family.get("all_tools_exact_gateway")
    leased = by_family.get("intentcap_leased_tools_exact_gateway")
    deltas: dict[str, Any] = {}
    if all_tools and leased:
        deltas = {
            "leased_minus_all_exact_executed_calls": _int(leased["exact_executed_calls"])
            - _int(all_tools["exact_executed_calls"]),
            "leased_minus_all_wrong_or_hallucinated_tool_calls": _int(
                leased["wrong_or_hallucinated_tool_calls"]
            )
            - _int(all_tools["wrong_or_hallucinated_tool_calls"]),
            "leased_minus_all_gateway_blocked_calls": _int(leased["gateway_blocked_calls"])
            - _int(all_tools["gateway_blocked_calls"]),
            "leased_minus_all_tool_oracle_pass_tasks": _int(leased["tool_oracle_pass_tasks"])
            - _int(all_tools["tool_oracle_pass_tasks"]),
            "leased_minus_all_action_reward_pass_tasks": _int(leased["action_reward_pass_tasks"])
            - _int(all_tools["action_reward_pass_tasks"]),
        }
    return {
        "run_id": run_id,
        "analysis": "E1 saved-online local-Qwen trajectory wrapper comparison",
        "source_runs": [path.name for path in run_dirs],
        "task_count_per_run": {str(row["run_id"]): row["task_count"] for row in run_rows},
        "trajectory_families": [str(row["trajectory_family"]) for row in run_rows],
        "run_rows": len(run_rows),
        "task_rows": len(task_rows),
        "primary_pair_delta": deltas,
        "headline": (
            "Leased IntentCap tool exposure changes saved online model trajectories: it removes "
            "wrong/hallucinated tool proposals in the R034/R036 pair and increases exact executions, "
            "but it does not improve tool-oracle task success in this small fixed slice."
        ),
        "no_dataset_sync": True,
        "not_a_fresh_online_run": True,
        "uses_saved_online_model_trajectories": True,
        "not_benchmark_scale": True,
        "limitations": [
            "This matrix compares saved online local-Qwen trajectories rather than rerunning a fresh model.",
            "The primary R034/R036 pair is a small fixed tau2 slice with exact reference-action leases.",
            "It isolates tool exposure effects on proposals and gateway outcomes, not full non-oracle utility.",
        ],
        "input_digests": [_file_digest(path) for path in _input_paths(run_dirs, mismatch_csvs)],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }


def _input_paths(run_dirs: tuple[Path, ...], mismatch_csvs: tuple[Path, ...]) -> list[Path]:
    paths: list[Path] = []
    for run_dir in run_dirs:
        for name in ("command.txt", "task_gateway_summary.json", "task_results.csv", "action_results.csv"):
            path = run_dir / name
            if path.exists():
                paths.append(path)
    paths.extend(path for path in mismatch_csvs if path.exists())
    return paths


def _read_mismatch_rows(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                copied = dict(row)
                copied["source_file"] = str(path)
                rows.append(copied)
    return rows


def _group_mismatches_by_run(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("run_id", "")), []).append(row)
    return grouped


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _tool_exposure(tasks: list[dict[str, Any]], run_dir: Path) -> str:
    exposures = {str(row.get("tool_exposure", "")) for row in tasks if row.get("tool_exposure")}
    if exposures:
        return "|".join(sorted(exposures))
    command = _command_summary(run_dir / "command.txt")
    return "leased" if "--tool-exposure leased" in command else "all"


def _trajectory_family(run_id: str, tasks: list[dict[str, Any]], run_dir: Path) -> str:
    exposure = _tool_exposure(tasks, run_dir)
    if exposure == "leased":
        return "intentcap_leased_tools_exact_gateway"
    if exposure == "all":
        return "all_tools_exact_gateway"
    return f"{exposure}_trajectory"


def _trajectory_note(run_id: str, tasks: list[dict[str, Any]], run_dir: Path) -> str:
    exposure = _tool_exposure(tasks, run_dir)
    if exposure == "leased":
        return "Actual saved task-loop trajectory with only active leased tools exposed to the model and exact gateway checks."
    if exposure == "all":
        return "Actual saved task-loop trajectory with all task tools exposed to the model and exact gateway checks."
    return "Actual saved task-loop trajectory."


def _command_summary(path: Path) -> str:
    return path.read_text().strip().replace("\n", " ") if path.exists() else ""


def _model_family(path: Path) -> str:
    command = _command_summary(path)
    if "Qwen.Qwen3.6" in command:
        return "qwen3.6-27b-gguf"
    if "qwen" in command.lower():
        return "local-qwen-default"
    return "local-qwen-default"


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mean(values: list[int]) -> float | str:
    return round(sum(values) / len(values), 8) if values else ""


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 8) if denominator else 0.0


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _git_status() -> str:
    try:
        return subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(os.path.basename(sys.executable))
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
