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

    synthesized_event, synthesized_bound = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=1,
        model_call={
            "tool": "create_task",
            "arguments": {
                "user_id": "user_1",
                "title": "Important Meeting",
                "_intentcap_synthesized_from_hint": True,
            },
        },
        pending_reference_actions=[action],
    )

    assert synthesized_bound == action
    assert synthesized_event["id"] == "mock:t:create_1"

    wrong_event, wrong_bound = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=2,
        model_call={
            "tool": "create_task",
            "arguments": {"user_id": "user_1", "title": "Wrong"},
        },
        pending_reference_actions=[action],
    )

    assert wrong_bound is None
    assert wrong_event["id"] == "model:mock:t:2"
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


def test_select_tool_schemas_can_expose_only_leased_tools():
    actions = [
        ReferenceAction(
            event_id="mock:t:create_1",
            domain="mock",
            task_id="t",
            action_id="create_1",
            index=0,
            name="create_task",
            requestor="assistant",
            args={"title": "Important Meeting"},
            reward_basis=(),
            object_name="tau2.mock.assistant.create_task",
        )
    ]
    schemas = [
        {"name": "create_task", "parameters": {}},
        {"name": "delete_task", "parameters": {}},
    ]

    assert runner.select_tool_schemas(schemas, actions, tool_exposure="all") == schemas
    assert runner.select_tool_schemas(schemas, actions, tool_exposure="leased") == [
        {"name": "create_task", "parameters": {}}
    ]


def test_summary_counts_feedback_rounds():
    summary = runner.summarize(
        run_id="RTEST",
        task_rows=[
            {
                "parse_ok": True,
                "tool_schema_count": 2,
                "model_calls": 2,
                "initial_model_calls": 1,
                "feedback_model_calls": 1,
                "feedback_attempted": True,
                "stepwise_steps_attempted": 0,
                "stepwise_model_calls": 0,
                "stepwise_empty_retry_steps": 0,
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
        tool_exposure="leased",
        stepwise_max_steps=0,
        stepwise_empty_retries=0,
        dry_run=False,
    )

    assert summary["feedback_rounds"] == 1
    assert summary["tool_exposure"] == "leased"
    assert summary["tool_schema_count_avg"] == 2
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
        empty_retry_count=1,
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
    assert "previous_empty_action_retries" in prompt
    assert "Hidden reference" not in prompt
    assert "evaluation_criteria" not in prompt


def test_state_grounded_arg_hints_only_expose_visible_lease_values():
    visible = ReferenceAction(
        event_id="airline:t:visible",
        domain="airline",
        task_id="t",
        action_id="visible",
        index=0,
        name="get_reservation_details",
        requestor="assistant",
        args={"reservation_id": "Q69X3R"},
        reward_basis=(),
        object_name="tau2.airline.assistant.get_reservation_details",
    )
    hidden = ReferenceAction(
        event_id="airline:t:hidden",
        domain="airline",
        task_id="t",
        action_id="hidden",
        index=1,
        name="get_reservation_details",
        requestor="assistant",
        args={"reservation_id": "HIDDEN1"},
        reward_basis=(),
        object_name="tau2.airline.assistant.get_reservation_details",
    )

    hints = runner.build_state_grounded_arg_hints(
        pending_reference_actions=[visible, hidden],
        raw_task={"id": "t", "evaluation_criteria": {"actions": [{"arguments": {"reservation_id": "HIDDEN1"}}]}},
        action_rows=[
            {
                "executed": True,
                "tool_result_preview": '{"reservations":["MZDDS4","Q69X3R"]}',
            }
        ],
        tools=[{"name": "get_reservation_details", "parameters": {}}],
    )

    assert hints == [
        {
            "tool": "get_reservation_details",
            "arguments": {"reservation_id": "Q69X3R"},
            "complete_arguments": True,
            "grounding": "active lease argument values also found in visible task text or executed tool results",
        }
    ]


def test_step_prompt_can_include_state_grounded_arg_hints_without_reference_actions():
    prompt = runner.build_step_prompt(
        domain="airline",
        raw_task={
            "id": "t",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "get_reservation_details",
                        "arguments": {"reservation_id": "Hidden reference"},
                    }
                ]
            },
        },
        tools=[{"name": "get_reservation_details", "parameters": {}}],
        step_index=2,
        action_rows=[],
        state_grounded_arg_hints=[
            {
                "tool": "get_reservation_details",
                "arguments": {"reservation_id": "Q69X3R"},
                "complete_arguments": True,
                "grounding": "active lease argument values also found in visible task text or executed tool results",
            }
        ],
    )

    assert "state_grounded_authorized_argument_hints" in prompt
    assert "Q69X3R" in prompt
    assert "Hidden reference" not in prompt
    assert "evaluation_criteria" not in prompt


