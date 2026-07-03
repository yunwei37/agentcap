import importlib.util
import json
from pathlib import Path


def _load_probe():
    path = Path(__file__).parents[1] / "scripts" / "probe_tau2_bench.py"
    spec = importlib.util.spec_from_file_location("probe_tau2_bench", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tau2_probe_parses_tasks_actions_and_tool_decorators(tmp_path):
    probe_module = _load_probe()
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
                    "user_tools": ["user_lookup"],
                    "required_documents": ["policy.md"],
                    "initial_state": {
                        "initialization_actions": [
                            {"name": "seed_customer", "arguments": {"customer_id": "c0"}},
                        ],
                    },
                    "evaluation_criteria": {
                        "reward_basis": ["DB", "ACTION"],
                        "actions": [
                            {
                                "action_id": "a0",
                                "requestor": "assistant",
                                "name": "create_case",
                                "arguments": {"customer_id": "c0", "summary": "x"},
                            },
                            {
                                "action_id": "u0",
                                "requestor": "user",
                                "name": "user_lookup",
                                "arguments": {"query": "billing"},
                            },
                        ],
                    },
                },
            ]
        )
    )
    (domain_dir / "tasks_voice.json").write_text(json.dumps([{"id": "voice_0"}]))
    (domain_dir / "split_tasks.json").write_text(json.dumps({"base": ["task_0"], "dev": []}))
    (domain_dir / "policy.md").write_text("# Policy\n\n## Cases\n")
    (domain_dir / "db.json").write_text(json.dumps({"customers": [], "cases": []}))
    (src_dir / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_discoverable_tool, is_tool


class MockTools:
    @is_tool(ToolType.WRITE)
    def create_case(self, customer_id, summary):
        \"\"\"Create a support case.\"\"\"

    @is_tool(tool_type=ToolType.GENERIC)
    def calculate(self, expression):
        \"\"\"Calculate a helper value.\"\"\"

    @is_discoverable_tool(tool_type=ToolType.READ)
    def hidden_lookup(self, query):
        \"\"\"Look up a hidden record.\"\"\"
"""
    )
    (src_dir / "user_tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool


class MockUserTools:
    @is_tool(ToolType.READ)
    def user_lookup(self, query):
        \"\"\"Search as the simulated user.\"\"\"
"""
    )

    result = probe_module.probe(benchmark_dir)
    summary = result["summary"]
    domain_row = result["domain_rows"][0]
    tool_rows = {(row["requestor"], row["name"]): row for row in result["tool_rows"]}

    assert summary["domains"] == 1
    assert summary["domain_names"] == ["mock"]
    assert summary["tasks"] == 1
    assert summary["voice_tasks"] == 1
    assert summary["evaluation_actions"] == 2
    assert summary["initialization_actions"] == 1
    assert summary["assistant_tools"] == 2
    assert summary["assistant_discoverable_tools"] == 1
    assert summary["user_tools"] == 1
    assert summary["tool_type_counts"] == {
        "assistant:generic": 1,
        "assistant:read": 1,
        "assistant:write": 1,
        "user:read": 1,
    }

    assert domain_row["tasks_with_actions"] == 1
    assert domain_row["tasks_with_user_tools"] == 1
    assert domain_row["tasks_with_required_documents"] == 1
    assert domain_row["policy_heading_count"] == 2
    assert domain_row["db_tables"] == "cases|customers"
    assert domain_row["top_actions"] == "create_case:1|user_lookup:1"
    assert domain_row["action_requestors"] == "assistant:1|user:1"
    assert domain_row["reward_basis_counts"] == "ACTION:1|DB:1"

    assert tool_rows[("assistant", "create_case")]["tool_type"] == "write"
    assert tool_rows[("assistant", "calculate")]["tool_type"] == "generic"
    assert tool_rows[("assistant", "hidden_lookup")]["discoverable"] is True
    assert tool_rows[("assistant", "hidden_lookup")]["tool_type"] == "read"
    assert tool_rows[("user", "user_lookup")]["tool_type"] == "read"

    action_names = [row["name"] for row in result["action_rows"]]
    assert action_names == ["create_case", "user_lookup"]
