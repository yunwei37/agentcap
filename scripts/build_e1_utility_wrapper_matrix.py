"""Build the E1 utility-side wrapper comparison matrix.

This script consolidates saved tau2/tau3 authority-minimization and
evaluator-backed reference replay summaries into one paper-facing utility
proxy table. It answers a narrow question: which wrapper families would block
benchmark assistant reference actions, and how much authority do they expose?

It does not run a model, execute tools, clone repositories, sync datasets, or
claim end-to-end task success for static wrapper baselines.
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
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_AUTHORITY_SUMMARY = Path("results/tau2/R022/authority_summary.json")
DEFAULT_ORACLE_SUMMARY = Path("results/tau2/R024/oracle_summary.json")

MATRIX_FIELDS = [
    "benchmark",
    "workload_family",
    "policy",
    "policy_family",
    "source_runs",
    "task_count",
    "tasks_with_assistant_reference_actions",
    "assistant_reference_actions",
    "allowed_reference_actions",
    "blocked_reference_actions",
    "reference_action_coverage_rate",
    "tasks_with_full_reference_coverage",
    "task_full_reference_coverage_rate",
    "control_provenance_checked",
    "event_id_checked",
    "argument_values_constrained",
    "direct_intentcap_reference_replay",
    "replay_tool_oracle_applicable_tasks",
    "replay_tool_oracle_pass_tasks",
    "replay_tool_oracle_pass_rate",
    "tool_error_events",
    "mean_exposed_tools_per_task",
    "median_exposed_tools_per_task",
    "p95_exposed_tools_per_task",
    "max_exposed_tools_per_task",
    "exposed_tool_slots_total",
    "extra_tool_slots_vs_intentcap",
    "tool_slot_over_intentcap_ratio",
    "write_tool_slots_total",
    "discoverable_tool_slots_total",
    "notes",
]

FAMILY_FIELDS = [
    "policy_family",
    "rows",
    "policies",
    "min_reference_action_coverage_rate",
    "max_reference_action_coverage_rate",
    "min_mean_exposed_tools_per_task",
    "max_mean_exposed_tools_per_task",
    "min_extra_tool_slots_vs_intentcap",
    "max_extra_tool_slots_vs_intentcap",
    "any_direct_intentcap_reference_replay",
    "all_rows_check_control_provenance",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 utility wrapper matrix")
    parser.add_argument("--run-id", default="R203E1U")
    parser.add_argument("--authority-summary", type=Path, default=DEFAULT_AUTHORITY_SUMMARY)
    parser.add_argument("--oracle-summary", type=Path, default=DEFAULT_ORACLE_SUMMARY)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build_matrix(
        run_id=args.run_id,
        authority_summary=args.authority_summary,
        oracle_summary=args.oracle_summary,
    )
    write_outputs(args.output_dir, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def build_matrix(
    *,
    run_id: str,
    authority_summary: Path = DEFAULT_AUTHORITY_SUMMARY,
    oracle_summary: Path = DEFAULT_ORACLE_SUMMARY,
) -> dict[str, Any]:
    authority = json.loads(authority_summary.read_text())
    oracle = json.loads(oracle_summary.read_text())
    inputs = [authority_summary, oracle_summary]

    matrix_rows = _rows_from_summaries(authority, oracle)
    family_rows = _family_summary_rows(matrix_rows)
    summary = _summary(run_id, authority, oracle, matrix_rows, family_rows, inputs)
    return {
        "summary": summary,
        "matrix_rows": matrix_rows,
        "family_rows": family_rows,
        "input_digests": [_file_digest(path) for path in inputs],
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "e1_utility_wrapper_matrix.csv", result["matrix_rows"], MATRIX_FIELDS)
    _write_rows(output_dir / "e1_utility_policy_family_summary.csv", result["family_rows"], FAMILY_FIELDS)
    _write_rows(output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "e1_utility_wrapper_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())


def _rows_from_summaries(authority: dict[str, Any], oracle: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    benchmark = str(authority.get("benchmark", "tau2-bench / tau3-bench"))
    for policy in authority.get("baseline_order", []):
        baseline = authority.get("baselines", {}).get(policy, {})
        assistant_reference_actions = _int(baseline.get("assistant_reference_actions"))
        covered = _int(baseline.get("covered_assistant_reference_actions"))
        blocked = max(0, assistant_reference_actions - covered)
        direct_replay = policy == "intentcap_reference_events"
        row = {
            "benchmark": benchmark,
            "workload_family": "stateful_reference_action_utility",
            "policy": policy,
            "policy_family": _policy_family(policy),
            "source_runs": "R022|R024",
            "task_count": _int(baseline.get("tasks")),
            "tasks_with_assistant_reference_actions": _int(
                baseline.get("tasks_with_assistant_reference_actions")
            ),
            "assistant_reference_actions": assistant_reference_actions,
            "allowed_reference_actions": covered,
            "blocked_reference_actions": blocked,
            "reference_action_coverage_rate": _rate(covered, assistant_reference_actions),
            "tasks_with_full_reference_coverage": _int(
                baseline.get("tasks_with_full_assistant_reference_coverage")
            ),
            "task_full_reference_coverage_rate": _rate(
                _int(baseline.get("tasks_with_full_assistant_reference_coverage")),
                _int(baseline.get("tasks")),
            ),
            "control_provenance_checked": bool(baseline.get("control_provenance_checked")),
            "event_id_checked": bool(baseline.get("event_id_checked")),
            "argument_values_constrained": bool(baseline.get("argument_values_constrained")),
            "direct_intentcap_reference_replay": direct_replay,
            "replay_tool_oracle_applicable_tasks": _oracle_value(
                oracle, "tool_oracle_applicable_tasks", direct_replay
            ),
            "replay_tool_oracle_pass_tasks": _oracle_value(
                oracle, "tool_oracle_pass_tasks", direct_replay
            ),
            "replay_tool_oracle_pass_rate": _oracle_value(
                oracle, "tool_oracle_pass_rate", direct_replay
            ),
            "tool_error_events": _oracle_value(oracle, "tool_error_events", direct_replay),
            "mean_exposed_tools_per_task": _float(baseline.get("mean_exposed_tools_per_task")),
            "median_exposed_tools_per_task": _float(baseline.get("median_exposed_tools_per_task")),
            "p95_exposed_tools_per_task": _float(baseline.get("p95_exposed_tools_per_task")),
            "max_exposed_tools_per_task": _float(baseline.get("max_exposed_tools_per_task")),
            "exposed_tool_slots_total": _int(baseline.get("exposed_tool_slots_total")),
            "extra_tool_slots_vs_intentcap": _int(baseline.get("extra_tool_slots_vs_intentcap")),
            "tool_slot_over_intentcap_ratio": _float(baseline.get("tool_slot_over_intentcap_ratio")),
            "write_tool_slots_total": _int(baseline.get("write_tool_slots_total")),
            "discoverable_tool_slots_total": _int(baseline.get("discoverable_tool_slots_total")),
            "notes": _row_note(policy, direct_replay),
        }
        rows.append(row)
    return rows


def _oracle_value(oracle: dict[str, Any], key: str, direct_replay: bool) -> Any:
    if not direct_replay:
        return ""
    return oracle.get(key, "")


def _policy_family(policy: str) -> str:
    mapping = {
        "intentcap_reference_events": "intentcap",
        "task_reference_tools": "exact_or_task_tool_acl",
        "domain_assistant_regular": "domain_allowlist",
        "domain_assistant_all": "domain_allowlist",
        "global_assistant_regular": "global_static_acl",
        "global_all_tools": "global_catalog_acl",
    }
    return mapping.get(policy, "other")


def _row_note(policy: str, direct_replay: bool) -> str:
    if direct_replay:
        return "Direct exact IntentCap reference-action replay through the gateway and tau2 evaluator."
    if policy == "task_reference_tools":
        return "Reference-action coverage proxy: task tool ACL covers benign reference tools but lacks event/provenance constraints."
    if policy.startswith("domain_"):
        return "Reference-action coverage proxy: domain allowlist covers reference actions but exposes extra domain tools."
    if policy.startswith("global_"):
        return "Reference-action coverage proxy: global static policy covers reference actions with broad extra authority."
    return "Reference-action coverage proxy; not a model-run utility result."


def _family_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["policy_family"])].append(row)

    family_rows: list[dict[str, Any]] = []
    for family, family_rows_raw in sorted(grouped.items()):
        family_rows.append(
            {
                "policy_family": family,
                "rows": len(family_rows_raw),
                "policies": "|".join(sorted(str(row["policy"]) for row in family_rows_raw)),
                "min_reference_action_coverage_rate": min(
                    _float(row["reference_action_coverage_rate"]) for row in family_rows_raw
                ),
                "max_reference_action_coverage_rate": max(
                    _float(row["reference_action_coverage_rate"]) for row in family_rows_raw
                ),
                "min_mean_exposed_tools_per_task": min(
                    _float(row["mean_exposed_tools_per_task"]) for row in family_rows_raw
                ),
                "max_mean_exposed_tools_per_task": max(
                    _float(row["mean_exposed_tools_per_task"]) for row in family_rows_raw
                ),
                "min_extra_tool_slots_vs_intentcap": min(
                    _int(row["extra_tool_slots_vs_intentcap"]) for row in family_rows_raw
                ),
                "max_extra_tool_slots_vs_intentcap": max(
                    _int(row["extra_tool_slots_vs_intentcap"]) for row in family_rows_raw
                ),
                "any_direct_intentcap_reference_replay": any(
                    bool(row["direct_intentcap_reference_replay"]) for row in family_rows_raw
                ),
                "all_rows_check_control_provenance": all(
                    bool(row["control_provenance_checked"]) for row in family_rows_raw
                ),
            }
        )
    return family_rows


def _summary(
    run_id: str,
    authority: dict[str, Any],
    oracle: dict[str, Any],
    matrix_rows: list[dict[str, Any]],
    family_rows: list[dict[str, Any]],
    input_paths: list[Path],
) -> dict[str, Any]:
    intentcap = _find_row(matrix_rows, "intentcap_reference_events")
    exact_acl = _find_row(matrix_rows, "task_reference_tools")
    max_extra = max(_int(row["extra_tool_slots_vs_intentcap"]) for row in matrix_rows)
    return {
        "run_id": run_id,
        "analysis": "E1 utility-side reference-action wrapper comparison",
        "benchmark": authority.get("benchmark", "tau2-bench / tau3-bench"),
        "matrix_rows": len(matrix_rows),
        "family_rows": len(family_rows),
        "task_count": _int(authority.get("tasks")),
        "assistant_reference_actions": _int(authority.get("assistant_reference_actions")),
        "intentcap_reference_action_coverage_rate": _float(
            intentcap["reference_action_coverage_rate"]
        ),
        "exact_or_task_tool_acl_reference_action_coverage_rate": _float(
            exact_acl["reference_action_coverage_rate"]
        ),
        "intentcap_replay_tool_oracle_pass_tasks": _int(oracle.get("tool_oracle_pass_tasks")),
        "intentcap_replay_tool_oracle_applicable_tasks": _int(
            oracle.get("tool_oracle_applicable_tasks")
        ),
        "intentcap_replay_tool_oracle_pass_rate": _float(oracle.get("tool_oracle_pass_rate")),
        "tool_error_events": _int(oracle.get("tool_error_events")),
        "max_extra_tool_slots_vs_intentcap": max_extra,
        "no_dataset_sync": True,
        "not_a_fresh_online_run": True,
        "not_a_model_task_success_result": True,
        "notes": [
            "This is an E1 utility-side proxy over saved tau2/tau3 reference actions.",
            "It measures whether wrapper families cover benign assistant reference actions and how much authority they expose.",
            "Only the IntentCap exact reference-event row has direct saved gateway/evaluator replay evidence from R024.",
            "Static wrapper rows are coverage proxies, not fresh model-run task-success measurements.",
        ],
        "input_digests": [_file_digest(path) for path in input_paths],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }


def _find_row(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    for row in rows:
        if row["policy"] == policy:
            return row
    raise KeyError(policy)


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


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 8) if denominator else 0.0


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
    return " ".join([os.path.basename(sys.executable), *sys.argv])


if __name__ == "__main__":
    raise SystemExit(main())