def test_single_hint_fallback_requires_exactly_one_complete_hint():
    incomplete = {
        "tool": "create_task",
        "arguments": {"user_id": "user_1"},
        "complete_arguments": False,
    }
    complete = {
        "tool": "create_task",
        "arguments": {"user_id": "user_1", "title": "Important Meeting"},
        "complete_arguments": True,
    }

    assert runner.build_single_hint_fallback_call([incomplete]) is None
    assert runner.build_single_hint_fallback_call([complete, complete]) is None

    call = runner.build_single_hint_fallback_call([complete])

    assert call == {
        "tool": "create_task",
        "arguments": {
            "user_id": "user_1",
            "title": "Important Meeting",
            "_intentcap_synthesized_from_hint": True,
        },
    }


def test_hint_choice_prompt_omits_reference_actions():
    prompt = runner.build_hint_choice_prompt(
        domain="retail",
        raw_task={
            "id": "t",
            "instruction": "Handle the visible order.",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "get_order_details",
                        "arguments": {"order_id": "HIDDEN"},
                    }
                ]
            },
        },
        step_index=3,
        action_rows=[
            {
                "round": "step_2",
                "model_tool": "get_user_details",
                "model_args_json": '{"user_id": "u1"}',
                "gateway_action": "execute",
                "gateway_reason": "lease matched",
                "executed": True,
                "tool_result_preview": '{"orders":["#W2378156"]}',
            }
        ],
        complete_hints=[
            {
                "tool": "get_order_details",
                "arguments": {"order_id": "#W2378156"},
                "complete_arguments": True,
                "grounding": "visible",
            }
        ],
    )

    assert "complete_visible_authorized_hints" in prompt
    assert "hint_0" in prompt
    assert "#W2378156" in prompt
    assert "HIDDEN" not in prompt
    assert "evaluation_criteria" not in prompt


def test_hint_choice_fallback_requires_valid_hint_id():
    hints = [
        {
            "tool": "get_order_details",
            "arguments": {"order_id": "#W2378156"},
            "complete_arguments": True,
        },
        {
            "tool": "get_product_details",
            "arguments": {"product_id": "1656367028"},
            "complete_arguments": True,
        },
    ]

    assert runner.build_hint_choice_fallback_call(hints, {"selected_hint_id": None}) is None
    assert runner.build_hint_choice_fallback_call(hints, {"selected_hint_id": "hint_99"}) is None
    assert runner.build_hint_choice_fallback_call(hints, {"selected_hint_id": "unknown"}) is None

    call = runner.build_hint_choice_fallback_call(hints, {"selected_hint_id": "hint_1"})

    assert call == {
        "tool": "get_product_details",
        "arguments": {
            "product_id": "1656367028",
            "_intentcap_synthesized_from_hint": True,
            "_intentcap_hint_choice_id": "hint_1",
        },
    }


def test_step_prompt_default_omits_empty_retry_instruction():
    prompt = runner.build_step_prompt(
        domain="mock",
        raw_task={"id": "t", "instruction": "Update the task."},
        tools=[{"name": "create_task", "parameters": {}}],
        step_index=1,
        action_rows=[],
    )

    assert "previous_empty_action_retries" not in prompt
    assert "previous step returned no tool call" not in prompt
