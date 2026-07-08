import csv
import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).parents[1] / "scripts" / "build_e1_matched_online_comparison.py"
    spec = importlib.util.spec_from_file_location("build_e1_matched_online_comparison", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_run(root: Path, run_id: str, exposure: str, schema_count: int, blocks: int):
    root.mkdir()
    summary = {
        "run_id": run_id,
        "tool_exposure": exposure,
        "tasks_evaluated": 1,
        "reference_actions": 2,
        "tool_schema_count_avg": schema_count,
        "tool_schema_count_min": schema_count,
        "tool_schema_count_max": schema_count,
        "active_leases_total": 2,
        "model_calls": 2,
        "gateway_allowed": 2 - blocks,
        "gateway_blocked": blocks,
        "off_lease_calls_blocked": blocks,
        "compiler_runtime_binding_missing_value_proof": 0,
        "executed_calls": 2 - blocks,
        "tool_error_calls": 0,
        "bound_reference_calls": 2 - blocks,
        "exact_sequence_match_tasks": 1 - blocks,
        "all_reference_actions_executed_tasks": 1 - blocks,
        "action_reward_pass_tasks": 1,
        "env_reward_pass_tasks": 0,
        "tool_oracle_pass_tasks": 0,
    }
    (root / "task_gateway_summary.json").write_text(json.dumps(summary))
    (root / "command.txt").write_text(f"run {run_id}\n")

    task_fields = [
        "domain",
        "task_id",
        "tool_schema_count",
        "active_leases",
        "model_calls",
        "gateway_blocked",
        "off_lease_calls_blocked",
        "compiler_runtime_binding_missing_value_proof",
        "executed_calls",
        "tool_error_calls",
        "bound_reference_calls",
        "exact_sequence_match",
        "all_reference_actions_executed",
        "action_reward",
        "tool_oracle_pass",
    ]
    with (root / "task_results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=task_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "domain": "retail",
                "task_id": "1",
                "tool_schema_count": schema_count,
                "active_leases": 2,
                "model_calls": 2,
                "gateway_blocked": blocks,
                "off_lease_calls_blocked": blocks,
                "compiler_runtime_binding_missing_value_proof": 0,
                "executed_calls": 2 - blocks,
                "tool_error_calls": 0,
                "bound_reference_calls": 2 - blocks,
                "exact_sequence_match": str(blocks == 0),
                "all_reference_actions_executed": str(blocks == 0),
                "action_reward": 1.0,
                "tool_oracle_pass": False,
            }
        )

    action_fields = [
        "domain",
        "task_id",
        "round",
        "index",
        "model_tool",
        "object",
        "gateway_allowed",
        "gateway_action",
        "gateway_reason",
        "runtime_binding_attempted",
        "runtime_binding_allowed",
        "runtime_binding_reason",
        "tool_activation_binding_attempted",
        "tool_activation_binding_allowed",
        "tool_activation_binding_reason",
        "model_args_json",
    ]
    with (root / "action_results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=action_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "domain": "retail",
                "task_id": "1",
                "round": "step_1",
                "index": 0,
                "model_tool": "get_order_details",
                "object": "tau2.retail.get_order_details",
                "gateway_allowed": "True",
                "gateway_action": "execute",
                "gateway_reason": "allowed",
                "model_args_json": "{}",
            }
        )
        if blocks:
            writer.writerow(
                {
                    "domain": "retail",
                    "task_id": "1",
                    "round": "step_2",
                    "index": 1,
                    "model_tool": "modify_order",
                    "object": "tau2.retail.modify_order",
                    "gateway_allowed": "False",
                    "gateway_action": "block",
                    "gateway_reason": "no matching lease",
                    "runtime_binding_attempted": "True",
                    "runtime_binding_allowed": "False",
                    "runtime_binding_reason": "missing value proof",
                    "model_args_json": '{"order_id":"x"}',
                }
            )


def test_builds_matched_online_comparison(tmp_path):
    module = _load_module()
    leased = tmp_path / "leased"
    all_tools = tmp_path / "all"
    _write_run(leased, "L", "leased", 3, 0)
    _write_run(all_tools, "A", "all", 9, 1)

    result = module.build_comparison(
        leased_dir=leased,
        all_tools_dir=all_tools,
        output_dir=tmp_path / "out",
        run_id="test",
    )

    summary = result["summary"]
    assert summary["matched_tasks"] == 1
    assert summary["delta_all_minus_leased"]["tool_schema_count_avg"] == 6
    assert summary["delta_all_minus_leased"]["gateway_blocked"] == 1
    assert len(result["blocked_rows"]) == 1
    assert result["task_rows"][0]["tool_schema_delta"] == 6
    assert (tmp_path / "out" / "run_comparison.csv").exists()
