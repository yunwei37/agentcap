import importlib.util
from pathlib import Path


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_tau2_evaluator_backed_replay.py"
    spec = importlib.util.spec_from_file_location("run_tau2_evaluator_backed_replay", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tau2_evaluator_backed_summary_separates_tool_oracle_from_unevaluated_basis():
    runner = _load_runner()
    task_rows = [
        {
            "domain": "mock",
            "task_id": "t0",
            "reward_basis": "DB|COMMUNICATE",
            "tool_oracle_applicable": True,
            "tool_oracle_pass": True,
            "env_oracle_applicable": True,
            "env_reward": 1.0,
            "action_reward": 1.0,
            "unevaluated_basis": "COMMUNICATE",
        },
        {
            "domain": "banking_knowledge",
            "task_id": "t1",
            "reward_basis": "ACTION",
            "tool_oracle_applicable": True,
            "tool_oracle_pass": False,
            "env_oracle_applicable": False,
            "env_reward": 1.0,
            "action_reward": 0.0,
            "unevaluated_basis": "none",
        },
    ]
    event_rows = [
        {"requestor": "assistant", "tool_error": False},
        {"requestor": "user", "tool_error": False},
        {"requestor": "assistant", "tool_error": True},
    ]
    gateway_records = [
        {"decision": {"allowed": True}},
        {"decision": {"allowed": False}},
    ]

    summary = runner.summarize(
        task_rows=task_rows,
        event_rows=event_rows,
        unsupported_rows=[{"domain": "x", "task_id": "bad", "reason": "unsupported"}],
        gateway_records=gateway_records,
        domains=("mock", "banking_knowledge"),
    )

    assert summary["tasks_evaluated"] == 2
    assert summary["unsupported_tasks"] == 1
    assert summary["assistant_reference_actions"] == 2
    assert summary["user_reference_actions_excluded_from_assistant_authority"] == 1
    assert summary["assistant_gateway_allowed"] == 1
    assert summary["assistant_gateway_blocked"] == 1
    assert summary["tool_error_events"] == 1
    assert summary["tool_oracle_applicable_tasks"] == 2
    assert summary["tool_oracle_pass_tasks"] == 1
    assert summary["tool_oracle_pass_rate"] == 0.5
    assert summary["tasks_with_unevaluated_communicate_or_nl_basis"] == 1
    assert summary["reward_basis_counts"] == {"ACTION": 1, "COMMUNICATE": 1, "DB": 1}


def test_tau2_evaluator_backed_event_ids_preserve_domain_task_and_action():
    runner = _load_runner()

    class Action:
        action_id = "a0"

    assert runner._event_id("retail", "task_1", 7, Action()) == "retail:task_1:a0"


def test_tau2_evaluator_backed_empty_csv_keeps_schema_header(tmp_path):
    runner = _load_runner()
    path = tmp_path / "unsupported_tasks.csv"

    runner._write_rows(path, [], runner.UNSUPPORTED_ROW_FIELDS)

    assert path.read_text() == "domain,task_id,reason\n"
