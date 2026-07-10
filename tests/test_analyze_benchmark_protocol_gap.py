import csv
import json

import scripts.analyze_benchmark_protocol_gap as analyzer


def test_protocol_gap_audit_characterizes_saved_r340_outputs(tmp_path):
    output_dir = tmp_path / "R344PROTOCOLGAP"
    summary = analyzer.analyze(
        input_dir=analyzer.DEFAULT_INPUT_DIR,
        output_dir=output_dir,
        run_id="T344PROTOCOLGAP",
    )

    assert summary["run_id"] == "T344PROTOCOLGAP"
    assert summary["source_run_id"] == "R340RETAILCOMPILERFEEDBACK5"
    assert summary["tasks_evaluated"] == 5
    assert summary["source_model_calls"] == 13
    assert summary["source_gateway_allowed"] == 11
    assert summary["source_gateway_blocked"] == 2
    assert summary["source_feedback_attempted_tasks"] == 2
    assert summary["source_feedback_gateway_allowed"] == 1
    assert summary["source_action_reward_pass_tasks"] == 0
    assert summary["source_tool_oracle_pass_tasks"] == 0
    assert summary["step_raw_outputs"] == 23
    assert summary["feedback_raw_outputs"] == 2
    assert summary["step_outputs_with_think"] == 21
    assert summary["step_outputs_empty"] == 2
    assert summary["step_outputs_likely_truncated"] == 14
    assert summary["step_outputs_with_parsed_calls"] == 10
    assert summary["tasks_with_likely_truncated_step_outputs"] == 5
    assert summary["protocol_gap_status"] == "open"
    assert summary["no_dataset_sync"] is True
    assert summary["not_a_model_run"] is True
    assert summary["not_a_new_benchmark"] is True

    persisted = json.loads((output_dir / "benchmark_protocol_gap_summary.json").read_text())
    assert persisted["step_outputs_with_think"] == 21
    raw_rows = list(csv.DictReader((output_dir / "protocol_raw_outputs.csv").open()))
    assert len(raw_rows) == 25
    assert any(row["empty_stdout"] == "True" for row in raw_rows)
    task_rows = list(csv.DictReader((output_dir / "protocol_task_summary.csv").open()))
    assert len(task_rows) == 5
    assert all(int(row["likely_truncated_step_outputs"]) > 0 for row in task_rows)
