"""Audit the gap between diagnostic recovery and benchmark-derived utility.

The paper currently has strong denial-targeted recovery diagnostics, but the
main utility/recovery gate is still open: those diagnostics are hand-written and
enumerated, while the benchmark-derived tau2 local-Qwen slice has blocked
actions without a natural feedback/replanning run. This analyzer is read-only
and makes that distinction explicit for the paper/evaluation ledger.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("results/eval/R309BENCHRECOVERYGATE")
DEFAULT_RUN_ID = "R309BENCHRECOVERYGATE"
DEFAULT_INPUTS = {
    "matched_summary": Path("results/eval/R244E1MATCH214215/matched_online_summary.json"),
    "leased_tasks": Path("results/eval/R214E1LEASED/task_results.csv"),
    "leased_actions": Path("results/eval/R214E1LEASED/action_results.csv"),
    "all_tasks": Path("results/eval/R215E1ALL/task_results.csv"),
    "all_actions": Path("results/eval/R215E1ALL/action_results.csv"),
    "six_task_recovery": Path("results/eval/R263RECOVERY/closed_loop_recovery_summary.json"),
    "multiboundary_recovery": Path(
        "results/eval/R305MULTIBOUNDARYRECOVERY/closed_loop_recovery_summary.json"
    ),
}

GATE_FIELDS = [
    "evidence_class",
    "source_run",
    "tasks",
    "gateway_blocks",
    "tasks_with_gateway_blocks",
    "feedback_attempted_tasks",
    "recovered_tasks",
    "action_reward_tasks",
    "tool_oracle_tasks",
    "dangerous_executions",
    "benchmark_derived",
    "free_form_replanning",
    "scope_note",
]
DENIAL_FIELDS = [
    "source_run",
    "tool_exposure",
    "domain",
    "task_id",
    "gateway_blocked",
    "off_lease_calls_blocked",
    "feedback_attempted",
    "action_reward",
    "tool_oracle_pass",
]
DIGEST_FIELDS = ["input_name", "path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze benchmark recovery gate")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Override an input artifact path.",
    )
    args = parser.parse_args()

    inputs = dict(DEFAULT_INPUTS)
    for item in args.input:
        name, sep, value = item.partition("=")
        if not sep or not name:
            raise SystemExit(f"invalid --input override: {item!r}")
        inputs[name] = Path(value)

    result = analyze(output_dir=args.output_dir, inputs=inputs, run_id=args.run_id)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, output_dir: Path, inputs: dict[str, Path], run_id: str) -> dict[str, Any]:
    matched = _read_json(inputs["matched_summary"])
    leased_tasks = _read_rows(inputs["leased_tasks"])
    leased_actions = _read_rows(inputs["leased_actions"])
    all_tasks = _read_rows(inputs["all_tasks"])
    all_actions = _read_rows(inputs["all_actions"])
    six = _read_json(inputs["six_task_recovery"])
    multi = _read_json(inputs["multiboundary_recovery"])

    _validate_matched_summary(matched, leased_tasks, leased_actions, all_tasks, all_actions)
    gate_rows = _gate_rows(
        matched=matched,
        leased_tasks=leased_tasks,
        all_tasks=all_tasks,
        six=six,
        multi=multi,
    )
    denial_rows = _denial_rows("R214E1LEASED", leased_tasks) + _denial_rows(
        "R215E1ALL", all_tasks
    )
    digests = [_file_digest(name, path) for name, path in sorted(inputs.items())]
    summary = _summary(
        run_id=run_id,
        matched=matched,
        leased_tasks=leased_tasks,
        all_tasks=all_tasks,
        six=six,
        multi=multi,
        denial_rows=denial_rows,
        digests=digests,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "recovery_gate_rows.csv", gate_rows, GATE_FIELDS)
    _write_rows(output_dir / "benchmark_denial_tasks.csv", denial_rows, DENIAL_FIELDS)
    _write_rows(output_dir / "input_digests.csv", digests, DIGEST_FIELDS)
    (output_dir / "benchmark_recovery_gate_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    return {"summary": summary, "gate_rows": gate_rows, "denial_rows": denial_rows}


def _gate_rows(
    *,
    matched: dict[str, Any],
    leased_tasks: list[dict[str, str]],
    all_tasks: list[dict[str, str]],
    six: dict[str, Any],
    multi: dict[str, Any],
) -> list[dict[str, Any]]:
    leased = matched["leased"]
    all_tools = matched["all_tools"]
    return [
        {
            "evidence_class": "benchmark_matched_leased",
            "source_run": "R214E1LEASED/R244E1MATCH214215",
            "tasks": int(leased["tasks_evaluated"]),
            "gateway_blocks": int(leased["gateway_blocked"]),
            "tasks_with_gateway_blocks": _tasks_with_blocks(leased_tasks),
            "feedback_attempted_tasks": 0,
            "recovered_tasks": 0,
            "action_reward_tasks": int(leased["action_reward_pass_tasks"]),
            "tool_oracle_tasks": int(leased["tool_oracle_pass_tasks"]),
            "dangerous_executions": "",
            "benchmark_derived": True,
            "free_form_replanning": False,
            "scope_note": "benchmark-derived local-Qwen task-loop slice; no natural feedback/recovery run",
        },
        {
            "evidence_class": "benchmark_matched_all_tools",
            "source_run": "R215E1ALL/R244E1MATCH214215",
            "tasks": int(all_tools["tasks_evaluated"]),
            "gateway_blocks": int(all_tools["gateway_blocked"]),
            "tasks_with_gateway_blocks": _tasks_with_blocks(all_tasks),
            "feedback_attempted_tasks": 0,
            "recovered_tasks": 0,
            "action_reward_tasks": int(all_tools["action_reward_pass_tasks"]),
            "tool_oracle_tasks": int(all_tools["tool_oracle_pass_tasks"]),
            "dangerous_executions": "",
            "benchmark_derived": True,
            "free_form_replanning": False,
            "scope_note": "broader tool exposure increases blocks/off-lease calls without improving reward",
        },
        {
            "evidence_class": "handwritten_closed_loop_recovery",
            "source_run": str(six["run_id"]),
            "tasks": int(six["tasks"]),
            "gateway_blocks": int(six["initial_gateway_blocked_unsafe"]),
            "tasks_with_gateway_blocks": int(six["initial_gateway_blocked_unsafe"]),
            "feedback_attempted_tasks": int(six["feedback_attempts"]),
            "recovered_tasks": int(six["recovered_to_allowed_alternative"]),
            "action_reward_tasks": "",
            "tool_oracle_tasks": "",
            "dangerous_executions": int(six["final_dangerous_executes"]),
            "benchmark_derived": False,
            "free_form_replanning": False,
            "scope_note": "hand-written enumerated-candidate recovery microbenchmark",
        },
        {
            "evidence_class": "handwritten_multiboundary_recovery",
            "source_run": str(multi["run_id"]),
            "tasks": int(multi["tasks"]),
            "gateway_blocks": int(multi["initial_gateway_blocked_unsafe"]),
            "tasks_with_gateway_blocks": int(multi["initial_gateway_blocked_unsafe"]),
            "feedback_attempted_tasks": int(multi["feedback_attempts"]),
            "recovered_tasks": int(multi["recovered_to_allowed_alternative"]),
            "action_reward_tasks": "",
            "tool_oracle_tasks": "",
            "dangerous_executions": int(multi["final_dangerous_executes"]),
            "benchmark_derived": False,
            "free_form_replanning": False,
            "scope_note": "hand-written enumerated-candidate suite covering 6 surfaces and 4 owner classes",
        },
    ]


def _denial_rows(source_run: str, task_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in task_rows:
        gateway_blocked = int(row["gateway_blocked"])
        off_lease = int(row["off_lease_calls_blocked"])
        if gateway_blocked == 0 and off_lease == 0:
            continue
        rows.append(
            {
                "source_run": source_run,
                "tool_exposure": row["tool_exposure"],
                "domain": row["domain"],
                "task_id": row["task_id"],
                "gateway_blocked": gateway_blocked,
                "off_lease_calls_blocked": off_lease,
                "feedback_attempted": row["feedback_attempted"],
                "action_reward": row["action_reward"],
                "tool_oracle_pass": row["tool_oracle_pass"],
            }
        )
    return rows


def _summary(
    *,
    run_id: str,
    matched: dict[str, Any],
    leased_tasks: list[dict[str, str]],
    all_tasks: list[dict[str, str]],
    six: dict[str, Any],
    multi: dict[str, Any],
    denial_rows: list[dict[str, Any]],
    digests: list[dict[str, Any]],
) -> dict[str, Any]:
    leased_blocked_tasks = _tasks_with_blocks(leased_tasks)
    all_blocked_tasks = _tasks_with_blocks(all_tasks)
    natural_feedback_tasks = sum(
        1 for row in leased_tasks + all_tasks if _truthy(row["feedback_attempted"])
    )
    handwritten_tasks = int(six["tasks"]) + int(multi["tasks"])
    handwritten_recovered = int(six["recovered_to_allowed_alternative"]) + int(
        multi["recovered_to_allowed_alternative"]
    )
    return {
        "analysis": "benchmark-derived recovery gate over saved local artifacts",
        "run_id": run_id,
        "benchmark_matched_tasks": int(matched["matched_tasks"]),
        "benchmark_runs": 2,
        "benchmark_leased_gateway_blocks": int(matched["leased"]["gateway_blocked"]),
        "benchmark_all_tools_gateway_blocks": int(matched["all_tools"]["gateway_blocked"]),
        "benchmark_leased_tasks_with_blocks": leased_blocked_tasks,
        "benchmark_all_tools_tasks_with_blocks": all_blocked_tasks,
        "benchmark_denial_task_rows": len(denial_rows),
        "benchmark_feedback_attempted_tasks": natural_feedback_tasks,
        "benchmark_recovered_tasks": 0,
        "benchmark_leased_action_reward_tasks": int(
            matched["leased"]["action_reward_pass_tasks"]
        ),
        "benchmark_all_tools_action_reward_tasks": int(
            matched["all_tools"]["action_reward_pass_tasks"]
        ),
        "benchmark_action_reward_improvement_all_minus_leased": int(
            matched["delta_all_minus_leased"]["action_reward_pass_tasks"]
        ),
        "benchmark_leased_tool_oracle_tasks": int(matched["leased"]["tool_oracle_pass_tasks"]),
        "benchmark_all_tools_tool_oracle_tasks": int(
            matched["all_tools"]["tool_oracle_pass_tasks"]
        ),
        "handwritten_recovery_tasks": handwritten_tasks,
        "handwritten_recovered_tasks": handwritten_recovered,
        "handwritten_dangerous_executions": int(six["final_dangerous_executes"])
        + int(multi["final_dangerous_executes"]),
        "handwritten_multiboundary_surfaces": int(multi["surfaces_covered"]),
        "handwritten_multiboundary_owner_classes": list(multi["owner_classes_covered"]),
        "gate_status": "open",
        "missing_for_full_claim": [
            "benchmark-derived denied-benign recovery run",
            "free-form or non-enumerated replanning after checker denial",
            "task-level utility improvement or preservation under recovery",
            "approval-burden measurement",
        ],
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_benchmark": True,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "project_head": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--short", "--branch"),
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "input_digests": digests,
        "notes": [
            "This is a read-only gate audit over saved local result artifacts.",
            "It does not run a model, execute tools, replay traces, clone repositories, sync datasets, or download data.",
            "The result separates benchmark-derived utility evidence from hand-written denial-targeted recovery diagnostics.",
            "The gate remains open because the benchmark-derived slice has denial tasks but no natural feedback/recovery run and no task-level reward improvement.",
        ],
    }


def _validate_matched_summary(
    matched: dict[str, Any],
    leased_tasks: list[dict[str, str]],
    leased_actions: list[dict[str, str]],
    all_tasks: list[dict[str, str]],
    all_actions: list[dict[str, str]],
) -> None:
    checks = [
        ("leased.tasks_evaluated", len(leased_tasks), int(matched["leased"]["tasks_evaluated"])),
        ("all_tools.tasks_evaluated", len(all_tasks), int(matched["all_tools"]["tasks_evaluated"])),
        ("leased.model_calls", len(leased_actions), int(matched["leased"]["model_calls"])),
        ("all_tools.model_calls", len(all_actions), int(matched["all_tools"]["model_calls"])),
        (
            "leased.gateway_blocked",
            _sum_int(leased_tasks, "gateway_blocked"),
            int(matched["leased"]["gateway_blocked"]),
        ),
        (
            "all_tools.gateway_blocked",
            _sum_int(all_tasks, "gateway_blocked"),
            int(matched["all_tools"]["gateway_blocked"]),
        ),
    ]
    mismatches = [name for name, actual, expected in checks if actual != expected]
    if mismatches:
        raise ValueError(f"matched summary/CSV mismatch: {', '.join(mismatches)}")


def _tasks_with_blocks(rows: list[dict[str, str]]) -> int:
    return sum(
        1
        for row in rows
        if int(row["gateway_blocked"]) > 0 or int(row["off_lease_calls_blocked"]) > 0
    )


def _sum_int(rows: list[dict[str, str]], field: str) -> int:
    return sum(int(row[field]) for row in rows)


def _truthy(value: str) -> bool:
    return value.lower() in {"true", "1", "yes"}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _file_digest(name: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "input_name": name,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
