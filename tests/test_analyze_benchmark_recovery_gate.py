import json
import csv

import pytest

import scripts.analyze_benchmark_recovery_gate as analyzer


def test_benchmark_recovery_gate_separates_benchmark_from_handwritten(tmp_path):
    result = analyzer.analyze(
        output_dir=tmp_path / "R309BENCHRECOVERYGATE",
        inputs=analyzer.DEFAULT_INPUTS,
        run_id="T309BENCHRECOVERYGATE",
    )

    summary = result["summary"]
    assert summary["run_id"] == "T309BENCHRECOVERYGATE"
    assert summary["benchmark_matched_tasks"] == 18
    assert summary["benchmark_runs"] == 2
    assert summary["benchmark_leased_gateway_blocks"] == 2
    assert summary["benchmark_all_tools_gateway_blocks"] == 18
    assert summary["benchmark_leased_tasks_with_blocks"] == 2
    assert summary["benchmark_all_tools_tasks_with_blocks"] == 9
    assert summary["benchmark_denial_task_rows"] == 11
    assert summary["benchmark_matched_feedback_attempted_tasks"] == 0
    assert summary["benchmark_feedback_attempted_tasks"] == 2
    assert summary["benchmark_compiler_feedback_tasks"] == 2
    assert summary["benchmark_compiler_feedback_gateway_blocks"] == 1
    assert summary["benchmark_compiler_feedback_tasks_with_blocks"] == 1
    assert summary["benchmark_compiler_feedback_attempted_tasks"] == 1
    assert summary["benchmark_compiler_feedback_model_calls"] == 1
    assert summary["benchmark_compiler_feedback_allowed_calls"] == 1
    assert summary["benchmark_compiler_feedback_bound_reference_calls"] == 5
    assert summary["benchmark_compiler_feedback_action_reward_tasks"] == 0
    assert summary["benchmark_compiler_feedback_tool_oracle_tasks"] == 0
    assert summary["benchmark_expanded_feedback_tasks"] == 5
    assert summary["benchmark_expanded_feedback_gateway_blocks"] == 2
    assert summary["benchmark_expanded_feedback_tasks_with_blocks"] == 2
    assert summary["benchmark_expanded_feedback_attempted_tasks"] == 2
    assert summary["benchmark_expanded_feedback_model_calls"] == 1
    assert summary["benchmark_expanded_feedback_allowed_calls"] == 1
    assert summary["benchmark_expanded_feedback_bound_reference_calls"] == 11
    assert summary["benchmark_expanded_feedback_action_reward_tasks"] == 0
    assert summary["benchmark_expanded_feedback_tool_oracle_tasks"] == 0
    assert summary["benchmark_recovered_tasks"] == 0
    assert summary["benchmark_leased_action_reward_tasks"] == 8
    assert summary["benchmark_all_tools_action_reward_tasks"] == 8
    assert summary["benchmark_action_reward_improvement_all_minus_leased"] == 0
    assert summary["benchmark_leased_tool_oracle_tasks"] == 0
    assert summary["benchmark_all_tools_tool_oracle_tasks"] == 0
    assert summary["handwritten_recovery_tasks"] == 14
    assert summary["handwritten_recovered_tasks"] == 14
    assert summary["handwritten_dangerous_executions"] == 0
    assert summary["handwritten_multiboundary_surfaces"] == 6
    assert summary["handwritten_multiboundary_owner_classes"] == [
        "agent",
        "env",
        "instruction",
        "tool",
    ]
    assert summary["gate_status"] == "open"
    assert "larger benchmark-derived denied-benign recovery run" in summary["missing_for_full_claim"]
    assert summary["no_dataset_sync"] is True
    assert summary["not_a_model_run"] is True
    assert summary["not_a_new_benchmark"] is True

    gate_rows = {row["evidence_class"]: row for row in result["gate_rows"]}
    assert gate_rows["benchmark_matched_leased"]["benchmark_derived"] is True
    assert gate_rows["benchmark_matched_leased"]["recovered_tasks"] == 0
    assert gate_rows["benchmark_compiler_feedback_shard"]["benchmark_derived"] is True
    assert gate_rows["benchmark_compiler_feedback_shard"]["free_form_replanning"] is True
    assert gate_rows["benchmark_compiler_feedback_shard"]["recovered_tasks"] == 1
    assert gate_rows["benchmark_compiler_feedback_shard"]["action_reward_tasks"] == 0
    assert gate_rows["benchmark_compiler_feedback_expanded"]["benchmark_derived"] is True
    assert gate_rows["benchmark_compiler_feedback_expanded"]["free_form_replanning"] is True
    assert gate_rows["benchmark_compiler_feedback_expanded"]["tasks"] == 5
    assert gate_rows["benchmark_compiler_feedback_expanded"]["recovered_tasks"] == 1
    assert gate_rows["benchmark_compiler_feedback_expanded"]["action_reward_tasks"] == 0
    assert gate_rows["handwritten_multiboundary_recovery"]["benchmark_derived"] is False
    assert gate_rows["handwritten_multiboundary_recovery"]["recovered_tasks"] == 8

    denial_rows = result["denial_rows"]
    assert len(denial_rows) == 11
    assert {row["source_run"] for row in denial_rows} == {"R214E1LEASED", "R215E1ALL"}
    assert all(row["feedback_attempted"] == "False" for row in denial_rows)

    output_dir = tmp_path / "R309BENCHRECOVERYGATE"
    assert (output_dir / "benchmark_recovery_gate_summary.json").exists()
    assert (output_dir / "benchmark_denial_tasks.csv").exists()
    persisted = json.loads((output_dir / "benchmark_recovery_gate_summary.json").read_text())
    assert persisted["gate_status"] == "open"


def test_benchmark_recovery_gate_validates_matched_summary(tmp_path):
    bad_tasks = tmp_path / "bad_tasks.csv"
    with analyzer.DEFAULT_INPUTS["leased_tasks"].open(newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = list(rows[0].keys())
    rows[0]["gateway_blocked"] = str(int(rows[0]["gateway_blocked"]) + 1)
    with bad_tasks.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    inputs = dict(analyzer.DEFAULT_INPUTS)
    inputs["leased_tasks"] = bad_tasks

    with pytest.raises(ValueError, match="matched summary/CSV mismatch"):
        analyzer.analyze(
            output_dir=tmp_path / "BAD",
            inputs=inputs,
            run_id="T309BENCHRECOVERYGATE",
        )
