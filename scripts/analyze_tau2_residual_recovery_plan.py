"""Build an R137-directed residual recovery candidate plan.

R137 showed that the first repair-map execution closed part of the tau2
compiler gap but left 25 DB-feasible missing actions. This script prepares the
next bounded recovery input without running a model, executing tools, syncing
datasets, or minting authority. It combines two recoverable buckets:

* runtime-candidate-generation gaps whose tool and argument values are visible
  in the saved R136 prompt/tool-result state; and
* candidate-selection/planning gaps where an exact-next runtime candidate was
  already labeled in the saved R131 pool but was not executed in R136.

The emitted candidate map keeps the R135 repair-map columns so it can be fed to
the existing task-loop repair-map fallback in a later execution experiment.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.analyze_tau2_candidate_generation_repair as repair_analyzer


EXTRA_RECOVERY_FIELDS = [
    "recovery_kind",
    "planner_candidate_step",
    "planner_candidate_rank_position",
    "planner_candidate_rank_score",
    "planner_candidate_source_run_id",
    "planner_candidate_proof_status",
    "planner_candidate_lease_template_id",
]

RECOVERY_FIELDS = [*repair_analyzer.REPAIR_FIELDS, *EXTRA_RECOVERY_FIELDS]

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "eligible_recovery_candidates",
    "generated_recovery_candidates",
    "existing_exact_candidate_recoveries",
    "high_impact_recovery_candidates",
    "recovery_event_ids",
    "primary_recovery_kind",
    "not_yet_actionable_db_feasible_missing_actions",
    "reward_residual_not_missing_action",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build R137 residual recovery candidate plan")
    parser.add_argument("--run-id", default="R138")
    parser.add_argument(
        "--actionability-csv",
        type=Path,
        default=Path("results/eval/R137/remaining_missing_actionability.csv"),
    )
    parser.add_argument(
        "--task-residual-csv",
        type=Path,
        default=Path("results/eval/R137/task_repair_residuals.csv"),
    )
    parser.add_argument(
        "--candidate-csv",
        type=Path,
        default=Path("results/eval/R131/runtime_evidence_candidate_correctness.csv"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("results/eval/R136"),
        help="Saved task-loop run directory containing samples.jsonl and step prompts.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R138"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_residual_recovery_plan(
        run_id=args.run_id,
        actionability_csv=args.actionability_csv,
        task_residual_csv=args.task_residual_csv,
        candidate_csv=args.candidate_csv,
        run_dir=args.run_dir,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "residual_recovery_candidate_map.csv",
        result["candidate_rows"],
        RECOVERY_FIELDS,
    )
    write_csv(
        args.output_dir / "candidate_generation_repair_map.csv",
        result["candidate_rows"],
        RECOVERY_FIELDS,
    )
    write_csv(
        args.output_dir / "not_yet_candidate_ready_residuals.csv",
        result["not_yet_candidate_rows"],
        result["not_yet_candidate_fields"],
    )
    write_csv(
        args.output_dir / "task_residual_recovery_plan.csv",
        result["task_rows"],
        TASK_FIELDS,
    )
    write_json(args.output_dir / "residual_recovery_plan_summary.json", result["summary"])
    write_csv(
        args.output_dir / "input_digests.csv",
        input_digest_rows(
            [
                args.actionability_csv,
                args.task_residual_csv,
                args.candidate_csv,
                args.run_dir / "samples.jsonl",
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (args.output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_residual_recovery_plan(
    *,
    run_id: str,
    actionability_csv: Path,
    task_residual_csv: Path,
    candidate_csv: Path,
    run_dir: Path,
) -> dict[str, Any]:
    actionability_rows = read_csv(actionability_csv)
    task_residual_rows = read_csv(task_residual_csv)
    candidate_label_rows = read_csv(candidate_csv)

    generation_result = repair_analyzer.analyze_repair_map(
        actionability_csv=actionability_csv,
        run_dir=run_dir,
        run_id=f"{run_id}_candidate_generation",
    )
    generated_rows = [
        enrich_generated_row(row)
        for row in generation_result["repair_rows"]
        if truthy(row.get("eligible", "")) and row.get("proof_status") == "repair_candidate_ready"
    ]
    records_by_task = repair_analyzer.load_records_by_task(run_dir)
    planner_rows = build_existing_exact_candidate_rows(
        actionability_rows=actionability_rows,
        candidate_label_rows=candidate_label_rows,
        records_by_task=records_by_task,
        run_dir=run_dir,
    )
    candidate_rows = sort_candidate_rows([*generated_rows, *planner_rows])
    handled_event_ids = {str(row.get("event_id", "")) for row in candidate_rows}
    not_yet_candidate_rows = [
        {**row, "residual_blocker": residual_blocker(row)}
        for row in actionability_rows
        if truthy(row.get("db_feasible", ""))
        and str(row.get("event_id", "")) not in handled_event_ids
    ]
    task_rows = build_task_rows(candidate_rows, not_yet_candidate_rows, task_residual_rows)
    summary = build_summary(
        run_id=run_id,
        actionability_csv=actionability_csv,
        task_residual_csv=task_residual_csv,
        candidate_csv=candidate_csv,
        run_dir=run_dir,
        actionability_rows=actionability_rows,
        candidate_rows=candidate_rows,
        generated_rows=generated_rows,
        planner_rows=planner_rows,
        not_yet_candidate_rows=not_yet_candidate_rows,
        task_rows=task_rows,
        task_residual_rows=task_residual_rows,
    )
    not_yet_fields = [*fieldnames_from_rows(actionability_rows), "residual_blocker"]
    return {
        "candidate_rows": candidate_rows,
        "not_yet_candidate_rows": not_yet_candidate_rows,
        "not_yet_candidate_fields": not_yet_fields,
        "task_rows": task_rows,
        "summary": summary,
    }


def enrich_generated_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "recovery_kind": "generate_runtime_candidate_from_visible_state",
        "planner_candidate_step": "",
        "planner_candidate_rank_position": "",
        "planner_candidate_rank_score": "",
        "planner_candidate_source_run_id": "",
        "planner_candidate_proof_status": "",
        "planner_candidate_lease_template_id": "",
    }


def build_existing_exact_candidate_rows(
    *,
    actionability_rows: list[dict[str, str]],
    candidate_label_rows: list[dict[str, str]],
    records_by_task: dict[tuple[str, str], dict[str, Any]],
    run_dir: Path,
) -> list[dict[str, Any]]:
    candidates_by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for candidate in candidate_label_rows:
        event_id = str(candidate.get("exact_reference_event_id", ""))
        if event_id:
            candidates_by_event[event_id].append(candidate)

    rows: list[dict[str, Any]] = []
    for row in actionability_rows:
        if str(row.get("actionability_class", "")) != "candidate_selection_or_planning_gap":
            continue
        rows.append(
            classify_existing_exact_candidate_row(
                row=row,
                candidates=candidates_by_event.get(str(row.get("event_id", "")), []),
                record=records_by_task.get(repair_analyzer.task_key(row), {}),
                run_dir=run_dir,
            )
        )
    return rows


def classify_existing_exact_candidate_row(
    *,
    row: dict[str, str],
    candidates: list[dict[str, str]],
    record: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    args = repair_analyzer.parse_json_object(row.get("args_json", "{}"))
    tool = str(row.get("tool", ""))
    visible_candidate_steps = set(repair_analyzer.parse_steps(row.get("runtime_exact_next_candidate_steps", "")))
    visible_candidate_steps &= set(repair_analyzer.parse_steps(row.get("tool_visible_steps", "")))
    visible_candidate_steps &= set(repair_analyzer.parse_steps(row.get("all_arg_evidence_steps", "")))
    matches = [
        candidate
        for candidate in candidates
        if str(candidate.get("candidate_correctness", "")) == "exact_next_reference"
        and str(candidate.get("tool", "")) == tool
        and repair_analyzer.parse_json_object(candidate.get("args_json", "{}")) == args
        and truthy(candidate.get("complete_arguments", ""))
        and truthy(candidate.get("proof_complete", ""))
        and (not visible_candidate_steps or str(candidate.get("step", "")) in visible_candidate_steps)
    ]
    matches.sort(key=candidate_sort_key)
    selected = matches[0] if matches else {}
    candidate_args = repair_analyzer.parse_json_object(selected.get("args_json", "{}")) if selected else args
    selected_step = str(selected.get("step", ""))
    if not selected_step and visible_candidate_steps:
        selected_step = repair_analyzer.sorted_steps(visible_candidate_steps)[0]

    contexts = repair_analyzer.prompt_contexts_from_record(record, run_dir=run_dir) if record else []
    context_by_step = {str(context["step"]): context for context in contexts}
    selected_context = context_by_step.get(selected_step, {})
    tool_schema = repair_analyzer.find_tool_schema(selected_context, tool)
    required_args = list(((tool_schema.get("parameters") or {}).get("required") or []))
    required_satisfied = all(arg in candidate_args for arg in required_args)
    arg_value_sources = repair_analyzer.value_sources(candidate_args, selected_context)
    all_values_visible = all(source.get("sources") for source in arg_value_sources.values())
    exact_match = candidate_args == args
    eligible = bool(selected) and bool(tool_schema) and required_satisfied and all_values_visible and exact_match
    proof_status = existing_candidate_proof_status(
        selected=selected,
        tool_schema=bool(tool_schema),
        required_satisfied=required_satisfied,
        all_values_visible=all_values_visible,
        exact_match=exact_match,
        eligible=eligible,
    )

    return {
        "source_run_id": str(row.get("source_run_id", "")),
        "domain": str(row.get("domain", "")),
        "task_id": str(row.get("task_id", "")),
        "event_id": str(row.get("event_id", "")),
        "tool": tool,
        "args_json": json.dumps(args, sort_keys=True),
        "actionability_class": str(row.get("actionability_class", "")),
        "repair_class": "planner_select_existing_exact_candidate",
        "eligible": eligible,
        "earliest_synthesis_step": selected_step,
        "synthesis_steps": "|".join(repair_analyzer.sorted_steps(visible_candidate_steps)),
        "tool_visible_steps": str(row.get("tool_visible_steps", "")),
        "all_arg_evidence_steps": str(row.get("all_arg_evidence_steps", "")),
        "complete_compiler_hint_steps": str(row.get("complete_compiler_hint_steps", "")),
        "candidate_json": json.dumps({"tool": tool, "arguments": candidate_args}, sort_keys=True),
        "candidate_source": "saved_exact_next_runtime_candidate_label",
        "candidate_exact_reference_match": exact_match,
        "tool_schema_available": bool(tool_schema),
        "required_args": "|".join(str(arg) for arg in required_args),
        "schema_required_args_satisfied": required_satisfied,
        "all_arg_values_visible_in_step": all_values_visible,
        "arg_value_sources_json": json.dumps(arg_value_sources, sort_keys=True),
        "proof_status": proof_status,
        "next_experiment_target": "planner_confirm_existing_exact_candidate_before_generation",
        "recovery_kind": "planner_select_existing_exact_candidate",
        "planner_candidate_step": selected_step,
        "planner_candidate_rank_position": str(selected.get("rank_position", "")),
        "planner_candidate_rank_score": str(selected.get("rank_score", "")),
        "planner_candidate_source_run_id": str(selected.get("source_run_id", "")),
        "planner_candidate_proof_status": str(selected.get("proof_status", "")),
        "planner_candidate_lease_template_id": str(selected.get("lease_template_id", "")),
    }


def candidate_sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    return (
        int_or_large(row.get("step", "")),
        int_or_large(row.get("rank_position", "")),
        json.dumps(repair_analyzer.parse_json_object(row.get("args_json", "{}")), sort_keys=True),
    )


def existing_candidate_proof_status(
    *,
    selected: dict[str, str],
    tool_schema: bool,
    required_satisfied: bool,
    all_values_visible: bool,
    exact_match: bool,
    eligible: bool,
) -> str:
    if not selected:
        return "missing_existing_exact_next_candidate"
    if not tool_schema:
        return "missing_tool_schema_at_planner_step"
    if not required_satisfied:
        return "missing_required_argument"
    if not all_values_visible:
        return "missing_visible_argument_value"
    if not exact_match:
        return "existing_candidate_does_not_match_reference"
    if eligible:
        return "repair_candidate_ready"
    return "not_repairable_by_this_stage"


def build_task_rows(
    candidate_rows: list[dict[str, Any]],
    not_yet_candidate_rows: list[dict[str, Any]],
    task_residual_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    candidate_by_task: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        candidate_by_task[(str(row.get("domain", "")), str(row.get("task_id", "")))].append(row)
    blockers_by_task: Counter[tuple[str, str]] = Counter(
        (str(row.get("domain", "")), str(row.get("task_id", ""))) for row in not_yet_candidate_rows
    )
    reward_residual_by_task = {
        (str(row.get("domain", "")), str(row.get("task_id", ""))): truthy(
            row.get("reward_residual_not_missing_action", "")
        )
        for row in task_residual_rows
    }
    all_keys = sorted(set(candidate_by_task) | set(blockers_by_task) | set(reward_residual_by_task))
    task_rows: list[dict[str, Any]] = []
    for domain, task_id in all_keys:
        rows = candidate_by_task.get((domain, task_id), [])
        counts = Counter(str(row.get("recovery_kind", "")) for row in rows if truthy(row.get("eligible", "")))
        task_rows.append(
            {
                "source_run_id": str(rows[0].get("source_run_id", "")) if rows else "",
                "domain": domain,
                "task_id": task_id,
                "eligible_recovery_candidates": sum(counts.values()),
                "generated_recovery_candidates": counts["generate_runtime_candidate_from_visible_state"],
                "existing_exact_candidate_recoveries": counts["planner_select_existing_exact_candidate"],
                "high_impact_recovery_candidates": sum(
                    1
                    for row in rows
                    if truthy(row.get("eligible", ""))
                    and repair_analyzer.is_high_impact_tool(str(row.get("tool", "")))
                ),
                "recovery_event_ids": "|".join(
                    str(row.get("event_id", "")) for row in rows if truthy(row.get("eligible", ""))
                ),
                "primary_recovery_kind": primary_recovery_kind(counts),
                "not_yet_actionable_db_feasible_missing_actions": blockers_by_task[(domain, task_id)],
                "reward_residual_not_missing_action": reward_residual_by_task.get((domain, task_id), False),
            }
        )
    return task_rows


def build_summary(
    *,
    run_id: str,
    actionability_csv: Path,
    task_residual_csv: Path,
    candidate_csv: Path,
    run_dir: Path,
    actionability_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, Any]],
    generated_rows: list[dict[str, Any]],
    planner_rows: list[dict[str, Any]],
    not_yet_candidate_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    task_residual_rows: list[dict[str, str]],
) -> dict[str, Any]:
    db_feasible_rows = [row for row in actionability_rows if truthy(row.get("db_feasible", ""))]
    eligible_rows = [row for row in candidate_rows if truthy(row.get("eligible", ""))]
    class_counts = Counter(str(row.get("actionability_class", "")) for row in db_feasible_rows)
    not_ready_counts = Counter(str(row.get("actionability_class", "")) for row in not_yet_candidate_rows)
    recovery_counts = Counter(str(row.get("recovery_kind", "")) for row in eligible_rows)
    reward_residual_tasks = [
        row for row in task_residual_rows if truthy(row.get("reward_residual_not_missing_action", ""))
    ]
    return {
        "run_id": run_id,
        "analysis": "R137-directed saved residual recovery candidate plan",
        "actionability_csv": str(actionability_csv),
        "task_residual_csv": str(task_residual_csv),
        "candidate_csv": str(candidate_csv),
        "run_dir": str(run_dir),
        "no_dataset_sync": True,
        "no_model_run": True,
        "no_tool_execution": True,
        "db_feasible_missing_actions_before_plan": len(db_feasible_rows),
        "db_feasible_actionability_class_counts": dict(sorted(class_counts.items())),
        "eligible_recovery_candidates": len(eligible_rows),
        "eligible_generated_runtime_candidates": len(
            [row for row in generated_rows if truthy(row.get("eligible", ""))]
        ),
        "eligible_existing_exact_candidate_recoveries": len(
            [row for row in planner_rows if truthy(row.get("eligible", ""))]
        ),
        "eligible_high_impact_recovery_candidates": sum(
            1
            for row in eligible_rows
            if repair_analyzer.is_high_impact_tool(str(row.get("tool", "")))
        ),
        "tasks_with_recovery_candidates": len(
            {(str(row.get("domain", "")), str(row.get("task_id", ""))) for row in eligible_rows}
        ),
        "recovery_kind_counts": dict(sorted(recovery_counts.items())),
        "not_yet_candidate_ready_db_feasible_missing_actions": len(not_yet_candidate_rows),
        "not_yet_candidate_ready_class_counts": dict(sorted(not_ready_counts.items())),
        "potential_db_feasible_missing_after_recovery_plan": len(not_yet_candidate_rows),
        "reward_residual_tasks_without_missing_action": len(reward_residual_tasks),
        "task_primary_recovery_kind_counts": dict(
            sorted(Counter(str(row.get("primary_recovery_kind", "")) for row in task_rows).items())
        ),
        "next_execution_input": "results/eval/R138/candidate_generation_repair_map.csv",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256(Path(__file__).read_bytes()),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This is an offline R137 residual recovery-plan analysis.",
            "Reference arguments and exact-next labels are used only as post-hoc exactness targets.",
            "The emitted candidate map is compatible with the existing repair-map task-loop fallback.",
            "The result supports a next-execution-input claim, not non-oracle utility success.",
        ],
    }


def residual_blocker(row: dict[str, Any]) -> str:
    actionability_class = str(row.get("actionability_class", ""))
    if actionability_class == "tool_activation_gap":
        return "tool_not_active_or_not_compiled"
    if actionability_class == "argument_evidence_gap":
        return "argument_value_not_visible_in_saved_context"
    if actionability_class == "upstream_planning_gap":
        return "upstream_action_needed_before_candidate_can_be_grounded"
    return actionability_class or "unclassified"


def primary_recovery_kind(counts: Counter[str]) -> str:
    for recovery_kind in (
        "planner_select_existing_exact_candidate",
        "generate_runtime_candidate_from_visible_state",
    ):
        if counts[recovery_kind]:
            return recovery_kind
    return "none"


def sort_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("domain", "")),
            str(row.get("task_id", "")),
            int_or_large(row.get("earliest_synthesis_step", "")),
            str(row.get("event_id", "")),
        ),
    )


def fieldnames_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return list(rows[0].keys())


def int_or_large(value: Any) -> int:
    text = str(value or "")
    return int(text) if text.isdigit() else 10**9


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


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


def input_digest_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        data = path.read_bytes()
        rows.append({"path": str(path), "sha256": sha256(data), "bytes": len(data)})
    return rows


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
