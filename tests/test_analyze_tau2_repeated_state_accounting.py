import csv

import scripts.analyze_tau2_repeated_state_accounting as analyzer


def test_same_args_get_call_is_creditable_read_accounting():
    row = analyzer.build_adjustment_row(
        source_run_id="RTEST",
        row={
            "domain": "retail",
            "task_id": "3",
            "event_id": "retail:3:3_3",
            "tool": "get_product_details",
            "args_json": '{"product_id":"9523456873"}',
            "proof_status": "missing_existing_exact_next_candidate",
            "diagnosis": "same_tool_args_already_executed_for_different_reference",
            "executed_same_call_event_ids": "retail:3:3_10",
            "executed_same_call_bound_reference_ids": "retail:3:3_10",
        },
    )

    assert row["read_only_idempotent_tool"] is True
    assert row["accounting_class"] == "idempotent_read_already_observed"
    assert row["db_feasible_missing_delta"] == -1
    assert row["adjusted_status"] == "credit_as_observed_for_adjusted_missing_accounting"


def test_existing_exact_candidate_without_execution_stays_missing():
    row = analyzer.build_adjustment_row(
        source_run_id="RTEST",
        row={
            "domain": "retail",
            "task_id": "3",
            "event_id": "retail:3:3_6",
            "tool": "get_order_details",
            "args_json": '{"order_id":"#W9711842"}',
            "proof_status": "missing_existing_exact_next_candidate",
            "diagnosis": "existing_exact_candidate_not_selected",
            "executed_same_call_event_ids": "",
            "executed_same_call_bound_reference_ids": "",
        },
    )

    assert row["read_only_idempotent_tool"] is True
    assert row["accounting_class"] == "planner_exact_candidate_not_selected"
    assert row["db_feasible_missing_delta"] == 0
    assert row["adjusted_status"] == "still_missing"


def test_non_read_same_args_call_gets_no_credit():
    row = analyzer.build_adjustment_row(
        source_run_id="RTEST",
        row={
            "domain": "retail",
            "task_id": "3",
            "event_id": "retail:3:write",
            "tool": "modify_pending_order_items",
            "args_json": '{"order_id":"#O"}',
            "proof_status": "missing_existing_exact_next_candidate",
            "diagnosis": "same_tool_args_already_executed_for_different_reference",
            "executed_same_call_event_ids": "retail:3:write_other",
            "executed_same_call_bound_reference_ids": "retail:3:write_other",
        },
    )

    assert row["read_only_idempotent_tool"] is False
    assert row["accounting_class"] == "same_call_requires_state_semantics"
    assert row["db_feasible_missing_delta"] == 0
    assert row["adjusted_status"] == "no_credit"


def test_analyze_writes_summary_and_adjustments(tmp_path):
    repeated_csv = tmp_path / "repeated.csv"
    with repeated_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_run_id",
                "domain",
                "task_id",
                "event_id",
                "tool",
                "args_json",
                "actionability_class",
                "proof_status",
                "executed_same_call_event_ids",
                "executed_same_call_rounds",
                "executed_same_call_bound_reference_ids",
                "diagnosis",
                "next_mechanism_target",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "source_run_id": "RTEST",
                "domain": "retail",
                "task_id": "3",
                "event_id": "retail:3:3_3",
                "tool": "get_product_details",
                "args_json": '{"product_id":"p"}',
                "actionability_class": "candidate_selection_or_planning_gap",
                "proof_status": "missing_existing_exact_next_candidate",
                "executed_same_call_event_ids": "retail:3:3_10",
                "executed_same_call_rounds": "step_5",
                "executed_same_call_bound_reference_ids": "retail:3:3_10",
                "diagnosis": "same_tool_args_already_executed_for_different_reference",
                "next_mechanism_target": "repeated_event_selection_or_reference_accounting",
            }
        )
        writer.writerow(
            {
                "source_run_id": "RTEST",
                "domain": "retail",
                "task_id": "3",
                "event_id": "retail:3:3_6",
                "tool": "get_order_details",
                "args_json": '{"order_id":"#O"}',
                "actionability_class": "candidate_selection_or_planning_gap",
                "proof_status": "missing_existing_exact_next_candidate",
                "executed_same_call_event_ids": "",
                "executed_same_call_rounds": "",
                "executed_same_call_bound_reference_ids": "",
                "diagnosis": "existing_exact_candidate_not_selected",
                "next_mechanism_target": "planner_confirm_existing_exact_candidate",
            }
        )

    actionability_csv = tmp_path / "missing.csv"
    with actionability_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "db_feasible"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            [
                {"event_id": "a", "db_feasible": "True"},
                {"event_id": "b", "db_feasible": "True"},
                {"event_id": "invalid", "db_feasible": "False"},
            ]
        )

    result = analyzer.analyze_repeated_state_accounting(
        run_id="RTEST",
        source_run_id="RTESTSRC",
        repeated_residual_csv=repeated_csv,
        missing_actionability_csv=actionability_csv,
        output_dir=tmp_path / "out",
    )

    summary = result["summary"]
    assert summary["input_repeated_state_residuals"] == 2
    assert summary["current_db_feasible_missing_before_accounting"] == 2
    assert summary["idempotent_same_call_creditable"] == 1
    assert summary["planner_selection_residuals"] == 1
    assert summary["adjusted_db_feasible_missing_after_idempotent_read_credit"] == 1
    assert (tmp_path / "out" / "repeated_state_adjustments.csv").exists()
    assert (tmp_path / "out" / "repeated_state_accounting_summary.json").exists()
