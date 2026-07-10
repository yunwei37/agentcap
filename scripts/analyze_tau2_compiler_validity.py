"""Audit tau2 compiler lease validity from saved local artifacts.

R090 is a saved-result analysis pass. It reads existing tau2 visible-lease
compiler, compiler-gateway replay, and task-loop mismatch artifacts, then emits
reviewer-auditable labels for lease quality and reference-action coverage. It
does not run a model, execute tau2 tools, call reward functions, clone, sync, or
download datasets.
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


DEFAULT_COMPILER_RUNS = (
    Path("results/eval/R074"),
    Path("results/eval/R077"),
)
DEFAULT_REPLAY_RUNS = (
    Path("results/eval/R075"),
    Path("results/eval/R076"),
    Path("results/eval/R078"),
)
DEFAULT_TASK_MISMATCH_RUNS = (
    Path("results/eval/R080"),
)

RUN_FIELDS = [
    "run_id",
    "run_kind",
    "source_run_id",
    "strict_argument_lowering",
    "tasks",
    "reference_actions",
    "lease_rows",
    "active_leases",
    "exact_reference_actions",
    "broad_or_runtime_actions_admitted",
    "broad_or_runtime_actions_blocked",
    "missing_tool_actions",
    "constraint_mismatch_actions",
    "exact_active_leases",
    "broad_or_runtime_active_leases",
    "inactive_broad_or_runtime_leases",
    "invalid_tool_leases",
    "model_calls",
    "exact_executed_calls",
    "off_lease_calls",
    "wrong_or_hallucinated_tool_calls",
    "same_tool_wrong_args_calls",
    "source_path",
]

ACTION_FIELDS = [
    "run_id",
    "source_run_id",
    "strict_argument_lowering",
    "domain",
    "task_id",
    "action_id",
    "index",
    "tool",
    "validity_label",
    "coverage_class",
    "gateway_allowed",
    "missing_reference_arg_constraints",
    "args_json",
    "source_path",
]

LEASE_FIELDS = [
    "run_id",
    "source_run_id",
    "strict_argument_lowering",
    "domain",
    "task_id",
    "lease_id",
    "tool",
    "validity_label",
    "valid_tool",
    "active",
    "inactive_reason",
    "constrained_args",
    "broad_or_runtime_args",
    "argument_policy_json",
    "source_path",
]

TASK_LOOP_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "round",
    "index",
    "model_tool",
    "validity_label",
    "category",
    "arg_distance",
    "arg_missing_keys",
    "arg_extra_keys",
    "arg_wrong_value_keys",
    "gateway_allowed",
    "executed",
    "closest_reference_tool",
    "source_path",
]

DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze saved tau2 compiler lease validity artifacts"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R090")
    parser.add_argument(
        "--compiler-run",
        dest="compiler_runs",
        action="append",
        type=Path,
        default=None,
        help="Saved visible-lease compiler run directory; may be repeated.",
    )
    parser.add_argument(
        "--replay-run",
        dest="replay_runs",
        action="append",
        type=Path,
        default=None,
        help="Saved compiler-gateway replay run directory; may be repeated.",
    )
    parser.add_argument(
        "--task-mismatch-run",
        dest="task_mismatch_runs",
        action="append",
        type=Path,
        default=None,
        help="Saved tau2 task mismatch analysis directory; may be repeated.",
    )
    args = parser.parse_args()

    result = analyze(
        run_id=args.run_id,
        compiler_runs=tuple(args.compiler_runs) if args.compiler_runs else DEFAULT_COMPILER_RUNS,
        replay_runs=tuple(args.replay_runs) if args.replay_runs else DEFAULT_REPLAY_RUNS,
        task_mismatch_runs=(
            tuple(args.task_mismatch_runs)
            if args.task_mismatch_runs
            else DEFAULT_TASK_MISMATCH_RUNS
        ),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "compiler_validity_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "compiler_run_validity.csv", result["run_rows"], RUN_FIELDS)
    _write_rows(
        args.output_dir / "compiler_reference_action_labels.csv",
        result["action_rows"],
        ACTION_FIELDS,
    )
    _write_rows(args.output_dir / "compiler_lease_labels.csv", result["lease_rows"], LEASE_FIELDS)
    _write_rows(
        args.output_dir / "task_loop_call_labels.csv",
        result["task_loop_rows"],
        TASK_LOOP_FIELDS,
    )
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], DIGEST_FIELDS)
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(
    *,
    run_id: str = "R090",
    compiler_runs: tuple[Path, ...] = DEFAULT_COMPILER_RUNS,
    replay_runs: tuple[Path, ...] = DEFAULT_REPLAY_RUNS,
    task_mismatch_runs: tuple[Path, ...] = DEFAULT_TASK_MISMATCH_RUNS,
) -> dict[str, Any]:
    run_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    lease_rows: list[dict[str, Any]] = []
    task_loop_rows: list[dict[str, Any]] = []

    for run_dir in compiler_runs:
        run_rows.append(_compiler_run_row(run_dir))

    for run_dir in replay_runs:
        replay = _load_replay_run(run_dir)
        run_rows.append(replay["run_row"])
        action_rows.extend(replay["action_rows"])
        lease_rows.extend(replay["lease_rows"])

    for run_dir in task_mismatch_runs:
        task_loop = _load_task_mismatch_run(run_dir)
        run_rows.append(task_loop["run_row"])
        task_loop_rows.extend(task_loop["task_loop_rows"])

    input_paths = _input_paths(compiler_runs, replay_runs, task_mismatch_runs)
    input_digests = [_digest_row(path) for path in input_paths if path.exists()]
    summary = _summary(
        run_id=run_id,
        compiler_runs=compiler_runs,
        replay_runs=replay_runs,
        task_mismatch_runs=task_mismatch_runs,
        run_rows=run_rows,
        action_rows=action_rows,
        lease_rows=lease_rows,
        task_loop_rows=task_loop_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "run_rows": run_rows,
        "action_rows": action_rows,
        "lease_rows": lease_rows,
        "task_loop_rows": task_loop_rows,
        "input_digests": input_digests,
    }


def _compiler_run_row(run_dir: Path) -> dict[str, Any]:
    summary = _load_json(_first_existing(
        run_dir / "llm_visible_lease_compiler_summary.json",
        run_dir / "visible_lease_compiler_summary.json",
    ))
    coverage = _counter_from_csv(run_dir / "reference_coverage.csv", "coverage_class")
    return _blank_run_row(
        run_id=str(summary.get("run_id") or run_dir.name),
        run_kind="visible_lease_compiler",
        source_run_id="",
        strict_argument_lowering="",
        tasks=int(summary.get("tasks_evaluated") or 0),
        reference_actions=int(summary.get("assistant_reference_actions") or sum(coverage.values())),
        lease_rows=int(summary.get("model_lease_slots_total") or 0),
        active_leases=int(summary.get("model_lease_slots_total") or 0),
        exact_reference_actions=coverage["tool_and_non_eval_json_args"],
        broad_or_runtime_actions_admitted=0,
        broad_or_runtime_actions_blocked=coverage["tool_only_runtime_or_broad_args_needed"],
        missing_tool_actions=coverage["missing_tool"],
        constraint_mismatch_actions=0,
        invalid_tool_leases=int(summary.get("invalid_tool_slots_total") or 0),
        source_path=str(run_dir),
    )


def _load_replay_run(run_dir: Path) -> dict[str, Any]:
    summary = _load_json(run_dir / "compiler_gateway_replay_summary.json")
    strict = bool(summary.get("require_all_tool_args_constrained"))
    source_run_id = str(summary.get("source_run_id") or "")
    action_rows = [
        _action_label_row(row, source_run_id, strict, run_dir / "action_results.csv")
        for row in _read_rows(run_dir / "action_results.csv")
    ]
    lease_rows = [
        _lease_label_row(row, source_run_id, strict, run_dir / "lease_results.csv")
        for row in _read_rows(run_dir / "lease_results.csv")
    ]
    action_counts = Counter(row["validity_label"] for row in action_rows)
    lease_counts = Counter(row["validity_label"] for row in lease_rows)
    run_row = _blank_run_row(
        run_id=str(summary.get("run_id") or run_dir.name),
        run_kind="compiler_gateway_replay",
        source_run_id=source_run_id,
        strict_argument_lowering=str(strict),
        tasks=int(summary.get("tasks_evaluated") or 0),
        reference_actions=int(summary.get("assistant_reference_actions") or len(action_rows)),
        lease_rows=len(lease_rows),
        active_leases=int(summary.get("active_leases_total") or 0),
        exact_reference_actions=action_counts["exact_reference_action_covered"],
        broad_or_runtime_actions_admitted=action_counts["broad_or_runtime_arg_admitted"],
        broad_or_runtime_actions_blocked=action_counts["broad_or_runtime_arg_blocked"],
        missing_tool_actions=action_counts["missing_reference_tool"],
        constraint_mismatch_actions=action_counts["exact_tool_wrong_argument_constraint"],
        exact_active_leases=lease_counts["exact_active_lease"],
        broad_or_runtime_active_leases=lease_counts["broad_or_runtime_active_lease"],
        inactive_broad_or_runtime_leases=lease_counts["inactive_broad_or_runtime_lease"],
        invalid_tool_leases=lease_counts["invalid_tool_lease"],
        source_path=str(run_dir),
    )
    return {
        "run_row": run_row,
        "action_rows": action_rows,
        "lease_rows": lease_rows,
    }


def _load_task_mismatch_run(run_dir: Path) -> dict[str, Any]:
    summary = _load_json(run_dir / "tau2_task_gateway_mismatch_summary.json")
    call_rows = [
        _task_loop_label_row(row, run_dir / "model_call_mismatches.csv")
        for row in _read_rows(run_dir / "model_call_mismatches.csv")
    ]
    call_counts = Counter(row["validity_label"] for row in call_rows)
    run_row = _blank_run_row(
        run_id=str(summary.get("run_id") or run_dir.name),
        run_kind="task_loop_mismatch",
        source_run_id="|".join(str(item) for item in summary.get("source_runs", [])),
        strict_argument_lowering="",
        tasks=int(summary.get("tasks") or 0),
        reference_actions=int(summary.get("reference_actions") or 0),
        model_calls=int(summary.get("model_calls") or len(call_rows)),
        exact_executed_calls=call_counts["exact_model_call_executed"],
        off_lease_calls=(
            call_counts["same_tool_wrong_argument_call"]
            + call_counts["wrong_or_hallucinated_tool_call"]
            + call_counts["repeated_or_consumed_exact_args_call"]
        ),
        wrong_or_hallucinated_tool_calls=call_counts["wrong_or_hallucinated_tool_call"],
        same_tool_wrong_args_calls=call_counts["same_tool_wrong_argument_call"],
        source_path=str(run_dir),
    )
    return {"run_row": run_row, "task_loop_rows": call_rows}


def _action_label_row(
    row: dict[str, str],
    source_run_id: str,
    strict: bool,
    source_path: Path,
) -> dict[str, Any]:
    return {
        "run_id": row.get("run_id", ""),
        "source_run_id": source_run_id,
        "strict_argument_lowering": strict,
        "domain": row.get("domain", ""),
        "task_id": row.get("task_id", ""),
        "action_id": row.get("action_id", ""),
        "index": row.get("index", ""),
        "tool": row.get("tool", ""),
        "validity_label": _action_label(row.get("coverage_class", "")),
        "coverage_class": row.get("coverage_class", ""),
        "gateway_allowed": row.get("gateway_allowed", ""),
        "missing_reference_arg_constraints": row.get("missing_reference_arg_constraints", ""),
        "args_json": row.get("args_json", ""),
        "source_path": str(source_path),
    }


def _action_label(coverage_class: str) -> str:
    return {
        "allowed_all_reference_args_constrained": "exact_reference_action_covered",
        "allowed_broad_or_runtime_args": "broad_or_runtime_arg_admitted",
        "blocked_broad_or_runtime_policy": "broad_or_runtime_arg_blocked",
        "blocked_missing_tool": "missing_reference_tool",
        "blocked_constraint_mismatch": "exact_tool_wrong_argument_constraint",
    }.get(coverage_class, "unknown_reference_action_label")


def _lease_label_row(
    row: dict[str, str],
    source_run_id: str,
    strict: bool,
    source_path: Path,
) -> dict[str, Any]:
    valid_tool = _as_bool(row.get("valid_tool", ""))
    active = _lease_active(row)
    broad_args = row.get("broad_or_runtime_args", "")
    inactive_reason = row.get("inactive_reason", "")
    if not valid_tool:
        label = "invalid_tool_lease"
    elif active and not broad_args:
        label = "exact_active_lease"
    elif active and broad_args:
        label = "broad_or_runtime_active_lease"
    elif inactive_reason == "broad_or_runtime_args":
        label = "inactive_broad_or_runtime_lease"
    else:
        label = "inactive_valid_lease"
    return {
        "run_id": row.get("run_id", ""),
        "source_run_id": source_run_id,
        "strict_argument_lowering": strict,
        "domain": row.get("domain", ""),
        "task_id": row.get("task_id", ""),
        "lease_id": row.get("lease_id", ""),
        "tool": row.get("tool", ""),
        "validity_label": label,
        "valid_tool": valid_tool,
        "active": active,
        "inactive_reason": inactive_reason,
        "constrained_args": row.get("constrained_args", ""),
        "broad_or_runtime_args": broad_args,
        "argument_policy_json": row.get("argument_policy_json", ""),
        "source_path": str(source_path),
    }


def _lease_active(row: dict[str, str]) -> bool:
    if "active" in row and row.get("active") != "":
        return _as_bool(row.get("active", ""))
    return _as_bool(row.get("valid_tool", ""))


def _task_loop_label_row(row: dict[str, str], source_path: Path) -> dict[str, Any]:
    category = row.get("category", "")
    label = {
        "exact_executed": "exact_model_call_executed",
        "off_lease_same_tool_wrong_args": "same_tool_wrong_argument_call",
        "off_lease_wrong_or_hallucinated_tool": "wrong_or_hallucinated_tool_call",
        "off_lease_repeated_or_consumed_exact_args": "repeated_or_consumed_exact_args_call",
    }.get(category, "unknown_task_loop_call_label")
    return {
        "run_id": row.get("run_id", ""),
        "domain": row.get("domain", ""),
        "task_id": row.get("task_id", ""),
        "round": row.get("round", ""),
        "index": row.get("index", ""),
        "model_tool": row.get("model_tool", ""),
        "validity_label": label,
        "category": category,
        "arg_distance": row.get("arg_distance", ""),
        "arg_missing_keys": row.get("arg_missing_keys", ""),
        "arg_extra_keys": row.get("arg_extra_keys", ""),
        "arg_wrong_value_keys": row.get("arg_wrong_value_keys", ""),
        "gateway_allowed": row.get("gateway_allowed", ""),
        "executed": row.get("executed", ""),
        "closest_reference_tool": row.get("closest_reference_tool", ""),
        "source_path": str(source_path),
    }


def _summary(
    *,
    run_id: str,
    compiler_runs: tuple[Path, ...],
    replay_runs: tuple[Path, ...],
    task_mismatch_runs: tuple[Path, ...],
    run_rows: list[dict[str, Any]],
    action_rows: list[dict[str, Any]],
    lease_rows: list[dict[str, Any]],
    task_loop_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    action_counts = Counter(str(row["validity_label"]) for row in action_rows)
    lease_counts = Counter(str(row["validity_label"]) for row in lease_rows)
    task_loop_counts = Counter(str(row["validity_label"]) for row in task_loop_rows)
    strict_action_counts = Counter(
        str(row["validity_label"])
        for row in action_rows
        if str(row["strict_argument_lowering"]) == "True"
    )
    non_strict_action_counts = Counter(
        str(row["validity_label"])
        for row in action_rows
        if str(row["strict_argument_lowering"]) != "True"
    )
    replay_reference_actions = sum(
        int(row["reference_actions"])
        for row in run_rows
        if row["run_kind"] == "compiler_gateway_replay"
    )
    exact_reference_actions = action_counts["exact_reference_action_covered"]
    strict_reference_actions = sum(
        int(row["reference_actions"])
        for row in run_rows
        if row["run_kind"] == "compiler_gateway_replay"
        and str(row["strict_argument_lowering"]) == "True"
    )
    strict_exact_reference_actions = strict_action_counts["exact_reference_action_covered"]
    return {
        "run_id": run_id,
        "analysis": "tau2 compiler lease validity and oracle-distance audit from saved artifacts",
        "no_dataset_sync": True,
        "compiler_runs": [str(path) for path in compiler_runs],
        "replay_runs": [str(path) for path in replay_runs],
        "task_mismatch_runs": [str(path) for path in task_mismatch_runs],
        "run_rows": len(run_rows),
        "reference_action_label_rows": len(action_rows),
        "lease_label_rows": len(lease_rows),
        "task_loop_call_label_rows": len(task_loop_rows),
        "replay_reference_actions": replay_reference_actions,
        "exact_reference_action_coverage_rate": (
            exact_reference_actions / replay_reference_actions
            if replay_reference_actions
            else 0.0
        ),
        "strict_reference_actions": strict_reference_actions,
        "strict_exact_reference_action_coverage_rate": (
            strict_exact_reference_actions / strict_reference_actions
            if strict_reference_actions
            else 0.0
        ),
        "action_label_counts": dict(sorted(action_counts.items())),
        "strict_action_label_counts": dict(sorted(strict_action_counts.items())),
        "non_strict_action_label_counts": dict(sorted(non_strict_action_counts.items())),
        "lease_label_counts": dict(sorted(lease_counts.items())),
        "task_loop_label_counts": dict(sorted(task_loop_counts.items())),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "input_digests": input_digests,
        "notes": [
            "This audit does not run models, execute tools, clone, sync, or download datasets; it reads saved R074/R077 compiler, R075/R076/R078 replay, and R080 task-loop mismatch artifacts only.",
            "Reference actions are used only for offline labeling and oracle-distance accounting; they were not available to the LLM compiler at synthesis time.",
            "exact_reference_action_covered means a replayed reference event matched a compiler lease whose reference arguments were all constrained.",
            "broad_or_runtime_arg_admitted is a non-strict replay hazard: the tool matched, but at least one reference argument was broad/runtime.",
            "broad_or_runtime_arg_blocked is the strict-lowering counterpart: the same class of lease is not active until runtime binding or a narrower compiler policy exists.",
            "The result is reviewer-auditable compiler validity evidence, not a blinded expert-oracle lease study.",
        ],
    }


def _blank_run_row(
    *,
    run_id: str,
    run_kind: str,
    source_run_id: str = "",
    strict_argument_lowering: str = "",
    tasks: int = 0,
    reference_actions: int = 0,
    lease_rows: int = 0,
    active_leases: int = 0,
    exact_reference_actions: int = 0,
    broad_or_runtime_actions_admitted: int = 0,
    broad_or_runtime_actions_blocked: int = 0,
    missing_tool_actions: int = 0,
    constraint_mismatch_actions: int = 0,
    exact_active_leases: int = 0,
    broad_or_runtime_active_leases: int = 0,
    inactive_broad_or_runtime_leases: int = 0,
    invalid_tool_leases: int = 0,
    model_calls: int = 0,
    exact_executed_calls: int = 0,
    off_lease_calls: int = 0,
    wrong_or_hallucinated_tool_calls: int = 0,
    same_tool_wrong_args_calls: int = 0,
    source_path: str = "",
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "run_kind": run_kind,
        "source_run_id": source_run_id,
        "strict_argument_lowering": strict_argument_lowering,
        "tasks": tasks,
        "reference_actions": reference_actions,
        "lease_rows": lease_rows,
        "active_leases": active_leases,
        "exact_reference_actions": exact_reference_actions,
        "broad_or_runtime_actions_admitted": broad_or_runtime_actions_admitted,
        "broad_or_runtime_actions_blocked": broad_or_runtime_actions_blocked,
        "missing_tool_actions": missing_tool_actions,
        "constraint_mismatch_actions": constraint_mismatch_actions,
        "exact_active_leases": exact_active_leases,
        "broad_or_runtime_active_leases": broad_or_runtime_active_leases,
        "inactive_broad_or_runtime_leases": inactive_broad_or_runtime_leases,
        "invalid_tool_leases": invalid_tool_leases,
        "model_calls": model_calls,
        "exact_executed_calls": exact_executed_calls,
        "off_lease_calls": off_lease_calls,
        "wrong_or_hallucinated_tool_calls": wrong_or_hallucinated_tool_calls,
        "same_tool_wrong_args_calls": same_tool_wrong_args_calls,
        "source_path": source_path,
    }


def _input_paths(
    compiler_runs: tuple[Path, ...],
    replay_runs: tuple[Path, ...],
    task_mismatch_runs: tuple[Path, ...],
) -> list[Path]:
    paths: list[Path] = []
    for run_dir in compiler_runs:
        paths.extend(
            [
                run_dir / "llm_visible_lease_compiler_summary.json",
                run_dir / "visible_lease_compiler_summary.json",
                run_dir / "lease_results.csv",
                run_dir / "reference_coverage.csv",
                run_dir / "task_results.csv",
            ]
        )
    for run_dir in replay_runs:
        paths.extend(
            [
                run_dir / "compiler_gateway_replay_summary.json",
                run_dir / "lease_results.csv",
                run_dir / "action_results.csv",
                run_dir / "task_results.csv",
            ]
        )
    for run_dir in task_mismatch_runs:
        paths.extend(
            [
                run_dir / "tau2_task_gateway_mismatch_summary.json",
                run_dir / "model_call_mismatches.csv",
                run_dir / "task_mismatch_summary.csv",
                run_dir / "run_mismatch_summary.csv",
            ]
        )
    return paths


def _counter_from_csv(path: Path, column: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in _read_rows(path):
        counter[str(row.get(column, ""))] += 1
    return counter


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


def _digest_row(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "sha256": _sha256(data), "bytes": len(data)}


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
