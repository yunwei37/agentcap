import csv
import json

import scripts.analyze_tau2_post_activation_delta as analyzer


def test_compare_runs_reports_gained_write_activation_and_lost_runtime_read():
    baseline = {
        "run_id": "RBASE",
        "executed_by_event": {
            "retail:3:3_6": {
                "domain": "retail",
                "task_id": "3",
                "round": "step_12",
                "index": "11",
                "model_tool": "get_order_details",
                "model_args_json": '{"order_id":"#W9711842"}',
                "bound_reference_event_id": "retail:3:3_6",
                "runtime_binding_attempted": "True",
                "runtime_binding_reason": "runtime evidence bound",
            }
        },
    }
    current = {
        "run_id": "RCUR",
        "executed_by_event": {
            "retail:2:2_11": {
                "domain": "retail",
                "task_id": "2",
                "round": "step_10",
                "index": "9",
                "model_tool": "return_delivered_order_items",
                "model_args_json": '{"order_id":"#W2378156"}',
                "bound_reference_event_id": "retail:2:2_11",
                "tool_activation_binding_attempted": "True",
                "tool_activation_binding_reason": "visible write-tool activation value-proof bound",
            }
        },
    }

    rows = analyzer.compare_runs(baseline=baseline, current=current)

    by_event = {row["event_id"]: row for row in rows}
    assert by_event["retail:2:2_11"]["delta_class"] == "gained_reference_execution"
    assert by_event["retail:2:2_11"]["current_binding_source"] == "tool_activation"
    assert by_event["retail:3:3_6"]["delta_class"] == "lost_reference_execution"
    assert by_event["retail:3:3_6"]["baseline_binding_source"] == "runtime_binding"


def test_build_summary_interprets_safe_activation_with_planning_drift(tmp_path):
    current = {
        "run_id": "RCUR",
        "run_dir": "current",
        "summary": {"bound_reference_calls": 51},
    }
    delta_rows = [
        {
            "baseline_run": "RBASE",
            "current_run": "RCUR",
            "domain": "retail",
            "task_id": "2",
            "event_id": "retail:2:2_11",
            "delta_class": "gained_reference_execution",
            "tool": "return_delivered_order_items",
            "current_binding_source": "tool_activation",
        },
        {
            "baseline_run": "RBASE",
            "current_run": "RCUR",
            "domain": "retail",
            "task_id": "3",
            "event_id": "retail:3:3_6",
            "delta_class": "lost_reference_execution",
            "tool": "get_order_details",
            "current_binding_source": "",
        },
    ]
    task_rows = [
        {
            "domain": "retail",
            "task_id": "2",
            "net_delta": 1,
        },
        {
            "domain": "retail",
            "task_id": "3",
            "net_delta": -1,
        },
    ]

    summary = analyzer.build_summary(
        run_id="RTEST",
        current=current,
        baseline_summaries={"RBASE": {"bound_reference_calls": 52}},
        delta_rows=delta_rows,
        task_rows=task_rows,
        residual_summary={
            "current_db_feasible_missing_reference_actions": 7,
            "current_db_feasible_actionability_class_counts": {
                "candidate_selection_or_planning_gap": 3,
            },
        },
        repeated_summary={"adjusted_db_feasible_missing_after_idempotent_read_credit": 2},
        activation_summary={"input_tool_activation_gaps": 0},
        output_dir=tmp_path,
    )

    assert summary["unique_gained_write_activation_event_ids"] == ["retail:2:2_11"]
    assert summary["tasks_with_negative_delta"] == 1
    assert "planning/candidate-generation dominated" in summary["interpretation"]


def test_analyze_writes_delta_outputs(tmp_path):
    baseline_dir = tmp_path / "baseline"
    current_dir = tmp_path / "current"
    baseline_dir.mkdir()
    current_dir.mkdir()
    write_summary(baseline_dir, "RBASE", 1)
    write_summary(current_dir, "RCUR", 1)
    write_actions(
        baseline_dir,
        [
            {
                "domain": "retail",
                "task_id": "3",
                "round": "step_1",
                "index": "0",
                "model_tool": "get_order_details",
                "model_args_json": '{"order_id":"#O"}',
                "bound_reference_event_id": "retail:3:3_6",
                "runtime_binding_attempted": "True",
                "runtime_binding_reason": "runtime evidence bound",
                "executed": "True",
                "tool_error": "False",
            }
        ],
    )
    write_actions(
        current_dir,
        [
            {
                "domain": "retail",
                "task_id": "2",
                "round": "step_1",
                "index": "0",
                "model_tool": "return_delivered_order_items",
                "model_args_json": '{"order_id":"#R"}',
                "bound_reference_event_id": "retail:2:2_11",
                "tool_activation_binding_attempted": "True",
                "tool_activation_binding_reason": "visible write-tool activation value-proof bound",
                "executed": "True",
                "tool_error": "False",
            }
        ],
    )
    out_dir = tmp_path / "out"

    result = analyzer.analyze_post_activation_delta(
        run_id="RTEST",
        current_run_dir=current_dir,
        baseline_run_dirs=[baseline_dir],
        residual_summary_json=None,
        repeated_summary_json=None,
        activation_summary_json=None,
        output_dir=out_dir,
    )

    assert result["summary"]["delta_class_counts"] == {
        "gained_reference_execution": 1,
        "lost_reference_execution": 1,
    }
    assert (out_dir / "post_activation_reference_delta.csv").exists()
    assert (out_dir / "post_activation_delta_summary.json").exists()


def write_summary(path, run_id, bound_reference_calls):
    (path / "task_gateway_summary.json").write_text(
        json.dumps({"run_id": run_id, "bound_reference_calls": bound_reference_calls}),
        encoding="utf-8",
    )


def write_actions(path, rows):
    fieldnames = [
        "domain",
        "task_id",
        "round",
        "index",
        "model_tool",
        "model_args_json",
        "intentcap_markers_json",
        "bound_reference_event_id",
        "runtime_binding_attempted",
        "runtime_binding_reason",
        "tool_activation_binding_attempted",
        "tool_activation_binding_reason",
        "executed",
        "tool_error",
    ]
    with (path / "action_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
