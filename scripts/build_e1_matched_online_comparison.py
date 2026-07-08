"""Build a paper-facing E1 matched online comparison.

This script consolidates two already executed local-Qwen task-loop runs:
one with leased IntentCap tool exposure and one with all tools exposed. It does
not run a model, execute tools, sync datasets, or mint authority. The output is
a compact comparison artifact for the E1 security/utility claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any


DEFAULT_LEASED_DIR = Path("results/eval/R197")
DEFAULT_ALL_TOOLS_DIR = Path("results/eval/R209E1ALL")

RUN_FIELDS = [
    "policy",
    "run_id",
    "tool_exposure",
    "tasks_evaluated",
    "reference_actions",
    "tool_schema_count_avg",
    "tool_schema_count_min",
    "tool_schema_count_max",
    "active_leases_total",
    "model_calls",
    "gateway_allowed",
    "gateway_blocked",
    "off_lease_calls_blocked",
    "compiler_runtime_binding_missing_value_proof",
    "executed_calls",
    "tool_error_calls",
    "bound_reference_calls",
    "exact_sequence_match_tasks",
    "all_reference_actions_executed_tasks",
    "action_reward_pass_tasks",
    "env_reward_pass_tasks",
    "tool_oracle_pass_tasks",
    "stepwise_repair_map_priority_steps",
    "stepwise_tool_activation_priority_steps",
    "stepwise_runtime_evidence_ranked_fallbacks",
    "stepwise_compiler_lease_fallbacks",
    "user_simulator_executed_actions",
]

TASK_FIELDS = [
    "domain",
    "task_id",
    "leased_tool_schema_count",
    "all_tool_schema_count",
    "tool_schema_delta",
    "leased_active_leases",
    "all_active_leases",
    "leased_model_calls",
    "all_model_calls",
    "leased_gateway_blocked",
    "all_gateway_blocked",
    "leased_off_lease_blocked",
    "all_off_lease_blocked",
    "leased_missing_value_proof",
    "all_missing_value_proof",
    "leased_executed_calls",
    "all_executed_calls",
    "leased_tool_error_calls",
    "all_tool_error_calls",
    "leased_bound_reference_calls",
    "all_bound_reference_calls",
    "leased_exact_sequence_match",
    "all_exact_sequence_match",
    "leased_all_reference_actions_executed",
    "all_all_reference_actions_executed",
    "leased_action_reward",
    "all_action_reward",
    "leased_tool_oracle_pass",
    "all_tool_oracle_pass",
]

BLOCK_FIELDS = [
    "policy",
    "run_id",
    "domain",
    "task_id",
    "round",
    "index",
    "model_tool",
    "object",
    "gateway_action",
    "gateway_reason",
    "runtime_binding_attempted",
    "runtime_binding_allowed",
    "runtime_binding_reason",
    "tool_activation_binding_attempted",
    "tool_activation_binding_allowed",
    "tool_activation_binding_reason",
    "model_args_json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 matched online comparison")
    parser.add_argument("--leased-dir", type=Path, default=DEFAULT_LEASED_DIR)
    parser.add_argument("--all-tools-dir", type=Path, default=DEFAULT_ALL_TOOLS_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R213E1MATCH")
    args = parser.parse_args()

    result = build_comparison(
        leased_dir=args.leased_dir,
        all_tools_dir=args.all_tools_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def build_comparison(
    *,
    leased_dir: Path,
    all_tools_dir: Path,
    output_dir: Path,
    run_id: str = "R213E1MATCH",
) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    leased = _load_run(leased_dir, "leased")
    all_tools = _load_run(all_tools_dir, "all_tools")

    run_rows = [_run_row(leased), _run_row(all_tools)]
    task_rows = _task_rows(leased, all_tools)
    blocked_rows = _blocked_rows(leased) + _blocked_rows(all_tools)
    summary = _summary(run_id, leased, all_tools, task_rows, blocked_rows, output_dir)

    _write_csv(output_dir / "run_comparison.csv", RUN_FIELDS, run_rows)
    _write_csv(output_dir / "task_comparison.csv", TASK_FIELDS, task_rows)
    _write_csv(output_dir / "blocked_calls.csv", BLOCK_FIELDS, blocked_rows)
    (output_dir / "matched_online_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "input_digests.csv").write_text(_input_digest_text(leased, all_tools))
    (output_dir / "command.txt").write_text(_command_text())
    return {
        "summary": summary,
        "run_rows": run_rows,
        "task_rows": task_rows,
        "blocked_rows": blocked_rows,
    }


def _load_run(run_dir: Path, policy: str) -> dict[str, Any]:
    summary_path = run_dir / "task_gateway_summary.json"
    task_path = run_dir / "task_results.csv"
    action_path = run_dir / "action_results.csv"
    return {
        "policy": policy,
        "run_dir": run_dir,
        "summary_path": summary_path,
        "task_path": task_path,
        "action_path": action_path,
        "summary": json.loads(summary_path.read_text()),
        "tasks": list(_read_csv(task_path)),
        "actions": list(_read_csv(action_path)),
        "command": (run_dir / "command.txt").read_text() if (run_dir / "command.txt").exists() else "",
    }


def _run_row(run: dict[str, Any]) -> dict[str, Any]:
    summary = run["summary"]
    return {field: _summary_field(run, field) for field in RUN_FIELDS}


def _summary_field(run: dict[str, Any], field: str) -> Any:
    if field == "policy":
        return run["policy"]
    summary = run["summary"]
    if field == "stepwise_compiler_lease_fallbacks":
        return summary.get("stepwise_compiler_lease_fallbacks", 0)
    return summary.get(field, "")


def _task_rows(leased: dict[str, Any], all_tools: dict[str, Any]) -> list[dict[str, Any]]:
    leased_tasks = {_task_key(row): row for row in leased["tasks"]}
    all_tasks = {_task_key(row): row for row in all_tools["tasks"]}
    rows: list[dict[str, Any]] = []
    for key in sorted(leased_tasks.keys() & all_tasks.keys()):
        left = leased_tasks[key]
        right = all_tasks[key]
        rows.append(
            {
                "domain": key[0],
                "task_id": key[1],
                "leased_tool_schema_count": _int(left, "tool_schema_count"),
                "all_tool_schema_count": _int(right, "tool_schema_count"),
                "tool_schema_delta": _int(right, "tool_schema_count")
                - _int(left, "tool_schema_count"),
                "leased_active_leases": _int(left, "active_leases"),
                "all_active_leases": _int(right, "active_leases"),
                "leased_model_calls": _int(left, "model_calls"),
                "all_model_calls": _int(right, "model_calls"),
                "leased_gateway_blocked": _int(left, "gateway_blocked"),
                "all_gateway_blocked": _int(right, "gateway_blocked"),
                "leased_off_lease_blocked": _int(left, "off_lease_calls_blocked"),
                "all_off_lease_blocked": _int(right, "off_lease_calls_blocked"),
                "leased_missing_value_proof": _int(
                    left, "compiler_runtime_binding_missing_value_proof"
                ),
                "all_missing_value_proof": _int(
                    right, "compiler_runtime_binding_missing_value_proof"
                ),
                "leased_executed_calls": _int(left, "executed_calls"),
                "all_executed_calls": _int(right, "executed_calls"),
                "leased_tool_error_calls": _int(left, "tool_error_calls"),
                "all_tool_error_calls": _int(right, "tool_error_calls"),
                "leased_bound_reference_calls": _int(left, "bound_reference_calls"),
                "all_bound_reference_calls": _int(right, "bound_reference_calls"),
                "leased_exact_sequence_match": _bool_cell(left, "exact_sequence_match"),
                "all_exact_sequence_match": _bool_cell(right, "exact_sequence_match"),
                "leased_all_reference_actions_executed": _bool_cell(
                    left, "all_reference_actions_executed"
                ),
                "all_all_reference_actions_executed": _bool_cell(
                    right, "all_reference_actions_executed"
                ),
                "leased_action_reward": _float(left, "action_reward"),
                "all_action_reward": _float(right, "action_reward"),
                "leased_tool_oracle_pass": _bool_cell(left, "tool_oracle_pass"),
                "all_tool_oracle_pass": _bool_cell(right, "tool_oracle_pass"),
            }
        )
    return rows


def _blocked_rows(run: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in run["actions"]:
        if _bool_cell(action, "gateway_allowed"):
            continue
        row = {field: "" for field in BLOCK_FIELDS}
        row.update(
            {
                "policy": run["policy"],
                "run_id": run["summary"].get("run_id", ""),
                "domain": action.get("domain", ""),
                "task_id": action.get("task_id", ""),
                "round": action.get("round", ""),
                "index": action.get("index", ""),
                "model_tool": action.get("model_tool", ""),
                "object": action.get("object", ""),
                "gateway_action": action.get("gateway_action", ""),
                "gateway_reason": action.get("gateway_reason", ""),
                "runtime_binding_attempted": action.get("runtime_binding_attempted", ""),
                "runtime_binding_allowed": action.get("runtime_binding_allowed", ""),
                "runtime_binding_reason": action.get("runtime_binding_reason", ""),
                "tool_activation_binding_attempted": action.get(
                    "tool_activation_binding_attempted", ""
                ),
                "tool_activation_binding_allowed": action.get(
                    "tool_activation_binding_allowed", ""
                ),
                "tool_activation_binding_reason": action.get(
                    "tool_activation_binding_reason", ""
                ),
                "model_args_json": action.get("model_args_json", ""),
            }
        )
        rows.append(row)
    return rows


def _summary(
    run_id: str,
    leased: dict[str, Any],
    all_tools: dict[str, Any],
    task_rows: list[dict[str, Any]],
    blocked_rows: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    left = leased["summary"]
    right = all_tools["summary"]
    deltas = {
        "tool_schema_count_avg": right.get("tool_schema_count_avg", 0)
        - left.get("tool_schema_count_avg", 0),
        "gateway_blocked": right.get("gateway_blocked", 0) - left.get("gateway_blocked", 0),
        "off_lease_calls_blocked": right.get("off_lease_calls_blocked", 0)
        - left.get("off_lease_calls_blocked", 0),
        "missing_value_proof_blocks": right.get(
            "compiler_runtime_binding_missing_value_proof", 0
        )
        - left.get("compiler_runtime_binding_missing_value_proof", 0),
        "bound_reference_calls": right.get("bound_reference_calls", 0)
        - left.get("bound_reference_calls", 0),
        "action_reward_pass_tasks": right.get("action_reward_pass_tasks", 0)
        - left.get("action_reward_pass_tasks", 0),
        "exact_sequence_match_tasks": right.get("exact_sequence_match_tasks", 0)
        - left.get("exact_sequence_match_tasks", 0),
        "tool_oracle_pass_tasks": right.get("tool_oracle_pass_tasks", 0)
        - left.get("tool_oracle_pass_tasks", 0),
    }
    return {
        "run_id": run_id,
        "analysis": "E1 matched online local-Qwen leased-vs-all-tools comparison",
        "leased_run_id": left.get("run_id"),
        "all_tools_run_id": right.get("run_id"),
        "leased_dir": str(leased["run_dir"]),
        "all_tools_dir": str(all_tools["run_dir"]),
        "matched_tasks": len(task_rows),
        "blocked_calls": len(blocked_rows),
        "leased": _summary_metrics(left),
        "all_tools": _summary_metrics(right),
        "delta_all_minus_leased": deltas,
        "claim_interpretation": (
            "On this matched 11-task local-Qwen slice, exposing all tools increases "
            "visible schemas and checker-visible blocks without improving action "
            "reward, exact-sequence match, or tool-oracle pass tasks."
        ),
        "boundary": (
            "This is a consolidation of existing local runs, not a new model run, "
            "benchmark-scale utility result, approval-burden study, or dataset sync."
        ),
        "output_dir": str(output_dir),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "project_head": _command_output(["git", "rev-parse", "HEAD"]),
        "git_status": _command_output(["git", "status", "--short", "--branch"]),
    }


def _summary_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "tool_exposure",
        "tasks_evaluated",
        "reference_actions",
        "tool_schema_count_avg",
        "tool_schema_count_min",
        "tool_schema_count_max",
        "active_leases_total",
        "model_calls",
        "gateway_allowed",
        "gateway_blocked",
        "off_lease_calls_blocked",
        "compiler_runtime_binding_missing_value_proof",
        "executed_calls",
        "tool_error_calls",
        "bound_reference_calls",
        "exact_sequence_match_tasks",
        "all_reference_actions_executed_tasks",
        "action_reward_pass_tasks",
        "env_reward_pass_tasks",
        "tool_oracle_pass_tasks",
    ]
    return {key: summary.get(key) for key in keys}


def _input_digest_text(leased: dict[str, Any], all_tools: dict[str, Any]) -> str:
    lines = ["policy,path,sha256,bytes\n"]
    for run in (leased, all_tools):
        for key in ("summary_path", "task_path", "action_path"):
            path = run[key]
            data = path.read_bytes()
            lines.append(
                f"{run['policy']},{path},{hashlib.sha256(data).hexdigest()},{len(data)}\n"
            )
    return "".join(lines)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _task_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("domain", ""), row.get("task_id", "")


def _int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value else 0


def _float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value else 0.0


def _bool_cell(row: dict[str, str], key: str) -> bool:
    return str(row.get(key, "")).lower() in {"1", "true", "yes"}


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _command_output(command: list[str]) -> str:
    import subprocess

    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
