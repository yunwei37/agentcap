import importlib.util
import json
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_tau2_authority_minimization.py"
    spec = importlib.util.spec_from_file_location("analyze_tau2_authority_minimization", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tau2_authority_minimization_compares_reference_leases_to_static_scopes(tmp_path):
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
                    "evaluation_criteria": {
                        "reward_basis": ["DB", "ACTION"],
                        "actions": [
                            {
                                "action_id": "a0",
                                "requestor": "assistant",
                                "name": "lookup_customer",
                                "arguments": {"customer_id": "c0"},
                            },
                            {
                                "action_id": "a1",
                                "requestor": "assistant",
                                "name": "update_customer",
                                "arguments": {"customer_id": "c0", "status": "active"},
                            },
                            {
                                "action_id": "a2",
                                "requestor": "assistant",
                                "name": "update_customer",
                                "arguments": {"customer_id": "c0", "status": "verified"},
                            },
                            {
                                "action_id": "u0",
                                "requestor": "user",
                                "name": "user_confirm",
                                "arguments": {"ok": True},
                            },
                        ],
                    },
                },
                {
                    "id": "task_1",
                    "evaluation_criteria": {
                        "reward_basis": ["ACTION"],
                        "actions": [
                            {
                                "action_id": "u1",
                                "requestor": "user",
                                "name": "user_confirm",
                                "arguments": {"ok": True},
                            },
                        ],
                    },
                },
            ]
        )
    )
    (domain_dir / "split_tasks.json").write_text(json.dumps({"base": ["task_0", "task_1"]}))
    (src_dir / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_discoverable_tool, is_tool


class MockTools:
    @is_tool(ToolType.READ)
    def lookup_customer(self, customer_id):
        pass

    @is_tool(ToolType.WRITE)
    def update_customer(self, customer_id, status):
        pass

    @is_tool(ToolType.GENERIC)
    def transfer_to_human(self, summary):
        pass

    @is_discoverable_tool(ToolType.WRITE)
    def hidden_offer(self, customer_id):
        pass
"""
    )
    (src_dir / "user_tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool


class MockUserTools:
    @is_tool(ToolType.READ)
    def user_confirm(self, ok):
        pass
"""
    )

    result = analyzer.analyze(benchmark_dir, ("mock",))
    summary = result["summary"]
    baselines = summary["baselines"]

    assert summary["tasks"] == 2
    assert summary["reference_actions"] == 5
    assert summary["assistant_reference_actions"] == 3
    assert summary["user_reference_actions"] == 2
    assert summary["ordinary_assistant_tools"] == 3
    assert summary["discoverable_assistant_tools"] == 1
    assert summary["all_tool_objects"] == 5

    intentcap = baselines["intentcap_reference_events"]
    task_reference = baselines["task_reference_tools"]
    domain_regular = baselines["domain_assistant_regular"]
    domain_all = baselines["domain_assistant_all"]
    global_all = baselines["global_all_tools"]

    assert intentcap["exposed_tool_slots_total"] == 3
    assert intentcap["exact_event_leases"] == 3
    assert intentcap["extra_tool_slots_total"] == 0
    assert intentcap["covered_assistant_reference_actions"] == 3
    assert intentcap["event_id_checked"] is True

    assert task_reference["exposed_tool_slots_total"] == 2
    assert task_reference["covered_assistant_reference_actions"] == 3
    assert task_reference["event_id_checked"] is False
    assert task_reference["argument_values_constrained"] is True

    assert domain_regular["exposed_tool_slots_total"] == 6
    assert domain_regular["extra_tool_slots_total"] == 4
    assert domain_regular["tool_slot_over_intentcap_ratio"] == 2.0

    assert domain_all["exposed_tool_slots_total"] == 8
    assert domain_all["extra_tool_slots_total"] == 6
    assert domain_all["discoverable_tool_slots_total"] == 2

    assert global_all["exposed_tool_slots_total"] == 10
    assert global_all["extra_tool_slots_total"] == 8
    assert global_all["covered_assistant_reference_actions"] == 3

    task_rows = {
        (row["baseline"], row["task_id"]): row
        for row in result["task_exposure"]
    }
    assert task_rows[("domain_assistant_regular", "task_1")]["extra_tools"] == 3
    assert task_rows[("intentcap_reference_events", "task_0")]["risk_score"] == 7
    assert task_rows[("intentcap_reference_events", "task_0")]["write_tool_slots"] == 2
    assert result["uncovered_reference_actions"] == []
