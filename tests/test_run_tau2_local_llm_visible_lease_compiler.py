import importlib.util
import json
import sys
from pathlib import Path


def _load_runner():
    repo_root = Path(__file__).parents[1]
    for path_entry in (repo_root / "src", repo_root / "scripts"):
        if str(path_entry) not in sys.path:
            sys.path.insert(0, str(path_entry))
    path = repo_root / "scripts" / "run_tau2_local_llm_visible_lease_compiler.py"
    spec = importlib.util.spec_from_file_location("run_tau2_local_llm_visible_lease_compiler", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_local_llm_visible_lease_compiler_scores_stubbed_model(tmp_path):
    runner = _load_runner()
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
                            "reason_for_call": "Please update order #W7654321 for user bob_lee_4321."
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
        \"\"\"Get user details.\"\"\"
        pass

    @is_tool(ToolType.WRITE)
    def update_order_item(self, order_id, product_id):
        \"\"\"Update order item.\"\"\"
        pass
"""
    )

    def fake_runner(command, timeout_seconds):
        return (
            json.dumps(
                {
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
                            "intent_evidence": "visible update order request",
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
                }
            ),
            "",
            0,
            0.25,
        )

    result = runner.run_experiment(
        benchmark_dir=benchmark_dir,
        output_dir=tmp_path / "out",
        run_id="TEST",
        domains=("mock",),
        max_tasks_per_domain=None,
        llama_bin=Path("/tmp/llama"),
        model=Path("/tmp/model.gguf"),
        runner=fake_runner,
    )

    summary = result["summary"]
    assert summary["parse_ok_tasks"] == 1
    assert summary["candidate_tool_slots_total"] == 2
    assert summary["coverage_class_counts"] == {
        "tool_and_non_eval_json_args": 1,
        "tool_only_runtime_or_broad_args_needed": 1,
    }
    assert summary["tool_coverage_rate"] == 1.0
    assert summary["non_eval_json_argument_coverage_rate"] == 0.5


def test_local_llm_visible_lease_compiler_rejects_wrong_equals_any_policy(tmp_path):
    runner = _load_runner()
    benchmark_dir = tmp_path / "tau2-bench"
    domain_dir = benchmark_dir / "data" / "tau2" / "domains" / "mock"
    src_dir = benchmark_dir / "src" / "tau2" / "domains" / "mock"
    domain_dir.mkdir(parents=True)
    src_dir.mkdir(parents=True)

    raw_task = {
        "id": "task_0",
        "user_scenario": {
            "instructions": {
                "reason_for_call": "Please look up user bob_lee_4321."
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
                }
            ],
        },
    }
    (src_dir / "tools.py").write_text(
        """
from tau2.environment.toolkit import ToolType, is_tool


class MockTools:
    @is_tool(ToolType.READ)
    def get_user_details(self, user_id):
        \"\"\"Get user details.\"\"\"
        pass
"""
    )
    tools = runner._parse_assistant_tools(src_dir / "tools.py", domain="mock")
    result = runner.evaluate_task(
        run_id="TEST",
        domain="mock",
        task_id="task_0",
        raw_task=raw_task,
        tools=tools,
        parsed={
            "leases": [
                {
                    "tool": "get_user_details",
                    "intent_evidence": "wrong value regression",
                    "argument_policy": {
                        "user_id": {
                            "mode": "equals_any",
                            "values": ["wrong_user_9999"],
                        }
                    },
                }
            ]
        },
    )

    row = result["coverage_rows"][0]
    assert row["coverage_class"] == "tool_only_runtime_or_broad_args_needed"
    assert row["missing_candidate_argument_keys"] == "user_id"


def test_repair_visible_arguments_fills_selected_tool_only(tmp_path):
    runner = _load_runner()
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
                                "arguments": {"order_id": "#W7654321"},
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
        \"\"\"Get user details.\"\"\"
        pass

    @is_tool(ToolType.WRITE)
    def update_order_item(self, order_id):
        \"\"\"Update order item.\"\"\"
        pass
"""
    )

    def fake_runner(command, timeout_seconds):
        return (
            json.dumps(
                {
                    "leases": [
                        {
                            "tool": "update_order_item",
                            "intent_evidence": "visible update order request",
                            "argument_policy": {
                                "order_id": {
                                    "mode": "runtime_from_prior_tool",
                                    "values": [],
                                }
                            },
                        }
                    ]
                }
            ),
            "",
            0,
            0.1,
        )

    result = runner.run_experiment(
        benchmark_dir=benchmark_dir,
        output_dir=tmp_path / "out",
        run_id="TEST",
        domains=("mock",),
        max_tasks_per_domain=None,
        llama_bin=Path("/tmp/llama"),
        model=Path("/tmp/model.gguf"),
        repair_visible_arguments=True,
        runner=fake_runner,
    )

    summary = result["summary"]
    assert summary["repair_visible_arguments"] is True
    assert summary["visible_arg_repairs_total"] == 1
    assert summary["coverage_class_counts"] == {
        "missing_tool": 1,
        "tool_and_non_eval_json_args": 1,
    }
    assert result["task_rows"][0]["visible_arg_repairs"] == 1
    record = result["records"][0]
    original_policy = record["parsed_model_json"]["leases"][0]["argument_policy"]["order_id"]
    repaired_policy = record["repaired_model_json"]["leases"][0]["argument_policy"]["order_id"]
    assert original_policy["mode"] == "runtime_from_prior_tool"
    assert repaired_policy == {"mode": "equals_any", "values": ["#W7654321"]}


def test_json_schema_constrained_mode_writes_schema_and_passes_flag(tmp_path):
    runner = _load_runner()
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
                            "reason_for_call": "Please look up user bob_lee_4321."
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
        \"\"\"Get user details.\"\"\"
        pass
"""
    )
    seen = {}

    def fake_runner(command, timeout_seconds):
        seen["command"] = command
        schema_path = Path(command[command.index("--json-schema-file") + 1])
        seen["schema"] = json.loads(schema_path.read_text())
        return (
            json.dumps(
                {
                    "leases": [
                        {
                            "tool": "get_user_details",
                            "intent_evidence": "task asks for user lookup",
                            "argument_policy": {
                                "user_id": {
                                    "mode": "equals_any",
                                    "values": ["bob_lee_4321"],
                                }
                            },
                        }
                    ]
                }
            ),
            "",
            0,
            0.1,
        )

    result = runner.run_experiment(
        benchmark_dir=benchmark_dir,
        output_dir=tmp_path / "out",
        run_id="TEST",
        domains=("mock",),
        max_tasks_per_domain=None,
        llama_bin=Path("/tmp/llama"),
        model=Path("/tmp/model.gguf"),
        json_schema_constrained=True,
        runner=fake_runner,
    )

    assert "--json-schema-file" in seen["command"]
    schema = seen["schema"]
    lease_schema = schema["properties"]["leases"]["items"]
    assert lease_schema["properties"]["tool"]["enum"] == ["get_user_details"]
    assert "user_id" in lease_schema["properties"]["argument_policy"]["properties"]
    assert result["summary"]["json_schema_constrained"] is True
    assert result["task_rows"][0]["schema_path"].endswith("schemas/mock_task_0.json")


def test_parse_model_json_finds_first_leases_object():
    runner = _load_runner()
    parsed = runner.parse_model_json(
        "<think>ignored</think>\n```json\n{\"leases\":[{\"tool\":\"x\"}]}\n```"
    )
    assert parsed == {"leases": [{"tool": "x"}]}
