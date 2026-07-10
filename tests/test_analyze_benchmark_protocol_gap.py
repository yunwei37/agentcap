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


def test_protocol_gap_audit_reports_controlled_schema_shard(tmp_path):
    input_dir = tmp_path / "source"
    output_dir = tmp_path / "out"
    (input_dir / "step_raw_outputs").mkdir(parents=True)
    (input_dir / "feedback_raw_outputs").mkdir()
    (input_dir / "task_gateway_summary.json").write_text(
        json.dumps(
            {
                "run_id": "SCHEMA_SOURCE",
                "tasks_evaluated": 1,
                "model_calls": 2,
                "gateway_allowed": 2,
                "gateway_blocked": 0,
                "feedback_attempted_tasks": 0,
                "feedback_model_calls": 0,
                "feedback_gateway_allowed": 0,
                "bound_reference_calls": 2,
                "action_reward_pass_tasks": 0,
                "tool_oracle_pass_tasks": 0,
                "llama_json_schema_actions": True,
                "llama_reasoning_off": True,
            }
        )
    )
    (input_dir / "task_results.csv").write_text(
        "\n".join(
            [
                "domain,task_id,gateway_allowed,gateway_blocked,feedback_attempted,feedback_model_calls,action_reward,tool_oracle_pass",
                "retail,0,2,0,False,0,0.0,False",
            ]
        )
        + "\n"
    )
    (input_dir / "action_results.csv").write_text(
        "\n".join(
            [
                "domain,task_id,round,gateway_allowed",
                "retail,0,step_1,True",
                "retail,0,step_2,True",
            ]
        )
        + "\n"
    )
    for index, tool in enumerate(["find_user_id_by_name_zip", "get_order_details"], start=1):
        (input_dir / "step_raw_outputs" / f"retail_0_step_{index}.txt").write_text(
            json.dumps(
                {
                    "returncode": 0,
                    "stdout": (
                        '{"actions":[{"tool":"'
                        + tool
                        + '","arguments":{"id":"v"}}]} [end of text]\n'
                    ),
                    "stderr": "",
                }
            )
        )

    summary = analyzer.analyze(
        input_dir=input_dir,
        output_dir=output_dir,
        run_id="SCHEMA_GAP",
    )

    assert summary["protocol_gap_status"] == "controlled_on_source_shard"
    assert summary["step_protocol_clean"] is True
    assert summary["source_llama_json_schema_actions"] is True
    assert summary["source_llama_reasoning_off"] is True
    assert summary["step_outputs_with_think"] == 0
    assert summary["step_outputs_likely_truncated"] == 0
    assert summary["step_outputs_with_parsed_calls"] == 2
    assert "reliable no-thinking JSON output protocol" not in " ".join(
        summary["missing_for_stronger_utility_claim"]
    )
