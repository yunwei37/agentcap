import importlib.util
import json
import sys
from pathlib import Path


def _load_runner():
    repo_root = Path(__file__).parents[1]
    for path_entry in (repo_root / "src", repo_root / "scripts"):
        if str(path_entry) not in sys.path:
            sys.path.insert(0, str(path_entry))
    path = repo_root / "scripts" / "replay_tau2_compiler_leases_gateway.py"
    spec = importlib.util.spec_from_file_location("replay_tau2_compiler_leases_gateway", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compiler_lease_gateway_replay_classifies_exact_broad_and_missing(tmp_path):
    runner = _load_runner()
    benchmark_dir = tmp_path / "tau2-bench"
    domain_dir = benchmark_dir / "data" / "tau2" / "domains" / "mock"
    src_dir = benchmark_dir / "src" / "tau2" / "domains" / "mock"
    source_dir = tmp_path / "R074"
    domain_dir.mkdir(parents=True)
    src_dir.mkdir(parents=True)
    source_dir.mkdir()

    (domain_dir / "tasks.json").write_text(
        json.dumps(
            [
                {
                    "id": "task_0",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": (
                                "Please update order #W7654321 for user "
                                "bob_lee_4321."
                            )
                        }
                    },
                    "evaluation_criteria": {
                        "reward_basis": ["ACTION"],
                        "actions": [
                            {
                                "action_id": "a0",
                                "requestor": "assistant",
                                "name": "get_user_details",
                                "arguments": {"user_id": "bob_lee_4321"},
                            },
                            {
                                "action_id": "a1",
                                "requestor": "assistant",
                                "name": "update_order_item",
                                "arguments": {
                                    "order_id": "#W7654321",
                                    "product_id": "8888888888",
                                },
                            },
                            {
                                "action_id": "a2",
                                "requestor": "assistant",
                                "name": "cancel_order",
                                "arguments": {"order_id": "#W7654321"},
                            },
                            {
                                "action_id": "a3",
                                "requestor": "assistant",
                                "name": "update_order_item",
                                "arguments": {
                                    "order_id": "#W0000000",
                                    "product_id": "9999999999",
                                },
                            },
                        ],
                    },
                }
            ]
        )
    )
    (src_dir / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool


class MockTools:
    @is_tool(ToolType.READ)
    def get_user_details(self, user_id):
        pass

    @is_tool(ToolType.WRITE)
    def update_order_item(self, order_id, product_id):
        pass

    @is_tool(ToolType.WRITE)
    def cancel_order(self, order_id):
        pass
"""
    )
    (source_dir / "llm_visible_lease_compiler_summary.json").write_text(
        json.dumps({"run_id": "R074"})
    )
    (source_dir / "samples.jsonl").write_text(
        json.dumps(
            {
                "run_id": "R074",
                "domain": "mock",
                "task_id": "task_0",
                "visible_arg_repairs": 1,
                "task_row": {"parse_ok": True},
                "parsed_model_json": {
                    "leases": [
                        {
                            "tool": "get_user_details",
                            "intent_evidence": "visible user id",
                            "argument_policy": {
                                "user_id": {
                                    "mode": "equals_any",
                                    "values": ["bob_lee_4321"],
                                }
                            },
                        }
                    ]
                },
                "repaired_model_json": {
                    "leases": [
                        {
                            "tool": "get_user_details",
                            "intent_evidence": "visible user id",
                            "argument_policy": {
                                "user_id": {
                                    "mode": "equals_any",
                                    "values": ["bob_lee_4321"],
                                }
                            },
                        },
                        {
                            "tool": "update_order_item",
                            "intent_evidence": "incorrect exact update candidate",
                            "argument_policy": {
                                "order_id": {
                                    "mode": "equals_any",
                                    "values": ["#W0000001"],
                                },
                                "product_id": {
                                    "mode": "equals_any",
                                    "values": ["8888888888"],
                                },
                            },
                        },
                        {
                            "tool": "update_order_item",
                            "intent_evidence": "visible order update",
                            "argument_policy": {
                                "order_id": {
                                    "mode": "equals_any",
                                    "values": ["#W7654321"],
                                },
                                "product_id": {
                                    "mode": "runtime_from_prior_tool",
                                    "values": [],
                                },
                            },
                        },
                    ]
                },
            },
            sort_keys=True,
        )
        + "\n"
    )

    result = runner.replay(
        benchmark_dir=benchmark_dir,
        source_run_dir=source_dir,
        output_dir=tmp_path / "out",
        run_id="TEST",
        domains=("mock",),
        max_tasks_per_domain=None,
    )

    summary = result["summary"]
    assert summary["assistant_reference_actions"] == 4
    assert summary["gateway_allowed_reference_actions"] == 2
    assert summary["allowed_all_reference_args_constrained"] == 1
    assert summary["allowed_broad_or_runtime_args"] == 1
    assert summary["blocked_broad_or_runtime_policy"] == 0
    assert summary["blocked_missing_tool"] == 1
    assert summary["blocked_constraint_mismatch"] == 1
    assert summary["active_leases_total"] == 3
    assert summary["source_run_id"] == "R074"

    classes = [row["coverage_class"] for row in result["action_rows"]]
    assert classes == [
        "allowed_all_reference_args_constrained",
        "allowed_broad_or_runtime_args",
        "blocked_missing_tool",
        "blocked_constraint_mismatch",
    ]

    strict_result = runner.replay(
        benchmark_dir=benchmark_dir,
        source_run_dir=source_dir,
        output_dir=tmp_path / "strict_out",
        run_id="TEST_STRICT",
        domains=("mock",),
        max_tasks_per_domain=None,
        require_all_tool_args_constrained=True,
    )

    strict_summary = strict_result["summary"]
    assert strict_summary["assistant_reference_actions"] == 4
    assert strict_summary["gateway_allowed_reference_actions"] == 1
    assert strict_summary["allowed_all_reference_args_constrained"] == 1
    assert strict_summary["allowed_broad_or_runtime_args"] == 0
    assert strict_summary["blocked_broad_or_runtime_policy"] == 1
    assert strict_summary["blocked_missing_tool"] == 1
    assert strict_summary["blocked_constraint_mismatch"] == 1
    assert strict_summary["active_leases_total"] == 2
    assert strict_summary["inactive_valid_broad_lease_rows_total"] == 1
    assert strict_summary["require_all_tool_args_constrained"] is True

    strict_classes = [row["coverage_class"] for row in strict_result["action_rows"]]
    assert strict_classes == [
        "allowed_all_reference_args_constrained",
        "blocked_broad_or_runtime_policy",
        "blocked_missing_tool",
        "blocked_constraint_mismatch",
    ]
