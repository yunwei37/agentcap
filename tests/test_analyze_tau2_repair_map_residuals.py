import csv
from pathlib import Path

import scripts.analyze_tau2_repair_map_residuals as analyzer


def test_classify_repair_map_execution_separates_marker_other_and_missing():
    repair_rows = [
        {
            "domain": "retail",
            "task_id": "0",
            "event_id": "retail:0:0_2",
            "tool": "get_product_details",
            "args_json": '{"product_id": "1656367028"}',
            "repair_class": "visible_tool_argument_candidate_generation",
            "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
            "earliest_synthesis_step": "4",
        },
        {
            "domain": "retail",
            "task_id": "1",
            "event_id": "retail:1:1_2",
            "tool": "get_product_details",
            "args_json": '{"product_id": "1656367028"}',
            "repair_class": "visible_tool_argument_candidate_generation",
            "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
            "earliest_synthesis_step": "4",
        },
        {
            "domain": "retail",
            "task_id": "3",
            "event_id": "retail:3:3_10",
            "tool": "get_product_details",
            "args_json": '{"product_id": "7314138884"}',
            "repair_class": "visible_tool_argument_candidate_generation",
            "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
            "earliest_synthesis_step": "10",
        },
    ]
    action_rows = [
        {
            "round": "step_4",
            "index": "3",
            "bound_reference_event_id": "retail:0:0_2",
            "executed": "True",
            "runtime_binding_allowed": "True",
            "intentcap_markers_json": (
                '{"_intentcap_synthesized_from_repair_map": true, '
                '"_intentcap_repair_map_event_id": "retail:0:0_2"}'
            ),
        },
        {
            "round": "step_3",
            "index": "2",
            "bound_reference_event_id": "retail:1:1_2",
            "executed": "True",
            "runtime_binding_allowed": "False",
            "intentcap_markers_json": "{}",
        },
    ]
    previous = [
        {
            "event_id": "retail:3:3_10",
            "actionability_class": "runtime_candidate_generation_gap",
        }
    ]
    current = [
        {
            "event_id": "retail:3:3_10",
            "actionability_class": "runtime_candidate_generation_gap",
            "next_experiment_target": "generate_runtime_candidate_from_visible_tool_and_arguments",
            "db_feasible": True,
            "feasibility": "task_adjusted_db_feasible_reference",
        }
    ]

    rows = analyzer.classify_repair_map_execution(
        repair_rows=repair_rows,
        action_rows=action_rows,
        previous_actionability_rows=previous,
        current_actionability_rows=current,
    )

    by_event = {row["event_id"]: row for row in rows}
    assert by_event["retail:0:0_2"]["execution_status"] == "repair_map_fallback_executed"
    assert by_event["retail:0:0_2"]["executed_by_repair_map_fallback"] is True
    assert by_event["retail:1:1_2"]["execution_status"] == "executed_by_other_path"
    assert by_event["retail:3:3_10"]["execution_status"] == "not_executed"
    assert by_event["retail:3:3_10"]["still_missing_after_source_run"] is True
    assert by_event["retail:3:3_10"]["current_next_experiment_target"] == (
        "generate_runtime_candidate_from_visible_tool_and_arguments"
    )


def test_build_summary_reports_repair_map_reduction(tmp_path: Path):
    previous_csv = tmp_path / "previous.csv"
    with previous_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "db_feasible"])
        writer.writeheader()
        writer.writerow({"event_id": "a", "db_feasible": "True"})
        writer.writerow({"event_id": "b", "db_feasible": "True"})
        writer.writerow({"event_id": "c", "db_feasible": "False"})

    summary = analyzer.build_summary(
        run_id="RTEST",
        source_run_dir=Path("results/eval/RTEST"),
        repair_map_csv=Path("repair.csv"),
        previous_actionability_csv=previous_csv,
        candidate_csv=Path("candidates.csv"),
        feasibility_csv=Path("feasibility.csv"),
        mismatch_summary={
            "exact_executed_calls": 3,
            "off_lease_calls": 1,
            "category_counts": {"off_lease_same_tool_wrong_args": 1},
        },
        residual_summary={
            "missing_reference_actions": 1,
            "executed_reference_actions": 3,
        },
        adjusted_summary={
            "official_tool_oracle_pass_tasks": 0,
            "adjusted_action_env_pass_tasks": 0,
            "db_feasible_reference_complete_tasks": 1,
        },
        recall_summary={"missing_gap_class_counts": {"tool_visible_no_arg_evidence": 1}},
        actionability_summary={
            "missing_db_feasible_reference_actions": 1,
            "reward_residual_tasks_without_missing_action": 1,
            "db_feasible_actionability_class_counts": {"argument_evidence_gap": 1},
            "task_primary_actionability_counts": {"argument_evidence_gap": 1},
        },
        repair_rows=[
            {
                "execution_status": "repair_map_fallback_executed",
                "executed_by_any_path": True,
                "still_missing_after_source_run": False,
            }
        ],
    )

    assert summary["previous_db_feasible_missing_reference_actions"] == 2
    assert summary["current_db_feasible_missing_reference_actions"] == 1
    assert summary["db_feasible_missing_reduction_vs_previous"] == 1
    assert summary["repair_map_fallback_executed_candidates"] == 1
    assert summary["source_same_tool_wrong_args_calls"] == 1
