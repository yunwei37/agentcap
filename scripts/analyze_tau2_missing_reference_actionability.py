"""Classify tau2 missing-reference actionability across saved diagnostics.

This is an offline roll-up over saved R125/R128/R129/R131/R067 artifacts.  It
does not run models, execute tools, clone benchmarks, sync datasets, or use
reference labels to mint runtime authority.  Its purpose is to turn the current
0/11 non-oracle utility failure into an actionable repair map: selection over
existing candidates, runtime candidate generation, tool activation, argument
evidence gathering, upstream planning, invalid-reference cleanup, or reward
residual debugging.
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


MISSING_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "reference_index",
    "event_id",
    "tool",
    "args_json",
    "arg_values",
    "feasibility",
    "feasibility_source",
    "invalid_reference",
    "db_feasible",
    "compiler_gap_class",
    "complete_compiler_hint_steps",
    "partial_compiler_hint_steps",
    "tool_visible_steps",
    "all_arg_evidence_steps",
    "any_arg_evidence_steps",
    "task_arg_evidence",
    "missing_arg_values_from_prompt_evidence",
    "runtime_exact_candidate_count",
    "runtime_exact_candidate_steps",
    "runtime_exact_next_candidate_steps",
    "runtime_exact_future_candidate_steps",
    "runtime_selected_steps",
    "runtime_ranked_fallback_steps",
    "runtime_executed_steps",
    "runtime_top_rank",
    "runtime_top_correctness",
    "runtime_candidate_correctness_counts",
    "actionability_class",
    "next_experiment_target",
]

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "adjusted_category",
    "official_reference_actions",
    "invalid_reference_actions",
    "db_feasible_reference_actions",
    "official_executed_reference_actions",
    "executed_db_feasible_reference_actions",
    "official_missing_reference_actions",
    "missing_db_feasible_reference_actions",
    "db_feasible_reference_complete",
    "official_tool_oracle_pass",
    "official_action_reward",
    "official_env_reward",
    "adjusted_action_env_pass",
    "missing_rows",
    "missing_db_feasible_rows",
    "invalid_missing_rows",
    "candidate_selection_or_planning_gap",
    "complete_compiler_hint_not_called",
    "runtime_candidate_generation_gap",
    "tool_activation_gap",
    "argument_evidence_gap",
    "upstream_planning_gap",
    "reward_residual_not_missing_action",
    "primary_actionability_class",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify broader tau2 missing-reference actionability gaps"
    )
    parser.add_argument("--run-id", default="R134")
    parser.add_argument(
        "--missing-csv",
        type=Path,
        default=Path("results/eval/R129/missing_compiler_recall_gap.csv"),
        help="Saved R129 missing-reference compiler-recall CSV.",
    )
    parser.add_argument(
        "--candidate-csv",
        type=Path,
        default=Path("results/eval/R131/runtime_evidence_candidate_correctness.csv"),
        help="Saved R131 runtime-evidence candidate correctness CSV.",
    )
    parser.add_argument(
        "--feasibility-csv",
        type=Path,
        default=Path("results/eval/R067/reference_feasibility.csv"),
        help="Saved R067 reference feasibility audit CSV.",
    )
    parser.add_argument(
        "--adjusted-task-csv",
        type=Path,
        default=Path("results/eval/R128/invalid_reference_adjusted_tasks.csv"),
        help="Saved R128 invalid-reference-adjusted task accounting CSV.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R134"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_actionability(
        missing_csv=args.missing_csv,
        candidate_csv=args.candidate_csv,
        feasibility_csv=args.feasibility_csv,
        adjusted_task_csv=args.adjusted_task_csv,
        run_id=args.run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "missing_reference_actionability.csv",
        result["missing_rows"],
        MISSING_FIELDS,
    )
    write_csv(
        args.output_dir / "task_missing_reference_actionability.csv",
        result["task_rows"],
        TASK_FIELDS,
    )
    (args.output_dir / "missing_reference_actionability_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(
        args.output_dir / "input_digests.csv",
        input_digest_rows(
            [
                args.missing_csv,
                args.candidate_csv,
                args.feasibility_csv,
                args.adjusted_task_csv,
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (args.output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_actionability(
    *,
    missing_csv: Path,
    candidate_csv: Path,
    feasibility_csv: Path,
    adjusted_task_csv: Path,
    run_id: str = "R134",
) -> dict[str, Any]:
    missing_rows = read_csv(missing_csv)
    candidates_by_event = group_exact_candidates_by_event(read_csv(candidate_csv))
    adjusted_by_task = {
        task_key(row): row for row in read_csv(adjusted_task_csv)
    }
    feasibility_by_event = infer_missing_feasibility(
        missing_rows,
        read_feasibility(feasibility_csv),
        adjusted_by_task,
    )

    classified_missing = [
        classify_missing_row(row, candidates_by_event, feasibility_by_event)
        for row in missing_rows
    ]
    task_rows = build_task_rows(classified_missing, adjusted_by_task)
    summary = build_summary(
        run_id=run_id,
        missing_csv=missing_csv,
        candidate_csv=candidate_csv,
        feasibility_csv=feasibility_csv,
        adjusted_task_csv=adjusted_task_csv,
        missing_rows=classified_missing,
        task_rows=task_rows,
    )
    return {"missing_rows": classified_missing, "task_rows": task_rows, "summary": summary}


def classify_missing_row(
    row: dict[str, str],
    candidates_by_event: dict[str, list[dict[str, str]]],
    feasibility_by_event: dict[str, str],
) -> dict[str, Any]:
    event_id = str(row.get("event_id", ""))
    feasibility_record = feasibility_by_event.get(event_id, {})
    feasibility = str(feasibility_record.get("feasibility", ""))
    feasibility_source = str(feasibility_record.get("source", ""))
    invalid_reference = feasibility.startswith("invalid_")
    db_feasible = bool(feasibility) and not invalid_reference
    exact_candidates = candidates_by_event.get(event_id, [])
    candidate_summary = summarize_candidates(exact_candidates)

    base = {
        "source_run_id": str(row.get("source_run_id", "")),
        "domain": str(row.get("domain", "")),
        "task_id": str(row.get("task_id", "")),
        "reference_index": str(row.get("reference_index", "")),
        "event_id": event_id,
        "tool": str(row.get("tool", "")),
        "args_json": str(row.get("args_json", "")),
        "arg_values": str(row.get("arg_values", "")),
        "feasibility": feasibility,
        "feasibility_source": feasibility_source,
        "invalid_reference": invalid_reference,
        "db_feasible": db_feasible,
        "compiler_gap_class": str(row.get("gap_class", "")),
        "complete_compiler_hint_steps": str(row.get("complete_compiler_hint_steps", "")),
        "partial_compiler_hint_steps": str(row.get("partial_compiler_hint_steps", "")),
        "tool_visible_steps": str(row.get("tool_visible_steps", "")),
        "all_arg_evidence_steps": str(row.get("all_arg_evidence_steps", "")),
        "any_arg_evidence_steps": str(row.get("any_arg_evidence_steps", "")),
        "task_arg_evidence": str(row.get("task_arg_evidence", "")),
        "missing_arg_values_from_prompt_evidence": str(
            row.get("missing_arg_values_from_prompt_evidence", "")
        ),
        **candidate_summary,
    }
    base["actionability_class"] = actionability_class(base)
    base["next_experiment_target"] = next_experiment_target(base["actionability_class"])
    return base


def summarize_candidates(rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        return {
            "runtime_exact_candidate_count": 0,
            "runtime_exact_candidate_steps": "",
            "runtime_exact_next_candidate_steps": "",
            "runtime_exact_future_candidate_steps": "",
            "runtime_selected_steps": "",
            "runtime_ranked_fallback_steps": "",
            "runtime_executed_steps": "",
            "runtime_top_rank": "",
            "runtime_top_correctness": "",
            "runtime_candidate_correctness_counts": "",
        }
    rows_by_rank = sorted(rows, key=lambda row: int_or_large(row.get("rank_position", "")))
    correctness_counts = Counter(str(row.get("candidate_correctness", "")) for row in rows)
    return {
        "runtime_exact_candidate_count": len(rows),
        "runtime_exact_candidate_steps": join_unique(row.get("step", "") for row in rows),
        "runtime_exact_next_candidate_steps": join_unique(
            row.get("step", "")
            for row in rows
            if row.get("candidate_correctness") == "exact_next_reference"
        ),
        "runtime_exact_future_candidate_steps": join_unique(
            row.get("step", "")
            for row in rows
            if row.get("candidate_correctness") == "exact_future_reference"
        ),
        "runtime_selected_steps": join_unique(
            row.get("step", "")
            for row in rows
            if truthy(row.get("selected_by_model", ""))
        ),
        "runtime_ranked_fallback_steps": join_unique(
            row.get("step", "")
            for row in rows
            if truthy(row.get("selected_by_ranked_fallback", ""))
        ),
        "runtime_executed_steps": join_unique(
            row.get("step", "") for row in rows if truthy(row.get("executed", ""))
        ),
        "runtime_top_rank": str(int_or_large(rows_by_rank[0].get("rank_position", ""))),
        "runtime_top_correctness": str(rows_by_rank[0].get("candidate_correctness", "")),
        "runtime_candidate_correctness_counts": "|".join(
            f"{key}:{correctness_counts[key]}" for key in sorted(correctness_counts)
        ),
    }


def actionability_class(row: dict[str, Any]) -> str:
    if row["invalid_reference"]:
        return "invalid_reference"
    if int(row["runtime_exact_candidate_count"]) > 0:
        return "candidate_selection_or_planning_gap"
    if row["complete_compiler_hint_steps"]:
        return "complete_compiler_hint_not_called"

    tool_visible = bool(row["tool_visible_steps"])
    all_arg_evidence = bool(row["all_arg_evidence_steps"]) or row["task_arg_evidence"] == "true"
    any_arg_evidence = bool(row["any_arg_evidence_steps"]) or row["task_arg_evidence"] == "true"

    if tool_visible and all_arg_evidence:
        return "runtime_candidate_generation_gap"
    if (not tool_visible) and all_arg_evidence:
        return "tool_activation_gap"
    if tool_visible:
        return "argument_evidence_gap"
    if any_arg_evidence:
        return "tool_activation_gap"
    return "upstream_planning_gap"


def next_experiment_target(actionability: str) -> str:
    return {
        "invalid_reference": "exclude_or_repair_invalid_reference_oracle",
        "candidate_selection_or_planning_gap": "planner_select_existing_exact_candidate",
        "complete_compiler_hint_not_called": "force_or_confirm_complete_compiler_hint",
        "runtime_candidate_generation_gap": "generate_runtime_candidate_from_visible_tool_and_arguments",
        "tool_activation_gap": "activate_or_compile_missing_tool_from_visible_argument_evidence",
        "argument_evidence_gap": "gather_or_extract_missing_argument_evidence",
        "upstream_planning_gap": "improve_upstream_plan_and_evidence_discovery",
    }.get(actionability, "inspect_unclassified_gap")


def build_task_rows(
    missing_rows: list[dict[str, Any]],
    adjusted_by_task: dict[tuple[str, str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    missing_by_task: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in missing_rows:
        missing_by_task[task_key(row)].append(row)

    all_keys = sorted(set(missing_by_task) | set(adjusted_by_task))
    task_rows: list[dict[str, Any]] = []
    for key in all_keys:
        adjusted = adjusted_by_task.get(key, {})
        rows = missing_by_task.get(key, [])
        counts = Counter(str(row["actionability_class"]) for row in rows)
        reward_residual = int(
            str(adjusted.get("adjusted_category", ""))
            == "feasible_refs_complete_but_reward_failed"
        )
        row = {
            "source_run_id": key[0],
            "domain": key[1],
            "task_id": key[2],
            "adjusted_category": str(adjusted.get("adjusted_category", "")),
            "official_reference_actions": str(adjusted.get("official_reference_actions", "")),
            "invalid_reference_actions": str(adjusted.get("invalid_reference_actions", "")),
            "db_feasible_reference_actions": str(
                adjusted.get("db_feasible_reference_actions", "")
            ),
            "official_executed_reference_actions": str(
                adjusted.get("official_executed_reference_actions", "")
            ),
            "executed_db_feasible_reference_actions": str(
                adjusted.get("executed_db_feasible_reference_actions", "")
            ),
            "official_missing_reference_actions": str(
                adjusted.get("official_missing_reference_actions", "")
            ),
            "missing_db_feasible_reference_actions": str(
                adjusted.get("missing_db_feasible_reference_actions", "")
            ),
            "db_feasible_reference_complete": str(
                adjusted.get("db_feasible_reference_complete", "")
            ),
            "official_tool_oracle_pass": str(adjusted.get("official_tool_oracle_pass", "")),
            "official_action_reward": str(adjusted.get("official_action_reward", "")),
            "official_env_reward": str(adjusted.get("official_env_reward", "")),
            "adjusted_action_env_pass": str(adjusted.get("adjusted_action_env_pass", "")),
            "missing_rows": len(rows),
            "missing_db_feasible_rows": sum(1 for row in rows if row["db_feasible"]),
            "invalid_missing_rows": counts["invalid_reference"],
            "candidate_selection_or_planning_gap": counts[
                "candidate_selection_or_planning_gap"
            ],
            "complete_compiler_hint_not_called": counts[
                "complete_compiler_hint_not_called"
            ],
            "runtime_candidate_generation_gap": counts[
                "runtime_candidate_generation_gap"
            ],
            "tool_activation_gap": counts["tool_activation_gap"],
            "argument_evidence_gap": counts["argument_evidence_gap"],
            "upstream_planning_gap": counts["upstream_planning_gap"],
            "reward_residual_not_missing_action": reward_residual,
        }
        row["primary_actionability_class"] = primary_task_actionability(row, counts)
        task_rows.append(row)
    return task_rows


def primary_task_actionability(row: dict[str, Any], counts: Counter[str]) -> str:
    if row["reward_residual_not_missing_action"]:
        return "reward_residual_not_missing_action"
    for label in [
        "candidate_selection_or_planning_gap",
        "complete_compiler_hint_not_called",
        "runtime_candidate_generation_gap",
        "tool_activation_gap",
        "argument_evidence_gap",
        "upstream_planning_gap",
        "invalid_reference",
    ]:
        if counts[label]:
            return label
    return "no_missing_reference_gap"


def build_summary(
    *,
    run_id: str,
    missing_csv: Path,
    candidate_csv: Path,
    feasibility_csv: Path,
    adjusted_task_csv: Path,
    missing_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    action_counts = Counter(str(row["actionability_class"]) for row in missing_rows)
    db_feasible_rows = [row for row in missing_rows if row["db_feasible"]]
    db_counts = Counter(str(row["actionability_class"]) for row in db_feasible_rows)
    primary_counts = Counter(str(row["primary_actionability_class"]) for row in task_rows)
    exact_candidate_rows = [
        row for row in db_feasible_rows if int(row["runtime_exact_candidate_count"]) > 0
    ]
    return {
        "run_id": run_id,
        "analysis": "saved local-Qwen tau2 broader missing-reference actionability classification",
        "missing_csv": str(missing_csv),
        "candidate_csv": str(candidate_csv),
        "feasibility_csv": str(feasibility_csv),
        "adjusted_task_csv": str(adjusted_task_csv),
        "no_dataset_sync": True,
        "tasks": len(task_rows),
        "missing_reference_actions": len(missing_rows),
        "missing_db_feasible_reference_actions": len(db_feasible_rows),
        "missing_invalid_reference_actions": action_counts["invalid_reference"],
        "missing_unknown_feasibility_actions": sum(
            1 for row in missing_rows if not row["feasibility"]
        ),
        "actionability_class_counts": dict(sorted(action_counts.items())),
        "db_feasible_actionability_class_counts": dict(sorted(db_counts.items())),
        "task_primary_actionability_counts": dict(sorted(primary_counts.items())),
        "db_feasible_missing_with_existing_runtime_exact_candidate": len(
            exact_candidate_rows
        ),
        "db_feasible_missing_without_runtime_exact_candidate": len(db_feasible_rows)
        - len(exact_candidate_rows),
        "reward_residual_tasks_without_missing_action": sum(
            1 for row in task_rows if row["reward_residual_not_missing_action"]
        ),
        "db_feasible_selection_or_planning_gap_actions": db_counts[
            "candidate_selection_or_planning_gap"
        ],
        "db_feasible_candidate_generation_gap_actions": db_counts[
            "runtime_candidate_generation_gap"
        ],
        "db_feasible_tool_activation_gap_actions": db_counts["tool_activation_gap"],
        "db_feasible_argument_evidence_gap_actions": db_counts["argument_evidence_gap"],
        "db_feasible_upstream_planning_gap_actions": db_counts["upstream_planning_gap"],
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256_path(Path(__file__)),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This analysis reads saved R067/R128/R129/R131 artifacts only.",
            "Reference labels are used only post-hoc to classify the current utility failure surface.",
            "A runtime exact candidate means R131 observed a runtime-evidence candidate bound to this missing reference event at some step; it does not imply the model executed it.",
            "DB-feasible counts exclude saved feasibility rows marked invalid_schema_example_reference.",
            "The output identifies the next repair target for each missing action rather than claiming utility recovery.",
        ],
    }


def group_exact_candidates_by_event(
    rows: list[dict[str, str]]
) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        event_id = str(row.get("exact_reference_event_id", ""))
        if event_id:
            groups[event_id].append(row)
    return dict(groups)


def infer_missing_feasibility(
    missing_rows: list[dict[str, str]],
    direct_feasibility: dict[str, str],
    adjusted_by_task: dict[tuple[str, str, str], dict[str, str]],
) -> dict[str, dict[str, str]]:
    """Infer per-missing-reference feasibility from direct and task-level audits.

    R067 directly labels the schema-example invalid references, while R128
    records per-task counts of invalid and DB-feasible references.  If all
    invalid references in a task are directly identified by R067, the remaining
    missing references can be conservatively marked task-adjusted DB feasible.
    Otherwise they stay unknown.
    """

    rows_by_task: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    inferred: dict[str, dict[str, str]] = {}
    for row in missing_rows:
        rows_by_task[task_key(row)].append(row)
        event_id = str(row.get("event_id", ""))
        if event_id in direct_feasibility:
            inferred[event_id] = {
                "feasibility": direct_feasibility[event_id],
                "source": "direct_feasibility_audit",
            }

    for key, rows in rows_by_task.items():
        adjusted = adjusted_by_task.get(key, {})
        invalid_budget = int_or_zero(adjusted.get("invalid_reference_actions", ""))
        direct_invalid = sum(
            1
            for row in rows
            if direct_feasibility.get(str(row.get("event_id", "")), "").startswith(
                "invalid_"
            )
        )
        can_infer_remaining_db_feasible = invalid_budget == direct_invalid
        for row in rows:
            event_id = str(row.get("event_id", ""))
            if event_id in inferred:
                continue
            if can_infer_remaining_db_feasible:
                inferred[event_id] = {
                    "feasibility": "task_adjusted_db_feasible_reference",
                    "source": "task_adjusted_invalid_budget",
                }
            else:
                inferred[event_id] = {
                    "feasibility": "",
                    "source": "unknown_feasibility",
                }
    return inferred


def read_feasibility(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {
        str(row.get("event_id", "")): str(row.get("feasibility", ""))
        for row in read_csv(path)
        if row.get("event_id")
    }


def task_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("source_run_id", "")),
        str(row.get("domain", "")),
        str(row.get("task_id", "")),
    )


def join_unique(values: Any) -> str:
    seen: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.append(text)
    return "|".join(seen)


def int_or_large(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 10**9


def int_or_zero(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def truthy(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "y"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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
