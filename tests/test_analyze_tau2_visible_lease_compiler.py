import importlib.util
import json
import sys
from pathlib import Path


def _load_analyzer():
    repo_root = Path(__file__).parents[1]
    for path_entry in (repo_root / "src", repo_root / "scripts"):
        if str(path_entry) not in sys.path:
            sys.path.insert(0, str(path_entry))
    path = repo_root / "scripts" / "analyze_tau2_visible_lease_compiler.py"
    spec = importlib.util.spec_from_file_location("analyze_tau2_visible_lease_compiler", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_visible_lease_compiler_scores_visible_and_runtime_arguments(tmp_path):
    analyzer = _load_analyzer()
    benchmark_dir = tmp_path / "tau2-bench"
    domain_dir = benchmark_dir / "data" / "tau2" / "domains" / "mock"
    src_dir = benchmark_dir / "src" / "tau2" / "domains" / "mock"
    domain_dir.mkdir(parents=True)
    src_dir.mkdir(parents=True)

    (domain_dir / "tasks.json").write_text(
        json.dumps(
            [
                {
                    "id": "task_0",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": "Please update order #W1234567 for user alice_ng_1234.",
                            "known_info": "The product id is not visible yet.",
                        }
                    },
                    "evaluation_criteria": {
                        "reward_basis": ["ACTION"],
                        "actions": [
                            {
                                "action_id": "a0",
                                "requestor": "assistant",
                                "name": "get_user_details",
                                "arguments": {"user_id": "alice_ng_1234"},
                            },
                            {
                                "action_id": "a1",
                                "requestor": "assistant",
                                "name": "update_order_item",
                                "arguments": {
                                    "order_id": "#W1234567",
                                    "product_id": "9999999999",
                                },
                            },
                            {
                                "action_id": "a2",
                                "requestor": "assistant",
                                "name": "send_email",
                                "arguments": {"email": "nobody@example.com"},
                            },
                        ],
                    },
                },
                {
                    "id": "task_1",
                    "user_scenario": {
                        "instructions": {
                            "reason_for_call": "Please lookup ticket ABC123."
                        }
                    },
                    "evaluation_criteria": {
                        "reward_basis": ["ACTION"],
                        "actions": [
                            {
                                "action_id": "b0",
                                "requestor": "assistant",
                                "name": "lookup_ticket",
                                "arguments": {"ticket_code": "ABC123"},
                            }
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
        \"\"\"Get details for a user account.\"\"\"
        pass

    @is_tool(ToolType.WRITE)
    def update_order_item(self, order_id, product_id):
        \"\"\"Update an order item after the product id is discovered.\"\"\"
        pass

    @is_tool(ToolType.WRITE)
    def send_email(self, email):
        \"\"\"Send an email to a recipient.\"\"\"
        pass

    @is_tool(ToolType.READ)
    def lookup_ticket(self, ticket_code):
        \"\"\"Lookup ticket code for a support request.\"\"\"
        pass
"""
    )

    result = analyzer.analyze(
        benchmark_dir=benchmark_dir,
        run_id="TEST",
        domains=("mock",),
        max_tasks_per_domain=None,
    )

    summary = result["summary"]
    assert summary["tasks_evaluated"] == 2
    assert summary["assistant_reference_actions"] == 4
    assert summary["coverage_class_counts"]["tool_and_non_eval_json_args"] == 1
    assert summary["coverage_class_counts"]["tool_only_runtime_or_broad_args_needed"] == 2
    assert summary["coverage_class_counts"]["missing_tool"] == 1

    coverage_by_action = {
        row["action_id"]: row["coverage_class"]
        for row in result["reference_coverage"]
    }
    assert coverage_by_action == {
        "a0": "tool_and_non_eval_json_args",
        "a1": "tool_only_runtime_or_broad_args_needed",
        "a2": "missing_tool",
        "b0": "tool_only_runtime_or_broad_args_needed",
    }

    candidate_tools = {
        (row["task_id"], row["tool"]): row
        for row in result["candidate_leases"]
    }
    assert set(candidate_tools) == {
        ("task_0", "get_user_details"),
        ("task_0", "update_order_item"),
        ("task_1", "lookup_ticket"),
    }
    assert "visible_arg:user_id" in candidate_tools[("task_0", "get_user_details")]["evidence"]
    assert "product_id" in candidate_tools[("task_0", "update_order_item")]["broad_argument_keys"]
    assert "ticket_code" in candidate_tools[("task_1", "lookup_ticket")]["broad_argument_keys"]


def test_value_grounding_handles_nested_structures():
    analyzer = _load_analyzer()
    visible = json.dumps(
        {
            "order": "#W1234567",
            "items": ["1111111111", "2222222222"],
            "confirmed": True,
        }
    )
    assert analyzer._value_is_grounded("#W1234567", visible)
    assert analyzer._value_is_grounded(["1111111111", "2222222222"], visible)
    assert analyzer._value_is_grounded({"ok": True}, visible)
    assert not analyzer._value_is_grounded({"missing": "3333333333"}, visible)
