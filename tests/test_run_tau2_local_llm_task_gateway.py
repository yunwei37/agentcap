from pathlib import Path

import scripts.run_tau2_local_llm_task_gateway as runner
from run_tau2_reference_actions_live_gateway import ReferenceAction
from intentcap.live_gateway import LiveToolGateway


def test_parse_model_json_extracts_fenced_actions():
    parsed = runner.parse_model_json(
        '```json\n{"actions":[{"tool":"create_task","arguments":{"user_id":"u","title":"t"}}]}\n```'
    )

    calls = runner.normalize_model_calls(parsed)

    assert calls == [{"tool": "create_task", "arguments": {"user_id": "u", "title": "t"}}]


def test_bind_model_call_adds_event_id_only_for_exact_reference_match():
    action = ReferenceAction(
        event_id="mock:t:create_1",
        domain="mock",
        task_id="t",
        action_id="create_1",
        index=0,
        name="create_task",
        requestor="assistant",
        args={"user_id": "user_1", "title": "Important Meeting"},
        reward_basis=(),
        object_name="tau2.mock.assistant.create_task",
    )

    event, bound = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=0,
        model_call={
            "tool": "create_task",
            "arguments": {"user_id": "user_1", "title": "Important Meeting"},
        },
        pending_reference_actions=[action],
    )

    assert bound == action
    assert event["id"] == "mock:t:create_1"
    assert event["args"]["intentcap_event_id"] == "mock:t:create_1"

    wrong_event, wrong_bound = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=1,
        model_call={
            "tool": "create_task",
            "arguments": {"user_id": "user_1", "title": "Wrong"},
        },
        pending_reference_actions=[action],
    )

    assert wrong_bound is None
    assert wrong_event["id"] == "model:mock:t:1"
    assert "intentcap_event_id" not in wrong_event["args"]


def test_exact_task_trace_allows_bound_call_and_blocks_off_lease_call():
    action = ReferenceAction(
        event_id="mock:t:create_1",
        domain="mock",
        task_id="t",
        action_id="create_1",
        index=0,
        name="create_task",
        requestor="assistant",
        args={"user_id": "user_1", "title": "Important Meeting"},
        reward_basis=(),
        object_name="tau2.mock.assistant.create_task",
    )
    trace = runner.build_task_trace("mock", "t", [action])
    allowed_event, _ = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=0,
        model_call={
            "tool": "create_task",
            "arguments": {"user_id": "user_1", "title": "Important Meeting"},
        },
        pending_reference_actions=[action],
    )
    blocked_event, _ = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=1,
        model_call={
            "tool": "create_task",
            "arguments": {"user_id": "user_1", "title": "Wrong"},
        },
        pending_reference_actions=[action],
    )
    tools = {
        "tau2.mock.assistant.create_task": lambda **kwargs: {
            "ok": True,
            "kwargs": kwargs,
        }
    }

    gateway = LiveToolGateway(trace, tools)
    allowed = gateway.call(allowed_event)
    blocked = gateway.call(blocked_event)

    assert allowed["executed"] is True
    assert allowed["decision"]["allowed"] is True
    assert blocked["executed"] is False
    assert blocked["decision"]["reason"] == "no matching lease"


def test_safe_id_keeps_paths_simple():
    assert runner._safe_id("telecom", "[mobile]a/b") == "telecom_mobile_a_b"


def test_scope_note_distinguishes_mock_from_cross_domain_pilots():
    assert "mock-domain pilot" in runner._scope_note(("mock",))
    assert "small fixed-domain pilot" in runner._scope_note(("airline", "retail"))


def test_feedback_prompt_reports_blocks_without_reference_actions():
    prompt = runner.build_feedback_prompt(
        domain="mock",
        raw_task={
            "id": "t",
            "instruction": "Update the task.",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "create_task",
                        "arguments": {"title": "Hidden reference"},
                    }
                ]
            },
        },
        tools=[{"name": "create_task", "parameters": {}}],
        blocked_calls=[
            {
                "round": "initial",
                "index": 0,
                "tool": "create_task",
                "arguments": {"title": "Wrong"},
                "reason": "no matching lease",
                "object": "tau2.mock.assistant.create_task",
            }
        ],
        action_rows=[
            {
                "round": "initial",
                "model_tool": "create_task",
                "model_args_json": '{"title": "Wrong"}',
                "gateway_action": "block",
                "gateway_reason": "no matching lease",
                "executed": False,
            }
        ],
    )

    assert "no matching lease" in prompt
    assert "Hidden reference" not in prompt
    assert "evaluation_criteria" not in prompt


def test_summary_counts_feedback_rounds():
    summary = runner.summarize(
        run_id="RTEST",
        task_rows=[
            {
                "parse_ok": True,
                "model_calls": 2,
                "initial_model_calls": 1,
                "feedback_model_calls": 1,
                "feedback_attempted": True,
                "stepwise_steps_attempted": 0,
                "stepwise_model_calls": 0,
                "reference_actions": 1,
                "bound_reference_calls": 1,
                "off_lease_calls_blocked": 1,
                "exact_sequence_match": False,
                "all_reference_actions_executed": True,
                "action_reward": 1.0,
                "env_reward": 1.0,
                "tool_oracle_applicable": True,
                "tool_oracle_pass": True,
            }
        ],
        action_rows=[
            {
                "round": "initial",
                "gateway_allowed": False,
                "executed": False,
                "tool_error": False,
            },
            {
                "round": "feedback_1",
                "gateway_allowed": True,
                "executed": True,
                "tool_error": False,
            },
        ],
        unsupported_rows=[],
        domains=(),
        benchmark_dir=Path("."),
        llama_bin=Path("/missing/llama"),
        model=Path("/missing/model"),
        n_predict=1,
        ctx_size=1,
        gpu_layers=0,
        timeout_seconds=1,
        max_tasks_per_domain=1,
        feedback_rounds=1,
        stepwise_max_steps=0,
        dry_run=False,
    )

    assert summary["feedback_rounds"] == 1
    assert summary["feedback_attempted_tasks"] == 1
    assert summary["initial_gateway_blocked"] == 1
    assert summary["feedback_gateway_allowed"] == 1


def test_step_prompt_reports_tool_results_without_reference_actions():
    prompt = runner.build_step_prompt(
        domain="mock",
        raw_task={
            "id": "t",
            "instruction": "Update the task.",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "create_task",
                        "arguments": {"title": "Hidden reference"},
                    }
                ]
            },
        },
        tools=[{"name": "create_task", "parameters": {}}],
        step_index=2,
        action_rows=[
            {
                "round": "step_1",
                "model_tool": "read_task",
                "model_args_json": '{"task_id": "task_1"}',
                "gateway_action": "execute",
                "gateway_reason": "lease matched",
                "executed": True,
                "tool_result_preview": '{"title": "Visible tool result"}',
            }
        ],
    )

    assert "Visible tool result" in prompt
    assert "Hidden reference" not in prompt
    assert "evaluation_criteria" not in prompt
