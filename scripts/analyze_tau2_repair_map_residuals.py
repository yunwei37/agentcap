"""Audit R136 repair-map execution residuals.

This is a saved-artifact analysis over the local tau2 compiler task loop. It
does not run a model, execute tools, clone benchmarks, sync datasets, or mint
authority. Its purpose is to explain why feeding the R135 repair map into R136
raised safe exact executions but still left official tau2 utility at 0/11.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.analyze_tau2_compiler_recall_gap as recall_analyzer
import scripts.analyze_tau2_missing_reference_actionability as actionability_analyzer
import scripts.analyze_tau2_residual_completion as residual_analyzer
import scripts.analyze_tau2_task_gateway_mismatches as mismatch_analyzer
import scripts.score_tau2_invalid_reference_oracle as adjusted_scorer


REPAIR_EXECUTION_FIELDS = [
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "repair_class",
    "candidate_source",
    "earliest_synthesis_step",
    "execution_status",
    "executed_by_repair_map_fallback",
    "executed_by_any_path",
    "still_missing_after_source_run",
    "previous_actionability_class",
    "current_actionability_class",
    "current_next_experiment_target",
    "current_db_feasible",
    "current_feasibility",
    "action_round",
    "action_index",
    "runtime_binding_allowed",
]

TASK_RESIDUAL_FIELDS = [
    *actionability_analyzer.TASK_FIELDS,
    "source_run_tool_oracle_pass",
    "source_run_all_reference_actions_executed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit R136 repair-map residuals")
    parser.add_argument("--run-id", default="R137")
    parser.add_argument("--source-run-dir", type=Path, default=Path("results/eval/R136"))
    parser.add_argument(
        "--repair-map-csv",
        type=Path,
        default=Path("results/eval/R135/candidate_generation_repair_map.csv"),
    )
    parser.add_argument(
        "--previous-actionability-csv",
        type=Path,
        default=Path("results/eval/R134/missing_reference_actionability.csv"),
    )
    parser.add_argument(
        "--candidate-csv",
        type=Path,
        default=Path("results/eval/R131/runtime_evidence_candidate_correctness.csv"),
    )
    parser.add_argument(
        "--feasibility-csv",
        type=Path,
        default=Path("results/eval/R067/reference_feasibility.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R137"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_repair_map_residuals(
        run_id=args.run_id,
        source_run_dir=args.source_run_dir,
        repair_map_csv=args.repair_map_csv,
        previous_actionability_csv=args.previous_actionability_csv,
        candidate_csv=args.candidate_csv,
        feasibility_csv=args.feasibility_csv,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_repair_map_residuals(
    *,
    run_id: str,
    source_run_dir: Path,
    repair_map_csv: Path,
    previous_actionability_csv: Path,
    candidate_csv: Path,
    feasibility_csv: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    mismatch_result = mismatch_analyzer.analyze_runs((source_run_dir,), run_id=f"{run_id}_mismatch")
    residual_result = residual_analyzer.analyze_run(source_run_dir, run_id=f"{run_id}_residual")
    adjusted_task_rows = adjusted_scorer.score_task_rows(
        run_id=f"{run_id}_adjusted",
        residual_rows=residual_result["task_rows"],
        feasibility_rows=read_csv(feasibility_csv),
    )
    adjusted_summary = adjusted_scorer._summary(
        run_id=f"{run_id}_adjusted",
        residual_dir=output_dir / "residual",
        feasibility_dir=feasibility_csv.parent,
        source_run_dir=source_run_dir,
        task_rows=adjusted_task_rows,
    )
    recall_result = recall_analyzer.analyze_run(source_run_dir, run_id=f"{run_id}_recall")

    residual_dir = output_dir / "residual"
    adjusted_dir = output_dir / "adjusted"
    recall_dir = output_dir / "recall"
    actionability_dir = output_dir / "actionability"
    mismatch_dir = output_dir / "mismatch"
    for directory in [residual_dir, adjusted_dir, recall_dir, actionability_dir, mismatch_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    write_csv(mismatch_dir / "model_call_mismatches.csv", mismatch_result["call_rows"], mismatch_analyzer.CALL_FIELDS)
    write_csv(mismatch_dir / "task_mismatch_summary.csv", mismatch_result["task_rows"], mismatch_analyzer.TASK_FIELDS)
    write_csv(mismatch_dir / "run_mismatch_summary.csv", mismatch_result["run_rows"], mismatch_analyzer.RUN_FIELDS)
    write_csv(mismatch_dir / "argument_key_mismatches.csv", mismatch_result["argument_key_rows"], mismatch_analyzer.ARG_KEY_FIELDS)
    write_json(mismatch_dir / "tau2_task_gateway_mismatch_summary.json", mismatch_result["summary"])

    write_csv(residual_dir / "task_residual_completion.csv", residual_result["task_rows"], residual_analyzer.TASK_FIELDS)
    write_csv(residual_dir / "missing_reference_actions.csv", residual_result["missing_rows"], residual_analyzer.MISSING_FIELDS)
    write_json(residual_dir / "tau2_residual_completion_summary.json", residual_result["summary"])

    write_csv(adjusted_dir / "invalid_reference_adjusted_tasks.csv", adjusted_task_rows, adjusted_scorer.TASK_FIELDS)
    write_json(adjusted_dir / "tau2_invalid_reference_oracle_summary.json", adjusted_summary)

    write_csv(recall_dir / "task_compiler_recall_gap.csv", recall_result["task_rows"], recall_analyzer.TASK_FIELDS)
    write_csv(recall_dir / "missing_compiler_recall_gap.csv", recall_result["missing_rows"], recall_analyzer.MISSING_FIELDS)
    write_json(recall_dir / "tau2_compiler_recall_gap_summary.json", recall_result["summary"])

    actionability_result = actionability_analyzer.analyze_actionability(
        missing_csv=recall_dir / "missing_compiler_recall_gap.csv",
        candidate_csv=candidate_csv,
        feasibility_csv=feasibility_csv,
        adjusted_task_csv=adjusted_dir / "invalid_reference_adjusted_tasks.csv",
        run_id=f"{run_id}_actionability",
    )
    write_csv(
        actionability_dir / "missing_reference_actionability.csv",
        actionability_result["missing_rows"],
        actionability_analyzer.MISSING_FIELDS,
    )
    write_csv(
        actionability_dir / "task_missing_reference_actionability.csv",
        actionability_result["task_rows"],
        actionability_analyzer.TASK_FIELDS,
    )
    write_json(
        actionability_dir / "missing_reference_actionability_summary.json",
        actionability_result["summary"],
    )

    repair_rows = classify_repair_map_execution(
        repair_rows=eligible_repair_rows(read_csv(repair_map_csv)),
        action_rows=read_csv(source_run_dir / "action_results.csv"),
        previous_actionability_rows=read_csv(previous_actionability_csv),
        current_actionability_rows=actionability_result["missing_rows"],
    )
    task_rows = enrich_task_rows(
        actionability_result["task_rows"],
        residual_result["task_rows"],
    )
    summary = build_summary(
        run_id=run_id,
        source_run_dir=source_run_dir,
        repair_map_csv=repair_map_csv,
        previous_actionability_csv=previous_actionability_csv,
        candidate_csv=candidate_csv,
        feasibility_csv=feasibility_csv,
        mismatch_summary=mismatch_result["summary"],
        residual_summary=residual_result["summary"],
        adjusted_summary=adjusted_summary,
        recall_summary=recall_result["summary"],
        actionability_summary=actionability_result["summary"],
        repair_rows=repair_rows,
    )

    write_csv(output_dir / "repair_map_candidate_execution.csv", repair_rows, REPAIR_EXECUTION_FIELDS)
    write_csv(
        output_dir / "remaining_missing_actionability.csv",
        actionability_result["missing_rows"],
        actionability_analyzer.MISSING_FIELDS,
    )
    write_csv(output_dir / "task_repair_residuals.csv", task_rows, TASK_RESIDUAL_FIELDS)
    write_json(output_dir / "r136_repair_map_residual_summary.json", summary)
    write_csv(
        output_dir / "input_digests.csv",
        input_digest_rows(
            [
                source_run_dir / "task_gateway_summary.json",
                source_run_dir / "samples.jsonl",
                source_run_dir / "action_results.csv",
                repair_map_csv,
                previous_actionability_csv,
                candidate_csv,
                feasibility_csv,
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    return {
        "summary": summary,
        "repair_rows": repair_rows,
        "task_rows": task_rows,
        "actionability_rows": actionability_result["missing_rows"],
    }


def eligible_repair_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if truthy(row.get("eligible", "")) and row.get("proof_status") == "repair_candidate_ready"
    ]


def classify_repair_map_execution(
    *,
    repair_rows: list[dict[str, str]],
    action_rows: list[dict[str, str]],
    previous_actionability_rows: list[dict[str, str]],
    current_actionability_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions_by_bound = {
        str(row.get("bound_reference_event_id", "")): row
        for row in action_rows
        if truthy(row.get("executed", "")) and row.get("bound_reference_event_id")
    }
    repair_marker_events: dict[str, dict[str, str]] = {}
    for row in action_rows:
        markers = json_dict(row.get("intentcap_markers_json", "{}"))
        if markers.get("_intentcap_synthesized_from_repair_map"):
            event_id = str(markers.get("_intentcap_repair_map_event_id", ""))
            if event_id:
                repair_marker_events[event_id] = row

    previous_by_event = {str(row.get("event_id", "")): row for row in previous_actionability_rows}
    current_by_event = {str(row.get("event_id", "")): row for row in current_actionability_rows}

    classified: list[dict[str, Any]] = []
    for row in repair_rows:
        event_id = str(row.get("event_id", ""))
        current = current_by_event.get(event_id, {})
        previous = previous_by_event.get(event_id, {})
        marker_action = repair_marker_events.get(event_id)
        any_action = actions_by_bound.get(event_id)
        executed_by_marker = marker_action is not None
        executed_by_any = any_action is not None
        if executed_by_marker:
            status = "repair_map_fallback_executed"
            action = marker_action
        elif executed_by_any:
            status = "executed_by_other_path"
            action = any_action
        else:
            status = "not_executed"
            action = {}
        classified.append(
            {
                "domain": str(row.get("domain", "")),
                "task_id": str(row.get("task_id", "")),
                "event_id": event_id,
                "tool": str(row.get("tool", "")),
                "args_json": str(row.get("args_json", "")),
                "repair_class": str(row.get("repair_class", "")),
                "candidate_source": str(row.get("candidate_source", "")),
                "earliest_synthesis_step": str(row.get("earliest_synthesis_step", "")),
                "execution_status": status,
                "executed_by_repair_map_fallback": executed_by_marker,
                "executed_by_any_path": executed_by_any,
                "still_missing_after_source_run": event_id in current_by_event,
                "previous_actionability_class": str(previous.get("actionability_class", "")),
                "current_actionability_class": str(current.get("actionability_class", "")),
                "current_next_experiment_target": str(current.get("next_experiment_target", "")),
                "current_db_feasible": str(current.get("db_feasible", "")),
                "current_feasibility": str(current.get("feasibility", "")),
                "action_round": str(action.get("round", "")),
                "action_index": str(action.get("index", "")),
                "runtime_binding_allowed": str(action.get("runtime_binding_allowed", "")),
            }
        )
    return classified


def enrich_task_rows(
    actionability_task_rows: list[dict[str, Any]],
    residual_task_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    residual_by_key = {
        (str(row.get("source_run_id", "")), str(row.get("domain", "")), str(row.get("task_id", ""))): row
        for row in residual_task_rows
    }
    enriched: list[dict[str, Any]] = []
    for row in actionability_task_rows:
        key = (
            str(row.get("source_run_id", "")),
            str(row.get("domain", "")),
            str(row.get("task_id", "")),
        )
        residual = residual_by_key.get(key, {})
        enriched.append(
            {
                **row,
                "source_run_tool_oracle_pass": str(residual.get("tool_oracle_pass", "")),
                "source_run_all_reference_actions_executed": str(
                    residual.get("all_reference_actions_executed", "")
                ),
            }
        )
    return enriched


def build_summary(
    *,
    run_id: str,
    source_run_dir: Path,
    repair_map_csv: Path,
    previous_actionability_csv: Path,
    candidate_csv: Path,
    feasibility_csv: Path,
    mismatch_summary: dict[str, Any],
    residual_summary: dict[str, Any],
    adjusted_summary: dict[str, Any],
    recall_summary: dict[str, Any],
    actionability_summary: dict[str, Any],
    repair_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    repair_status_counts = Counter(str(row["execution_status"]) for row in repair_rows)
    previous_rows = read_csv(previous_actionability_csv)
    previous_db_feasible = sum(1 for row in previous_rows if truthy(row.get("db_feasible", "")))
    current_db_feasible = int(actionability_summary.get("missing_db_feasible_reference_actions", 0))
    repair_still_missing = sum(1 for row in repair_rows if row["still_missing_after_source_run"])
    return {
        "run_id": run_id,
        "analysis": "saved R136 repair-map execution residual audit",
        "source_run": source_run_dir.name,
        "source_run_dir": str(source_run_dir),
        "repair_map_csv": str(repair_map_csv),
        "previous_actionability_csv": str(previous_actionability_csv),
        "candidate_csv": str(candidate_csv),
        "feasibility_csv": str(feasibility_csv),
        "no_dataset_sync": True,
        "no_model_execution": True,
        "no_tool_execution": True,
        "repair_map_eligible_candidates": len(repair_rows),
        "repair_map_execution_status_counts": dict(sorted(repair_status_counts.items())),
        "repair_map_fallback_executed_candidates": repair_status_counts[
            "repair_map_fallback_executed"
        ],
        "repair_map_candidates_executed_by_any_path": sum(
            1 for row in repair_rows if row["executed_by_any_path"]
        ),
        "repair_map_candidates_not_executed": repair_status_counts["not_executed"],
        "repair_map_candidates_still_missing_after_source_run": repair_still_missing,
        "previous_db_feasible_missing_reference_actions": previous_db_feasible,
        "current_db_feasible_missing_reference_actions": current_db_feasible,
        "db_feasible_missing_reduction_vs_previous": previous_db_feasible
        - current_db_feasible,
        "source_exact_executed_calls": int(mismatch_summary.get("exact_executed_calls", 0)),
        "source_off_lease_calls": int(mismatch_summary.get("off_lease_calls", 0)),
        "source_same_tool_wrong_args_calls": int(
            mismatch_summary.get("category_counts", {}).get(
                "off_lease_same_tool_wrong_args", 0
            )
        ),
        "source_wrong_or_hallucinated_tool_calls": int(
            mismatch_summary.get("category_counts", {}).get(
                "off_lease_wrong_or_hallucinated_tool", 0
            )
        ),
        "source_off_lease_category_counts": dict(
            sorted(
                {
                    key: value
                    for key, value in mismatch_summary.get("category_counts", {}).items()
                    if key != "exact_executed"
                }.items()
            )
        ),
        "source_missing_reference_actions": int(
            residual_summary.get("missing_reference_actions", 0)
        ),
        "source_executed_reference_actions": int(
            residual_summary.get("executed_reference_actions", 0)
        ),
        "source_tool_oracle_pass_tasks": int(
            adjusted_summary.get("official_tool_oracle_pass_tasks", 0)
        ),
        "source_adjusted_action_env_pass_tasks": int(
            adjusted_summary.get("adjusted_action_env_pass_tasks", 0)
        ),
        "source_db_feasible_reference_complete_tasks": int(
            adjusted_summary.get("db_feasible_reference_complete_tasks", 0)
        ),
        "source_reward_residual_tasks_without_missing_action": int(
            actionability_summary.get("reward_residual_tasks_without_missing_action", 0)
        ),
        "recall_missing_gap_class_counts": dict(
            sorted(recall_summary.get("missing_gap_class_counts", {}).items())
        ),
        "current_db_feasible_actionability_class_counts": dict(
            sorted(
                actionability_summary.get(
                    "db_feasible_actionability_class_counts", {}
                ).items()
            )
        ),
        "current_task_primary_actionability_counts": dict(
            sorted(actionability_summary.get("task_primary_actionability_counts", {}).items())
        ),
        "next_mechanism_priority": [
            "generate_runtime_candidates_for_visible_tool_argument_evidence",
            "add_planner_candidate_correctness_before_execution",
            "activate_or_compile_missing_tools_when_argument_evidence_exists",
            "gather_missing_argument_evidence",
            "debug_reward_env_residuals_after_reference_completion",
        ],
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256_path(Path(__file__)),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This is an offline saved-artifact audit over R136 and earlier diagnostic CSVs.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or reveal hidden references to a model.",
            "Reference labels are used only to measure post-hoc exactness and residual actionability.",
            "The result supports a residual-diagnosis claim, not non-oracle utility success.",
        ],
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_dict(raw: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def input_digest_rows(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {"path": str(path), "sha256": sha256_path(path), "bytes": path_size(path)}
        for path in paths
        if path.exists()
    ]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    return digest.hexdigest()


def path_size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else 0


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
