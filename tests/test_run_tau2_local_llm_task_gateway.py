import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_tau2_local_llm_task_gateway as runner
from run_tau2_reference_actions_live_gateway import ReferenceAction
from intentcap.live_gateway import LiveToolGateway


def test_parse_model_json_extracts_fenced_actions():
    parsed = runner.parse_model_json(
        '```json\n{"actions":[{"tool":"create_task","arguments":{"user_id":"u","title":"t"}}]}\n```'
    )

    calls = runner.normalize_model_calls(parsed)

    assert calls == [{"tool": "create_task", "arguments": {"user_id": "u", "title": "t"}}]


def test_parse_model_json_prefers_action_envelope_after_thought_json():
    parsed = runner.parse_model_json(
        '<think>Use {"user_id":"u"} as the argument.</think>\n'
        '```json\n'
        '{"actions":[{"tool":"get_user_details","arguments":{"user_id":"u"}}],'
        '"final_response":""}\n'
        '```'
    )

    calls = runner.normalize_model_calls(parsed)

    assert calls == [{"tool": "get_user_details", "arguments": {"user_id": "u"}}]


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


def test_repair_map_marker_prefers_matching_reference_event_for_scoring():
    earlier = ReferenceAction(
        event_id="retail:3:3_4",
        domain="retail",
        task_id="3",
        action_id="3_4",
        index=4,
        name="get_user_details",
        requestor="assistant",
        args={"user_id": "yusuf_rossi_9620"},
        reward_basis=(),
        object_name="tau2.retail.assistant.get_user_details",
    )
    repair_target = ReferenceAction(
        event_id="retail:3:3_11",
        domain="retail",
        task_id="3",
        action_id="3_11",
        index=11,
        name="get_user_details",
        requestor="assistant",
        args={"user_id": "yusuf_rossi_9620"},
        reward_basis=(),
        object_name="tau2.retail.assistant.get_user_details",
    )

    event, bound = runner.bind_model_call(
        domain="retail",
        task_id="3",
        index=0,
        model_call={
            "tool": "get_user_details",
            "arguments": {
                "user_id": "yusuf_rossi_9620",
                "_intentcap_repair_map_event_id": "retail:3:3_11",
            },
        },
        pending_reference_actions=[earlier, repair_target],
        include_reference_event_ids=False,
    )

    assert bound == repair_target
    assert event["id"] == "retail:3:3_11"
    assert "intentcap_event_id" not in event["args"]


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
    assert runner.select_tool_schemas(
        schemas,
        actions,
        tool_exposure="leased",
        active_tool_names={"delete_task"},
    ) == [{"name": "delete_task", "parameters": {}}]


def test_compiler_corpus_trace_uses_only_strict_saved_compiler_leases():
    trace, active_tools, active_objects = runner.build_compiler_corpus_task_trace(
        domain="mock",
        task_id="t",
        compiler_record={
            "repaired_model_json": {
                "leases": [
                    {
                        "tool": "create_task",
                        "argument_policy": {
                            "user_id": {"mode": "equals_any", "values": ["user_1"]},
                            "title": {"mode": "equals_any", "values": ["Important"]},
                        },
                    },
                    {
                        "tool": "delete_task",
                        "argument_policy": {
                            "task_id": {"mode": "runtime_value", "values": []},
                        },
                    },
                    {
                        "tool": "unknown_tool",
                        "argument_policy": {},
                    },
                ]
            }
        },
        tools_by_name={
            "create_task": SimpleNamespace(
                name="create_task",
                arguments=("user_id", "title"),
            ),
            "delete_task": SimpleNamespace(
                name="delete_task",
                arguments=("task_id",),
            ),
        },
    )

    assert active_tools == {"create_task"}
    assert active_objects == {"tau2.mock.assistant.create_task"}
    assert len(trace["leases"]) == 1
    assert trace["labels"][runner.TRUSTED_TASK_INTENT]["allowed"]["tool_select"] == [
        "mock.create_task.tool_choice"
    ]
    assert trace["metadata"]["selected_compiler_leases"] == 3
    assert trace["metadata"]["active_compiler_leases"] == 1
    assert trace["metadata"]["inactive_broad_or_runtime_arg_leases"] == 1
    assert trace["metadata"]["invalid_tool_leases"] == 1
    assert trace["metadata"]["runtime_bindable_compiler_lease_count"] == 1

    gateway = LiveToolGateway(
        trace,
        {
            "tau2.mock.assistant.create_task": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )
    allowed = gateway.call(
        {
            "id": "model:mock:t:0",
            "op": "tool.call",
            "object": "tau2.mock.assistant.create_task",
            "args": {"user_id": "user_1", "title": "Important"},
            "decision": "mock.create_task.tool_choice",
            "mode": "tool_select",
            "control_provenance": [runner.TRUSTED_TASK_INTENT],
            "data_provenance": [runner.TRUSTED_TASK_INTENT],
        }
    )
    reference_action = ReferenceAction(
        event_id="mock:t:create_1",
        domain="mock",
        task_id="t",
        action_id="create_1",
        index=0,
        name="create_task",
        requestor="assistant",
        args={"user_id": "user_1", "title": "Important"},
        reward_basis=(),
        object_name="tau2.mock.assistant.create_task",
    )
    bound_event, bound_action = runner.bind_model_call(
        domain="mock",
        task_id="t",
        index=3,
        model_call={
            "tool": "create_task",
            "arguments": {"user_id": "user_1", "title": "Important"},
        },
        pending_reference_actions=[reference_action],
        include_reference_event_ids=False,
    )
    bound_allowed = gateway.call(bound_event)
    blocked = gateway.call(
        {
            "id": "model:mock:t:1",
            "op": "tool.call",
            "object": "tau2.mock.assistant.create_task",
            "args": {"user_id": "user_1", "title": "Wrong"},
            "decision": "mock.create_task.tool_choice",
            "mode": "tool_select",
            "control_provenance": [runner.TRUSTED_TASK_INTENT],
            "data_provenance": [runner.TRUSTED_TASK_INTENT],
        }
    )
    extra_arg_blocked = gateway.call(
        {
            "id": "model:mock:t:2",
            "op": "tool.call",
            "object": "tau2.mock.assistant.create_task",
            "args": {
                "user_id": "user_1",
                "title": "Important",
                "extra_scope": "admin",
            },
            "decision": "mock.create_task.tool_choice",
            "mode": "tool_select",
            "control_provenance": [runner.TRUSTED_TASK_INTENT],
            "data_provenance": [runner.TRUSTED_TASK_INTENT],
        }
    )

    assert allowed["executed"] is True
    assert bound_action == reference_action
    assert "intentcap_event_id" not in bound_event["args"]
    assert bound_allowed["executed"] is True
    assert blocked["executed"] is False
    assert blocked["decision"]["reason"] == "no matching lease"
    assert extra_arg_blocked["executed"] is False
    assert extra_arg_blocked["decision"]["reason"] == "no matching lease"


def test_load_compiler_records_from_dirs_unions_leases_by_task(tmp_path):
    run_a = tmp_path / "R-A"
    run_b = tmp_path / "R-B"
    run_a.mkdir()
    run_b.mkdir()
    duplicate_create = {
        "tool": "create_task",
        "argument_policy": {
            "user_id": {"mode": "equals_any", "values": ["user_1"]},
            "title": {"mode": "equals_any", "values": ["Important"]},
        },
        "intent_evidence": "source A",
    }
    run_a_record = {
        "run_id": "R-A",
        "domain": "mock",
        "task_id": "t",
        "task_row": {"parse_ok": True},
        "repaired_model_json": {"leases": [duplicate_create]},
    }
    run_b_record = {
        "run_id": "R-B",
        "domain": "mock",
        "task_id": "t",
        "repaired_model_json": {
            "leases": [
                {
                    **duplicate_create,
                    "intent_evidence": "source B",
                },
                {
                    "tool": "delete_task",
                    "argument_policy": {
                        "task_id": {"mode": "runtime_value", "values": []}
                    },
                },
            ]
        },
    }
    (run_a / "samples.jsonl").write_text(json.dumps(run_a_record) + "\n")
    (run_b / "samples.jsonl").write_text(json.dumps(run_b_record) + "\n")

    records = runner.load_compiler_records_from_dirs((run_a, run_b))

    merged = records[("mock", "t")]
    leases = merged["repaired_model_json"]["leases"]
    assert merged["compiler_source_dirs"] == [str(run_a), str(run_b)]
    assert merged["compiler_source_parse_ok_count"] == 2
    assert merged["task_row"]["parse_ok"] is True
    assert [lease["tool"] for lease in leases] == ["create_task", "delete_task"]


def test_compiler_runtime_binding_requires_prior_tool_result_evidence():
    trace, active_tools, active_objects = runner.build_compiler_corpus_task_trace(
        domain="mock",
        task_id="t",
        compiler_record={
            "repaired_model_json": {
                "leases": [
                    {
                        "tool": "get_user_details",
                        "argument_policy": {
                            "user_id": {"mode": "equals_any", "values": ["user_1"]},
                        },
                    },
                    {
                        "tool": "cancel_reservation",
                        "argument_policy": {
                            "reservation_id": {
                                "mode": "runtime_from_prior_tool",
                                "values": [],
                            },
                        },
                    },
                ]
            }
        },
        tools_by_name={
            "get_user_details": SimpleNamespace(
                name="get_user_details",
                arguments=("user_id",),
            ),
            "cancel_reservation": SimpleNamespace(
                name="cancel_reservation",
                arguments=("reservation_id",),
            ),
        },
        expose_runtime_bindable=True,
    )

    assert active_tools == {"get_user_details", "cancel_reservation"}
    assert active_objects == {
        "tau2.mock.assistant.get_user_details",
        "tau2.mock.assistant.cancel_reservation",
    }
    assert trace["metadata"]["runtime_bindable_tools_exposed"] is True

    event = {
        "id": "model:mock:t:1",
        "op": "tool.call",
        "object": "tau2.mock.assistant.cancel_reservation",
        "args": {"reservation_id": "Q69X3R"},
        "decision": "mock.cancel_reservation.tool_choice",
        "mode": "tool_select",
        "control_provenance": [runner.TRUSTED_TASK_INTENT],
        "data_provenance": [runner.TRUSTED_TASK_INTENT],
    }
    gateway_without_evidence = LiveToolGateway(
        trace,
        {
            "tau2.mock.assistant.cancel_reservation": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )

    blocked, blocked_binding, blocked_activation = (
        runner.call_gateway_with_optional_runtime_binding(
            gateway=gateway_without_evidence,
            event=event,
            domain="mock",
            task_id="t",
            index=1,
            action_rows=[],
            enabled=True,
        )
    )

    assert blocked["executed"] is False
    assert blocked_binding["attempted"] is True
    assert blocked_binding["allowed"] is False
    assert blocked_binding["reason"].startswith("missing runtime evidence")
    assert blocked_activation["attempted"] is False

    trace_with_evidence, _, _ = runner.build_compiler_corpus_task_trace(
        domain="mock",
        task_id="t",
        compiler_record={
            "repaired_model_json": {
                "leases": [
                    {
                        "tool": "cancel_reservation",
                        "argument_policy": {
                            "reservation_id": {
                                "mode": "runtime_from_prior_tool",
                                "values": [],
                            },
                        },
                    },
                ]
            }
        },
        tools_by_name={
            "cancel_reservation": SimpleNamespace(
                name="cancel_reservation",
                arguments=("reservation_id",),
            ),
        },
        expose_runtime_bindable=True,
    )
    gateway_with_evidence = LiveToolGateway(
        trace_with_evidence,
        {
            "tau2.mock.assistant.cancel_reservation": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )
    allowed, allowed_binding, allowed_activation = (
        runner.call_gateway_with_optional_runtime_binding(
            gateway=gateway_with_evidence,
            event=event,
            domain="mock",
            task_id="t",
            index=1,
            action_rows=[
                {
                    "executed": True,
                    "tool_result_preview": '{"reservations":[{"reservation_id":"Q69X3R"}]}',
                }
            ],
            enabled=True,
        )
    )

    assert allowed["executed"] is True
    assert allowed_binding["attempted"] is True
    assert allowed_binding["allowed"] is True
    assert allowed_binding["args"] == {"reservation_id": "Q69X3R"}
    assert allowed_binding["lease_id"].startswith("compiler-runtime-live:mock:t:1")
    assert allowed_activation["attempted"] is False
    assert len(trace_with_evidence["leases"]) == 1


def test_compiler_runtime_binding_rejects_extra_arguments():
    trace, _, _ = runner.build_compiler_corpus_task_trace(
        domain="mock",
        task_id="t",
        compiler_record={
            "repaired_model_json": {
                "leases": [
                    {
                        "tool": "cancel_reservation",
                        "argument_policy": {
                            "reservation_id": {
                                "mode": "runtime_from_prior_tool",
                                "values": [],
                            },
                        },
                    },
                ]
            }
        },
        tools_by_name={
            "cancel_reservation": SimpleNamespace(
                name="cancel_reservation",
                arguments=("reservation_id",),
            ),
        },
        expose_runtime_bindable=True,
    )
    gateway = LiveToolGateway(
        trace,
        {
            "tau2.mock.assistant.cancel_reservation": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )

    blocked, binding, activation = runner.call_gateway_with_optional_runtime_binding(
        gateway=gateway,
        event={
            "id": "model:mock:t:1",
            "op": "tool.call",
            "object": "tau2.mock.assistant.cancel_reservation",
            "args": {"reservation_id": "Q69X3R", "extra_scope": "admin"},
            "decision": "mock.cancel_reservation.tool_choice",
            "mode": "tool_select",
            "control_provenance": [runner.TRUSTED_TASK_INTENT],
            "data_provenance": [runner.TRUSTED_TASK_INTENT],
        },
        domain="mock",
        task_id="t",
        index=1,
        action_rows=[
            {
                "executed": True,
                "tool_result_preview": '{"reservation_id":"Q69X3R","extra_scope":"admin"}',
            }
        ],
        enabled=True,
    )

    assert blocked["executed"] is False
    assert binding["attempted"] is True
    assert "argument key set mismatch" in binding["reason"]
    assert activation["attempted"] is False


def test_tool_registry_executes_unbound_compiler_event_with_synthetic_id(monkeypatch):
    calls = []

    class FakeToolCall:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeEnv:
        def get_response(self, tool_call):
            calls.append(tool_call)
            return {"ok": True, "tool": tool_call.name, "id": tool_call.id}

    monkeypatch.setattr(
        runner,
        "_import_attr",
        lambda module_name, attr_name: FakeToolCall,
    )
    invocations = []

    tools = runner.build_tool_registry(
        [],
        FakeEnv(),
        invocations,
        object_names={"tau2.mock.assistant.create_task"},
    )
    result = tools["tau2.mock.assistant.create_task"](title="Important")

    assert result == {"ok": True, "tool": "create_task", "id": "model:0"}
    assert calls[0].id == "model:0"
    assert calls[0].name == "create_task"
    assert calls[0].arguments == {"title": "Important"}
    assert invocations == [
        {
            "event_id": "model:0",
            "tool": "create_task",
            "object": "tau2.mock.assistant.create_task",
            "args": {"title": "Important"},
        }
    ]


def test_reference_action_parser_keeps_user_actions_separate_from_assistant_leases():
    criteria = {
        "reward_basis": ["ENV_ASSERTION"],
        "actions": [
            {
                "action_id": "enable_roaming_0",
                "requestor": "assistant",
                "name": "enable_roaming",
                "arguments": {"customer_id": "C1001", "line_id": "L1002"},
            },
            {
                "action_id": "toggle_roaming_1",
                "requestor": "user",
                "name": "toggle_roaming",
                "arguments": {},
            },
        ],
    }

    assistant_actions = runner._reference_actions("telecom", "t", criteria)
    all_actions = runner._reference_actions_by_requestor(
        "telecom",
        "t",
        criteria,
        requestor=None,
    )

    assert [action.name for action in assistant_actions] == ["enable_roaming"]
    assert [action.requestor for action in all_actions] == ["assistant", "user"]
    assert all_actions[1].object_name == "tau2.telecom.user.toggle_roaming"


def test_reference_user_simulator_waits_for_preceding_assistant_action():
    assistant_action = ReferenceAction(
        event_id="telecom:t:enable_roaming_0",
        domain="telecom",
        task_id="t",
        action_id="enable_roaming_0",
        index=0,
        name="enable_roaming",
        requestor="assistant",
        args={"customer_id": "C1001", "line_id": "L1002"},
        reward_basis=(),
        object_name="tau2.telecom.assistant.enable_roaming",
    )
    user_action = ReferenceAction(
        event_id="telecom:t:toggle_roaming_1",
        domain="telecom",
        task_id="t",
        action_id="toggle_roaming_1",
        index=1,
        name="toggle_roaming",
        requestor="user",
        args={},
        reward_basis=(),
        object_name="tau2.telecom.user.toggle_roaming",
    )
    env_calls = []

    class FakeToolCall:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeUserMessage:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeEnv:
        def get_response(self, tool_call):
            env_calls.append((tool_call.requestor, tool_call.name))
            return SimpleNamespace(
                content="ok",
                error=False,
                model_dump=lambda: {
                    "content": "ok",
                    "error": False,
                    "id": tool_call.id,
                    "requestor": tool_call.requestor,
                },
            )

    rows = []
    executed_users = []
    trajectory = []

    runner.execute_unlocked_reference_user_actions(
        reference_sequence=[assistant_action, user_action],
        executed_assistant_reference_ids=[],
        executed_user_reference_ids=executed_users,
        env=FakeEnv(),
        trajectory=trajectory,
        tool_call_cls=FakeToolCall,
        user_message_cls=FakeUserMessage,
        user_simulator_rows=rows,
    )

    assert rows == []
    assert env_calls == []

    runner.execute_unlocked_reference_user_actions(
        reference_sequence=[assistant_action, user_action],
        executed_assistant_reference_ids=[assistant_action.event_id],
        executed_user_reference_ids=executed_users,
        env=FakeEnv(),
        trajectory=trajectory,
        tool_call_cls=FakeToolCall,
        user_message_cls=FakeUserMessage,
        user_simulator_rows=rows,
    )

    assert env_calls == [("user", "toggle_roaming")]
    assert executed_users == [user_action.event_id]
    assert rows[0]["tool"] == "toggle_roaming"
    assert len(trajectory) == 2


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
        lease_source="exact-reference",
        compiler_run_dir=None,
        tool_exposure="leased",
        stepwise_max_steps=0,
        stepwise_empty_retries=0,
        dry_run=False,
    )

    assert summary["feedback_rounds"] == 1
    assert summary["lease_source"] == "exact-reference"
    assert summary["tool_exposure"] == "leased"
    assert summary["tool_schema_count_avg"] == 2
    assert summary["active_leases_total"] == 0
    assert summary["feedback_attempted_tasks"] == 1
    assert summary["initial_gateway_blocked"] == 1
    assert summary["feedback_gateway_allowed"] == 1


def test_compiler_corpus_mode_requires_source_and_disables_reference_hints():
    with pytest.raises(ValueError, match="compiler_run_dir is required"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="compiler-corpus",
            dry_run=True,
        )

    with pytest.raises(ValueError, match="disabled for compiler-corpus"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="compiler-corpus",
            compiler_run_dir=Path("results/eval/R074"),
            stepwise_state_grounded_arg_hints=True,
            dry_run=True,
        )

    with pytest.raises(ValueError, match="requires compiler-corpus"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="exact-reference",
            stepwise_compiler_lease_hints=True,
            dry_run=True,
        )

    with pytest.raises(ValueError, match="requires stepwise_compiler_lease_hints"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="compiler-corpus",
            compiler_run_dir=Path("results/eval/R074"),
            stepwise_compiler_lease_fallback=True,
            dry_run=True,
        )

    with pytest.raises(ValueError, match="requires compiler-corpus"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="exact-reference",
            stepwise_runtime_evidence_lease_hints=True,
            dry_run=True,
        )

    with pytest.raises(ValueError, match="requires compiler_runtime_binding"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="compiler-corpus",
            compiler_run_dir=Path("results/eval/R074"),
            stepwise_runtime_evidence_lease_hints=True,
            dry_run=True,
        )

    with pytest.raises(ValueError, match="requires stepwise_runtime_evidence_lease_hints"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="compiler-corpus",
            compiler_run_dir=Path("results/eval/R074"),
            compiler_runtime_binding=True,
            stepwise_runtime_evidence_fallback=True,
            dry_run=True,
        )

    with pytest.raises(ValueError, match="requires stepwise_runtime_evidence_lease_hints"):
        runner.run_experiment(
            benchmark_dir=Path("benchmarks/tau2-bench"),
            output_dir=Path("/tmp/intentcap-test-unused"),
            lease_source="compiler-corpus",
            compiler_run_dir=Path("results/eval/R074"),
            compiler_runtime_binding=True,
            stepwise_runtime_evidence_hint_choice_fallback=True,
            dry_run=True,
        )


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


def test_compiler_lease_arg_hints_come_only_from_active_leases():
    trace = {
        "leases": [
            {
                "id": "lease:create",
                "op": "tool.call",
                "object": "tau2.mock.assistant.create_task",
                "args": {
                    "user_id": {"one_of": ["user_1"]},
                    "title": {"one_of": ["Important"]},
                },
            },
            {
                "id": "lease:update",
                "op": "tool.call",
                "object": "tau2.mock.assistant.update_task",
                "args": {
                    "task_id": {"one_of": ["task_1", "task_2"]},
                    "title": {"equals": "Important"},
                },
            },
        ]
    }

    hints = runner.build_compiler_lease_arg_hints(
        trace=trace,
        action_rows=[
            {
                "model_tool": "create_task",
                "model_args_json": '{"title": "Important", "user_id": "user_1"}',
            }
        ],
    )

    assert hints == [
        {
            "tool": "update_task",
            "arguments": {"title": "Important"},
            "complete_arguments": False,
            "grounding": "active compiler lease strict argument constraints; no reference actions used",
            "lease_id": "lease:update",
            "argument_options": {"task_id": ["task_1", "task_2"]},
        }
    ]


def test_runtime_evidence_compiler_hints_use_templates_and_tool_results_only():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:cancel",
                    "tool": "cancel_reservation",
                    "object": "tau2.airline.assistant.cancel_reservation",
                    "static_args": {},
                    "runtime_args": ["reservation_id"],
                    "allowed_arg_keys": ["reservation_id"],
                }
            ]
        }
    }

    hints = runner.build_runtime_evidence_compiler_hints(
        trace=trace,
        action_rows=[
            {
                "model_tool": "get_user_details",
                "model_args_json": '{"user_id": "u1"}',
                "executed": True,
                "tool_result_preview": (
                    '{"content":"{\\"reservations\\":[\\"Q69X3R\\",\\"MZDDS4\\"]}"}'
                ),
            }
        ],
    )

    assert hints == [
        {
            "tool": "cancel_reservation",
            "arguments": {"reservation_id": "Q69X3R"},
            "complete_arguments": True,
            "grounding": (
                "runtime-bindable compiler template plus executed tool-result "
                "evidence; no reference actions used"
            ),
            "lease_template_id": "template:cancel",
            "runtime_args": ["reservation_id"],
        },
        {
            "tool": "cancel_reservation",
            "arguments": {"reservation_id": "MZDDS4"},
            "complete_arguments": True,
            "grounding": (
                "runtime-bindable compiler template plus executed tool-result "
                "evidence; no reference actions used"
            ),
            "lease_template_id": "template:cancel",
            "runtime_args": ["reservation_id"],
        },
    ]


def test_runtime_evidence_compiler_hints_require_all_runtime_args():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:enable",
                    "tool": "enable_roaming",
                    "object": "tau2.telecom.assistant.enable_roaming",
                    "static_args": {},
                    "runtime_args": ["customer_id", "line_id"],
                    "allowed_arg_keys": ["customer_id", "line_id"],
                }
            ]
        }
    }

    assert runner.build_runtime_evidence_compiler_hints(
        trace=trace,
        action_rows=[
            {
                "executed": True,
                "tool_result_preview": '{"content":"{\\"customer_id\\":\\"C1001\\"}"}',
            }
        ],
    ) == []

    hints = runner.build_runtime_evidence_compiler_hints(
        trace=trace,
        action_rows=[
            {
                "executed": True,
                "tool_result_preview": (
                    '{"content":"{\\"customer_id\\":\\"C1001\\",\\"line_id\\":\\"L1002\\"}"}'
                ),
            }
        ],
    )

    assert hints[0]["arguments"] == {"customer_id": "C1001", "line_id": "L1002"}


def test_runtime_evidence_ranked_hints_prefer_intent_matching_value_context():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:cancel",
                    "tool": "cancel_reservation",
                    "object": "tau2.airline.assistant.cancel_reservation",
                    "static_args": {},
                    "runtime_args": ["reservation_id"],
                    "allowed_arg_keys": ["reservation_id"],
                    "intent_evidence": (
                        "User wants to cancel reservation from Philadelphia to LaGuardia"
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    action_rows = [
        {
            "executed": True,
            "tool_result_preview": (
                '{"content":"{\\"reservation_id\\":\\"Q69X3R\\",'
                '\\"origin\\":\\"JFK\\",\\"destination\\":\\"BOS\\"}"}'
            ),
        },
        {
            "executed": True,
            "tool_result_preview": (
                '{"content":"{\\"reservation_id\\":\\"MZDDS4\\",'
                '\\"origin\\":\\"PHL\\",\\"destination\\":\\"LGA\\"}"}'
            ),
        },
    ]

    hints = runner.build_runtime_evidence_compiler_hints(
        trace=trace,
        action_rows=action_rows,
        rank_hints=True,
    )

    assert [hint["arguments"]["reservation_id"] for hint in hints] == [
        "MZDDS4",
        "Q69X3R",
    ]
    assert hints[0]["rank_score"] > hints[1]["rank_score"]
    assert "intent_tokens:philadelphia|laguardia" in hints[0]["rank_reasons"]


def test_runtime_value_proof_blocks_write_from_undifferentiated_id_list():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:cancel",
                    "tool": "cancel_reservation",
                    "object": "tau2.airline.assistant.cancel_reservation",
                    "static_args": {},
                    "runtime_args": ["reservation_id"],
                    "allowed_arg_keys": ["reservation_id"],
                    "intent_evidence": (
                        "User wants to cancel reservation from Philadelphia to LaGuardia"
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    action_rows = [
        {
            "executed": True,
            "tool_result_preview": (
                '{"content":"{\\"reservations\\":[\\"Q69X3R\\",\\"MZDDS4\\"]}"}'
            ),
        }
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.airline.assistant.cancel_reservation",
            "args": {"reservation_id": "Q69X3R"},
        },
        domain="airline",
        task_id="1",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["lease"] is None
    assert binding["reason"].startswith("missing runtime value proof for template:cancel")


def test_runtime_value_proof_allows_write_after_matching_detail_probe():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:cancel",
                    "tool": "cancel_reservation",
                    "object": "tau2.airline.assistant.cancel_reservation",
                    "static_args": {},
                    "runtime_args": ["reservation_id"],
                    "allowed_arg_keys": ["reservation_id"],
                    "intent_evidence": (
                        "User wants to cancel reservation from Philadelphia to LaGuardia"
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    action_rows = [
        {
            "executed": True,
            "tool_result_preview": (
                '{"content":"{\\"reservation_id\\":\\"Q69X3R\\",'
                '\\"origin\\":\\"PHL\\",\\"destination\\":\\"LGA\\"}"}'
            ),
        }
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.airline.assistant.cancel_reservation",
            "args": {"reservation_id": "Q69X3R"},
        },
        domain="airline",
        task_id="1",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["reason"] == "runtime evidence value-proof bound"
    assert binding["lease"]["args"] == {"reservation_id": {"equals": "Q69X3R"}}


def test_runtime_value_proof_allows_retail_item_list_with_structured_option_context():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:modify-items",
                    "tool": "modify_pending_order_items",
                    "object": "tau2.retail.assistant.modify_pending_order_items",
                    "static_args": {},
                    "runtime_args": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "allowed_arg_keys": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "intent_evidence": (
                        "User wants to modify pending small tshirt items to "
                        "purple, polyester, v-neck."
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    order = {
        "order_id": "#W4776164",
        "items": [
            {
                "name": "T-Shirt",
                "item_id": "8349118980",
                "options": {
                    "color": "blue",
                    "size": "S",
                    "material": "cotton",
                    "style": "v-neck",
                },
            }
        ],
        "payment_history": [{"payment_method_id": "credit_card_9513926"}],
    }
    product = {
        "name": "T-Shirt",
        "variants": {
            "9647292434": {
                "name": "T-Shirt",
                "item_id": "9647292434",
                "options": {
                    "color": "purple",
                    "size": "S",
                    "material": "polyester",
                    "style": "v-neck",
                },
                "available": True,
            }
        },
    }
    action_rows = [
        {"executed": True, "tool_result_preview": json.dumps({"content": json.dumps(order)})},
        {"executed": True, "tool_result_preview": json.dumps({"content": json.dumps(product)})},
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.retail.assistant.modify_pending_order_items",
            "args": {
                "item_ids": ["8349118980"],
                "new_item_ids": ["9647292434"],
                "order_id": "#W4776164",
                "payment_method_id": "credit_card_9513926",
            },
        },
        domain="retail",
        task_id="3",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["reason"] == "runtime evidence value-proof bound"
    assert binding["lease"]["args"] == {
        "item_ids": {"equals": ["8349118980"]},
        "new_item_ids": {"equals": ["9647292434"]},
        "order_id": {"equals": "#W4776164"},
        "payment_method_id": {"equals": "credit_card_9513926"},
    }


def test_runtime_value_proof_uses_full_evidence_when_prompt_preview_is_truncated():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:modify-items",
                    "tool": "modify_pending_order_items",
                    "object": "tau2.retail.assistant.modify_pending_order_items",
                    "static_args": {},
                    "runtime_args": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "allowed_arg_keys": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "intent_evidence": (
                        "User wants to modify pending small tshirt items to "
                        "purple, polyester, v-neck."
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    order = {
        "order_id": "#W4776164",
        "items": [
            {
                "name": "T-Shirt",
                "item_id": "8349118980",
                "options": {
                    "color": "blue",
                    "size": "S",
                    "material": "cotton",
                    "style": "v-neck",
                },
            }
        ],
        "payment_history": [{"payment_method_id": "credit_card_9513926"}],
    }
    product = {
        "name": "T-Shirt",
        "variants": {
            "9647292434": {
                "item_id": "9647292434",
                "options": {
                    "color": "purple",
                    "size": "S",
                    "material": "polyester",
                    "style": "v-neck",
                },
                "available": True,
            },
            **{
                f"dummy_{index}": {
                    "item_id": f"dummy_{index}",
                    "options": {"color": "black", "size": "XL"},
                }
                for index in range(200)
            },
        },
    }
    product_message = {"content": json.dumps(product)}
    truncated_preview = runner._preview_json(product_message, limit=1600)
    assert truncated_preview.endswith("...")
    assert "9647292434" in truncated_preview

    action_rows = [
        {
            "executed": True,
            "tool_result_preview": runner._preview_json({"content": json.dumps(order)}, limit=1600),
        },
        {
            "executed": True,
            "tool_result_preview": truncated_preview,
            "tool_result_evidence": runner._evidence_json(product_message),
        },
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.retail.assistant.modify_pending_order_items",
            "args": {
                "item_ids": ["8349118980"],
                "new_item_ids": ["9647292434"],
                "order_id": "#W4776164",
                "payment_method_id": "credit_card_9513926",
            },
        },
        domain="retail",
        task_id="3",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["reason"] == "runtime evidence value-proof bound"


def test_runtime_value_proof_blocks_retail_item_list_without_new_option_context():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:modify-items",
                    "tool": "modify_pending_order_items",
                    "object": "tau2.retail.assistant.modify_pending_order_items",
                    "static_args": {},
                    "runtime_args": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "allowed_arg_keys": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "intent_evidence": (
                        "User wants to modify pending small tshirt items to "
                        "purple, polyester, v-neck."
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    action_rows = [
        {
            "executed": True,
            "tool_result_preview": (
                '{"content":"{\\"order_id\\":\\"#W4776164\\",'
                '\\"items\\":[{\\"name\\":\\"T-Shirt\\",'
                '\\"item_id\\":\\"8349118980\\",'
                '\\"options\\":{\\"color\\":\\"blue\\",\\"size\\":\\"S\\",'
                '\\"material\\":\\"cotton\\",\\"style\\":\\"v-neck\\"}}],'
                '\\"payment_history\\":[{\\"payment_method_id\\":'
                '\\"credit_card_9513926\\"}],'
                '\\"candidate_items\\":[\\"9647292434\\"]}"}'
            ),
        }
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.retail.assistant.modify_pending_order_items",
            "args": {
                "item_ids": ["8349118980"],
                "new_item_ids": ["9647292434"],
                "order_id": "#W4776164",
                "payment_method_id": "credit_card_9513926",
            },
        },
        domain="retail",
        task_id="3",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["lease"] is None
    assert binding["reason"].startswith(
        "missing runtime value proof for template:modify-items"
    )


def test_runtime_value_proof_blocks_unproven_leaf_in_multi_item_list():
    good_item_id = "9647292434"
    bad_item_id = "5555555555"
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:modify-items",
                    "tool": "modify_pending_order_items",
                    "object": "tau2.retail.assistant.modify_pending_order_items",
                    "static_args": {},
                    "runtime_args": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "allowed_arg_keys": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "intent_evidence": (
                        "User wants to modify pending small tshirt items to "
                        "purple, polyester, v-neck."
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    order = {
        "order_id": "#W4776164",
        "items": [
            {
                "name": "T-Shirt",
                "item_id": "8349118980",
                "options": {
                    "color": "blue",
                    "size": "S",
                    "material": "cotton",
                    "style": "v-neck",
                },
            }
        ],
        "payment_history": [{"payment_method_id": "credit_card_9513926"}],
    }
    product = {
        "name": "T-Shirt",
        "variants": {
            good_item_id: {
                "name": "T-Shirt",
                "item_id": good_item_id,
                "options": {
                    "color": "purple",
                    "size": "S",
                    "material": "polyester",
                    "style": "v-neck",
                },
            },
            bad_item_id: {
                "name": "T-Shirt",
                "item_id": bad_item_id,
                "options": {
                    "color": "red",
                    "size": "L",
                    "material": "wool",
                    "style": "crew",
                },
            },
        },
    }
    action_rows = [
        {"executed": True, "tool_result_preview": json.dumps({"content": json.dumps(order)})},
        {"executed": True, "tool_result_preview": json.dumps({"content": json.dumps(product)})},
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.retail.assistant.modify_pending_order_items",
            "args": {
                "item_ids": ["8349118980"],
                "new_item_ids": [good_item_id, bad_item_id],
                "order_id": "#W4776164",
                "payment_method_id": "credit_card_9513926",
            },
        },
        domain="retail",
        task_id="3",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["lease"] is None
    assert binding["reason"].startswith(
        "missing runtime value proof for template:modify-items"
    )


def test_runtime_value_proof_blocks_scalar_list_sibling_proof_pollution():
    bad_item_id = "5555555555"
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:modify-items",
                    "tool": "modify_pending_order_items",
                    "object": "tau2.retail.assistant.modify_pending_order_items",
                    "static_args": {},
                    "runtime_args": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "allowed_arg_keys": [
                        "item_ids",
                        "new_item_ids",
                        "order_id",
                        "payment_method_id",
                    ],
                    "intent_evidence": (
                        "User wants to modify pending small tshirt items to "
                        "purple, polyester, v-neck."
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                }
            ]
        }
    }
    order = {
        "order_id": "#W4776164",
        "items": [
            {
                "name": "T-Shirt",
                "item_id": "8349118980",
                "options": {
                    "color": "blue",
                    "size": "S",
                    "material": "cotton",
                    "style": "v-neck",
                },
            }
        ],
        "payment_history": [{"payment_method_id": "credit_card_9513926"}],
        "candidate_items": [
            bad_item_id,
            "T-Shirt",
            "small",
            "purple",
            "polyester",
            "v-neck",
        ],
    }
    action_rows = [
        {"executed": True, "tool_result_preview": json.dumps({"content": json.dumps(order)})}
    ]

    binding = runner.build_runtime_bound_compiler_lease(
        trace=trace,
        event={
            "object": "tau2.retail.assistant.modify_pending_order_items",
            "args": {
                "item_ids": ["8349118980"],
                "new_item_ids": [bad_item_id],
                "order_id": "#W4776164",
                "payment_method_id": "credit_card_9513926",
            },
        },
        domain="retail",
        task_id="3",
        index=0,
        action_rows=action_rows,
        require_value_proof=True,
    )

    assert binding["attempted"] is True
    assert binding["lease"] is None
    assert binding["reason"].startswith(
        "missing runtime value proof for template:modify-items"
    )


def test_runtime_value_proof_allows_return_item_grouped_list_context():
    template = {
        "id": "template:return-items",
        "tool": "return_delivered_order_items",
        "object": "tau2.retail.assistant.return_delivered_order_items",
        "static_args": {},
        "runtime_args": ["item_ids", "order_id", "payment_method_id"],
        "allowed_arg_keys": ["item_ids", "order_id", "payment_method_id"],
        "intent_evidence": "return the cleaner, headphone, and smart watch",
        "tool_type": "write",
        "proof_required": True,
    }
    order = {
        "order_id": "#O",
        "items": [
            {"name": "Vacuum Cleaner", "item_id": "cleaner_item"},
            {"name": "Headphones", "item_id": "headphone_item"},
            {"name": "Smart Watch", "item_id": "watch_item"},
        ],
        "payment_history": [{"payment_method_id": "card"}],
    }

    proof = runner.runtime_value_proof_status(
        template=template,
        args={
            "item_ids": ["cleaner_item", "headphone_item", "watch_item"],
            "order_id": "#O",
            "payment_method_id": "card",
        },
        action_rows=[
            {
                "executed": True,
                "tool_result_evidence": json.dumps({"content": json.dumps(order)}),
            }
        ],
        require_value_proof=True,
    )

    assert proof["complete"] is True
    assert proof["grouped_semantic_args"] == ["item_ids"]


def test_runtime_value_proof_blocks_unmatched_leaf_in_grouped_return_list():
    template = {
        "id": "template:return-items",
        "tool": "return_delivered_order_items",
        "object": "tau2.retail.assistant.return_delivered_order_items",
        "static_args": {},
        "runtime_args": ["item_ids", "order_id", "payment_method_id"],
        "allowed_arg_keys": ["item_ids", "order_id", "payment_method_id"],
        "intent_evidence": "return the cleaner, headphone, and smart watch",
        "tool_type": "write",
        "proof_required": True,
    }
    order = {
        "order_id": "#O",
        "items": [
            {"name": "Vacuum Cleaner", "item_id": "cleaner_item"},
            {"name": "Headphones", "item_id": "headphone_item"},
            {"name": "Smart Watch", "item_id": "watch_item"},
            {"name": "Desk Lamp", "item_id": "lamp_item"},
        ],
        "payment_history": [{"payment_method_id": "card"}],
    }

    proof = runner.runtime_value_proof_status(
        template=template,
        args={
            "item_ids": ["cleaner_item", "headphone_item", "watch_item", "lamp_item"],
            "order_id": "#O",
            "payment_method_id": "card",
        },
        action_rows=[
            {
                "executed": True,
                "tool_result_evidence": json.dumps({"content": json.dumps(order)}),
            }
        ],
        require_value_proof=True,
    )

    assert proof["complete"] is False
    assert proof["grouped_semantic_args"] == []
    assert any("lamp_item" in value for value in proof["missing_args"]["item_ids"])


def test_runtime_value_proof_hints_suppress_write_and_emit_read_probe():
    trace = {
        "metadata": {
            "runtime_bindable_compiler_leases": [
                {
                    "id": "template:cancel",
                    "tool": "cancel_reservation",
                    "object": "tau2.airline.assistant.cancel_reservation",
                    "static_args": {},
                    "runtime_args": ["reservation_id"],
                    "allowed_arg_keys": ["reservation_id"],
                    "intent_evidence": (
                        "User wants to cancel reservation from Philadelphia to LaGuardia"
                    ),
                    "tool_type": "write",
                    "proof_required": True,
                },
                {
                    "id": "template:cancel:proof-probe:get_reservation_details:reservation_id",
                    "tool": "get_reservation_details",
                    "object": "tau2.airline.assistant.get_reservation_details",
                    "static_args": {},
                    "runtime_args": ["reservation_id"],
                    "allowed_arg_keys": ["reservation_id"],
                    "intent_evidence": (
                        "Gather details to prove runtime value satisfies: User wants "
                        "to cancel reservation from Philadelphia to LaGuardia"
                    ),
                    "tool_type": "read",
                    "proof_probe": True,
                    "proof_probe_for_template_id": "template:cancel",
                    "proof_required": False,
                },
            ]
        }
    }

    hints = runner.build_runtime_evidence_compiler_hints(
        trace=trace,
        action_rows=[
            {
                "model_tool": "get_user_details",
                "model_args_json": '{"user_id": "u1"}',
                "executed": True,
                "tool_result_preview": (
                    '{"content":"{\\"reservations\\":[\\"Q69X3R\\",\\"MZDDS4\\"]}"}'
                ),
            }
        ],
        require_value_proof=True,
    )

    assert {hint["tool"] for hint in hints} == {"get_reservation_details"}
    assert [hint["arguments"] for hint in hints] == [
        {"reservation_id": "Q69X3R"},
        {"reservation_id": "MZDDS4"},
    ]
    assert all(hint["proof_probe"] is True for hint in hints)
    assert all(hint["value_proof"]["required"] is False for hint in hints)


def test_compiler_corpus_task_trace_derives_read_proof_probe():
    compiler_record = {
        "parsed_model_json": {
            "leases": [
                {
                    "tool": "cancel_reservation",
                    "argument_policy": {
                        "reservation_id": {
                            "mode": "runtime_from_prior_tool",
                            "values": [],
                        }
                    },
                    "intent_evidence": (
                        "User wants to cancel reservation from Philadelphia to LaGuardia"
                    ),
                }
            ]
        },
        "task_row": {"parse_ok": True},
    }
    tools_by_name = {
        "cancel_reservation": SimpleNamespace(
            name="cancel_reservation",
            arguments=("reservation_id",),
            tool_type="write",
        ),
        "get_reservation_details": SimpleNamespace(
            name="get_reservation_details",
            arguments=("reservation_id",),
            tool_type="read",
        ),
    }

    trace, active_tools, active_objects = runner.build_compiler_corpus_task_trace(
        domain="airline",
        task_id="1",
        compiler_record=compiler_record,
        tools_by_name=tools_by_name,
        expose_runtime_bindable=True,
        runtime_proof_probes=True,
    )

    templates = trace["metadata"]["runtime_bindable_compiler_leases"]
    assert trace["metadata"]["runtime_proof_probe_template_count"] == 1
    assert any(template.get("proof_probe") is True for template in templates)
    assert "cancel_reservation" in active_tools
    assert "get_reservation_details" in active_tools
    assert "tau2.airline.assistant.get_reservation_details" in active_objects


def test_runtime_evidence_fallback_uses_distinct_marker():
    hint = {
        "tool": "cancel_reservation",
        "arguments": {"reservation_id": "Q69X3R"},
        "complete_arguments": True,
    }

    call = runner.build_single_hint_fallback_call_with_marker(
        [hint],
        marker={"_intentcap_synthesized_from_runtime_evidence_hint": True},
    )

    assert call == {
        "tool": "cancel_reservation",
        "arguments": {
            "reservation_id": "Q69X3R",
            "_intentcap_synthesized_from_runtime_evidence_hint": True,
        },
    }


def test_ranked_runtime_evidence_fallback_selects_highest_scored_hint():
    hints = [
        {
            "tool": "get_order_details",
            "arguments": {"order_id": "#W2378156"},
            "complete_arguments": True,
            "rank_score": 52,
        },
        {
            "tool": "get_product_details",
            "arguments": {"product_id": "9523456873"},
            "complete_arguments": True,
            "rank_score": 62,
        },
    ]

    call = runner.build_ranked_runtime_evidence_fallback_call(
        hints,
        min_score=50,
        margin=10,
    )

    assert call == {
        "tool": "get_product_details",
        "arguments": {
            "product_id": "9523456873",
            "_intentcap_synthesized_from_ranked_runtime_evidence_hint": True,
            "_intentcap_ranked_runtime_evidence_score": 62,
            "_intentcap_ranked_runtime_evidence_margin": 10,
        },
    }


def test_ranked_runtime_evidence_fallback_respects_score_and_margin():
    low_score = {
        "tool": "get_order_details",
        "arguments": {"order_id": "#W2378156"},
        "complete_arguments": True,
        "rank_score": 37,
    }
    top = {
        "tool": "get_product_details",
        "arguments": {"product_id": "9523456873"},
        "complete_arguments": True,
        "rank_score": 62,
    }
    tied = {
        "tool": "get_item_details",
        "arguments": {"item_id": "3799046073"},
        "complete_arguments": True,
        "rank_score": 62,
    }

    assert (
        runner.build_ranked_runtime_evidence_fallback_call(
            [low_score],
            min_score=50,
            margin=1,
        )
        is None
    )
    assert (
        runner.build_ranked_runtime_evidence_fallback_call(
            [top, tied],
            min_score=50,
            margin=1,
        )
        is None
    )

    call = runner.build_ranked_runtime_evidence_fallback_call(
        [top, tied],
        min_score=50,
        margin=0,
    )

    assert call is not None
    assert call["arguments"]["_intentcap_ranked_runtime_evidence_margin"] == 0


def test_compiler_lease_fallback_uses_complete_active_hint_marker():
    hint = {
        "tool": "create_task",
        "arguments": {"user_id": "user_1", "title": "Important"},
        "complete_arguments": True,
    }

    call = runner.build_single_hint_fallback_call_with_marker(
        [hint],
        marker={"_intentcap_synthesized_from_compiler_lease_hint": True},
    )

    assert call == {
        "tool": "create_task",
        "arguments": {
            "user_id": "user_1",
            "title": "Important",
            "_intentcap_synthesized_from_compiler_lease_hint": True,
        },
    }


def test_load_repair_map_candidates_filters_ready_rows(tmp_path):
    repair_csv = tmp_path / "repair.csv"
    fieldnames = [
        "domain",
        "task_id",
        "event_id",
        "tool",
        "args_json",
        "eligible",
        "proof_status",
        "repair_class",
        "candidate_source",
        "earliest_synthesis_step",
        "candidate_json",
    ]
    with repair_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "domain": "retail",
                "task_id": "0",
                "event_id": "retail:0:0_2",
                "tool": "get_product_details",
                "args_json": "{}",
                "eligible": "True",
                "proof_status": "repair_candidate_ready",
                "repair_class": "visible_tool_argument_candidate_generation",
                "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
                "earliest_synthesis_step": "4",
                "candidate_json": json.dumps(
                    {
                        "tool": "get_product_details",
                        "arguments": {"product_id": "1656367028"},
                    }
                ),
            }
        )
        writer.writerow(
            {
                "domain": "retail",
                "task_id": "0",
                "event_id": "bad",
                "tool": "get_product_details",
                "args_json": "{}",
                "eligible": "False",
                "proof_status": "repair_candidate_ready",
                "repair_class": "visible_tool_argument_candidate_generation",
                "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
                "earliest_synthesis_step": "4",
                "candidate_json": json.dumps(
                    {
                        "tool": "get_product_details",
                        "arguments": {"product_id": "4896585277"},
                    }
                ),
            }
        )

    loaded = runner.load_repair_map_candidates(repair_csv)

    assert list(loaded) == [("retail", "0")]
    assert loaded[("retail", "0")] == [
        {
            "domain": "retail",
            "task_id": "0",
            "event_id": "retail:0:0_2",
            "tool": "get_product_details",
            "arguments": {"product_id": "1656367028"},
            "repair_class": "visible_tool_argument_candidate_generation",
            "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
            "earliest_synthesis_step": 4,
        }
    ]


def test_load_read_tool_activation_candidates_filters_to_eligible_reads(tmp_path):
    activation_csv = tmp_path / "activation.csv"
    fieldnames = [
        "domain",
        "task_id",
        "event_id",
        "tool",
        "args_json",
        "tool_type",
        "activation_eligible",
        "activation_kind",
        "proof_status",
        "earliest_arg_visible_step",
        "candidate_json",
    ]
    with activation_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "domain": "airline",
                "task_id": "3",
                "event_id": "airline:3:3_1",
                "tool": "get_user_details",
                "args_json": "{}",
                "tool_type": "read",
                "activation_eligible": "True",
                "activation_kind": "read_only_tool_activation_from_visible_argument",
                "proof_status": "activation_candidate_ready",
                "earliest_arg_visible_step": "1",
                "candidate_json": json.dumps(
                    {
                        "tool": "get_user_details",
                        "arguments": {"user_id": "anya_garcia_5901"},
                    }
                ),
            }
        )
        writer.writerow(
            {
                "domain": "retail",
                "task_id": "2",
                "event_id": "retail:2:2_11",
                "tool": "return_delivered_order_items",
                "args_json": "{}",
                "tool_type": "write",
                "activation_eligible": "True",
                "activation_kind": "write_or_high_impact_tool_activation_requires_value_proof",
                "proof_status": "activation_candidate_ready",
                "earliest_arg_visible_step": "1",
                "candidate_json": json.dumps(
                    {
                        "tool": "return_delivered_order_items",
                        "arguments": {"order_id": "#W2378156"},
                    }
                ),
            }
        )

    loaded = runner.load_read_tool_activation_candidates(activation_csv)

    assert list(loaded) == [("airline", "3")]
    assert loaded[("airline", "3")] == [
        {
            "domain": "airline",
            "task_id": "3",
            "event_id": "airline:3:3_1",
            "tool": "get_user_details",
            "arguments": {"user_id": "anya_garcia_5901"},
            "activation_kind": "read_only_tool_activation_from_visible_argument",
            "proof_status": "activation_candidate_ready",
            "tool_type": "read",
            "intent_evidence": "",
            "earliest_activation_step": 1,
        }
    ]


def test_load_write_tool_activation_candidates_filters_to_proof_complete(tmp_path):
    activation_csv = tmp_path / "write_activation.csv"
    fieldnames = [
        "domain",
        "task_id",
        "event_id",
        "tool",
        "args_json",
        "tool_type",
        "proof_gap_class",
        "write_activation_candidate_ready",
        "intent_evidence",
    ]
    rows = [
        {
            "domain": "retail",
            "task_id": "2",
            "event_id": "retail:2:2_11",
            "tool": "return_delivered_order_items",
            "tool_type": "write",
            "proof_gap_class": "write_activation_value_proof_complete",
            "write_activation_candidate_ready": "True",
            "intent_evidence": "return the cleaner, headphone, and smart watch",
            "args_json": json.dumps(
                {
                    "item_ids": ["cleaner_item", "headphone_item", "watch_item"],
                    "order_id": "#O",
                    "payment_method_id": "card",
                }
            ),
        },
        {
            "domain": "retail",
            "task_id": "2",
            "event_id": "retail:2:blocked",
            "tool": "return_delivered_order_items",
            "tool_type": "write",
            "proof_gap_class": "write_activation_missing_value_proof",
            "write_activation_candidate_ready": "False",
            "intent_evidence": "return the lamp",
            "args_json": json.dumps({"item_ids": ["lamp_item"]}),
        },
    ]
    with activation_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    loaded = runner.load_write_tool_activation_candidates(activation_csv)

    assert loaded == {
        ("retail", "2"): [
            {
                "domain": "retail",
                "task_id": "2",
                "event_id": "retail:2:2_11",
                "tool": "return_delivered_order_items",
                "arguments": {
                    "item_ids": ["cleaner_item", "headphone_item", "watch_item"],
                    "order_id": "#O",
                    "payment_method_id": "card",
                },
                "activation_kind": (
                    "write_or_high_impact_tool_activation_value_proof_complete"
                ),
                "proof_status": "write_activation_value_proof_complete",
                "tool_type": "write",
                "intent_evidence": "return the cleaner, headphone, and smart watch",
                "earliest_activation_step": 1,
            }
        ]
    }


def test_repair_map_fallback_requires_step_pending_and_visible_values():
    candidate = {
        "domain": "retail",
        "task_id": "0",
        "event_id": "retail:0:0_2",
        "tool": "get_product_details",
        "arguments": {"product_id": "1656367028"},
        "repair_class": "visible_tool_argument_candidate_generation",
        "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
        "earliest_synthesis_step": 4,
    }
    pending = [
        runner.ReferenceAction(
            event_id="retail:0:0_2",
            domain="retail",
            task_id="0",
            action_id="0_2",
            index=2,
            name="get_product_details",
            requestor="assistant",
            args={"product_id": "1656367028"},
            reward_basis=("ACTION",),
            object_name="tau2.retail.assistant.get_product_details",
        )
    ]
    raw_task = {"id": "0", "instruction": "Handle the visible order."}
    visible_rows = [
        {
            "model_tool": "get_order_details",
            "model_args_json": '{"order_id": "#W2378156"}',
            "executed": True,
            "tool_result_preview": '{"product_id":"1656367028"}',
        }
    ]

    assert (
        runner.repair_map_candidates_for_step(
            repair_map_candidates=[candidate],
            step_index=3,
            raw_task=raw_task,
            action_rows=visible_rows,
            pending_reference_actions=pending,
        )
        == []
    )
    assert (
        runner.repair_map_candidates_for_step(
            repair_map_candidates=[candidate],
            step_index=4,
            raw_task=raw_task,
            action_rows=[],
            pending_reference_actions=pending,
        )
        == []
    )
    assert runner.repair_map_candidates_for_step(
        repair_map_candidates=[candidate],
        step_index=4,
        raw_task=raw_task,
        action_rows=visible_rows,
        pending_reference_actions=pending,
    ) == [candidate]

    call = runner.build_repair_map_fallback_call(
        repair_map_candidates=[candidate],
        domain="retail",
        task_id="0",
        step_index=4,
        raw_task=raw_task,
        action_rows=visible_rows,
        pending_reference_actions=pending,
    )

    assert call == {
        "tool": "get_product_details",
        "arguments": {
            "product_id": "1656367028",
            "_intentcap_synthesized_from_repair_map": True,
            "_intentcap_repair_map_event_id": "retail:0:0_2",
            "_intentcap_repair_map_class": "visible_tool_argument_candidate_generation",
            "_intentcap_repair_map_source": "posthoc_reference_args_verified_visible_in_prompt",
        },
    }

    attempted_rows = [
        *visible_rows,
        {
            "model_tool": "get_product_details",
            "model_args_json": '{"product_id": "1656367028"}',
            "executed": False,
            "tool_result_preview": "",
        },
    ]
    assert (
        runner.build_repair_map_fallback_call(
            repair_map_candidates=[candidate],
            domain="retail",
            task_id="0",
            step_index=4,
            raw_task=raw_task,
            action_rows=attempted_rows,
            pending_reference_actions=pending,
        )
        is None
    )


def test_read_tool_activation_priority_requires_pending_visible_value():
    candidate = {
        "domain": "airline",
        "task_id": "3",
        "event_id": "airline:3:3_1",
        "tool": "get_user_details",
        "arguments": {"user_id": "anya_garcia_5901"},
        "activation_kind": "read_only_tool_activation_from_visible_argument",
        "proof_status": "activation_candidate_ready",
        "earliest_activation_step": 1,
    }
    pending = [
        runner.ReferenceAction(
            event_id="airline:3:3_1",
            domain="airline",
            task_id="3",
            action_id="3_1",
            index=1,
            name="get_user_details",
            requestor="assistant",
            args={"user_id": "anya_garcia_5901"},
            reward_basis=("ACTION",),
            object_name="tau2.airline.assistant.get_user_details",
        )
    ]

    assert (
        runner.build_tool_activation_priority_call(
            tool_activation_candidates=[candidate],
            domain="airline",
            task_id="3",
            step_index=1,
            raw_task={"id": "3", "instruction": "Find Anya's profile."},
            action_rows=[],
            pending_reference_actions=pending,
        )
        is None
    )

    call = runner.build_tool_activation_priority_call(
        tool_activation_candidates=[candidate],
        domain="airline",
        task_id="3",
        step_index=1,
        raw_task={"id": "3", "instruction": "Find anya_garcia_5901 profile."},
        action_rows=[],
        pending_reference_actions=pending,
    )

    assert call == {
        "tool": "get_user_details",
        "arguments": {
            "user_id": "anya_garcia_5901",
            "_intentcap_synthesized_from_tool_activation": True,
            "_intentcap_tool_activation_event_id": "airline:3:3_1",
            "_intentcap_tool_activation_kind": "read_only_tool_activation_from_visible_argument",
            "_intentcap_tool_activation_source": "saved_visible_read_activation_candidate",
        },
    }


def test_read_tool_activation_binder_mints_one_shot_exact_lease():
    candidate = {
        "domain": "airline",
        "task_id": "3",
        "event_id": "airline:3:3_1",
        "tool": "get_user_details",
        "arguments": {"user_id": "anya_garcia_5901"},
        "activation_kind": "read_only_tool_activation_from_visible_argument",
        "proof_status": "activation_candidate_ready",
        "earliest_activation_step": 1,
    }
    trace, active_tools, active_objects = runner.build_compiler_corpus_task_trace(
        domain="airline",
        task_id="3",
        compiler_record={"repaired_model_json": {"leases": []}},
        tools_by_name={},
    )
    activation_objects = runner.attach_read_tool_activation_templates(
        trace=trace,
        domain="airline",
        task_id="3",
        candidates=[candidate],
    )
    active_objects.update(activation_objects)
    gateway = LiveToolGateway(
        trace,
        {
            "tau2.airline.assistant.get_user_details": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )
    event = {
        "id": "airline:3:3_1",
        "op": "tool.call",
        "object": "tau2.airline.assistant.get_user_details",
        "args": {"user_id": "anya_garcia_5901"},
        "decision": "airline.get_user_details.tool_choice",
        "mode": "tool_select",
        "control_provenance": [runner.TRUSTED_TASK_INTENT],
        "data_provenance": [runner.TRUSTED_TASK_INTENT],
        "intentcap_markers": {
            "_intentcap_synthesized_from_tool_activation": True,
            "_intentcap_tool_activation_event_id": "airline:3:3_1",
        },
    }

    record, runtime_binding, activation_binding = (
        runner.call_gateway_with_optional_runtime_binding(
            gateway=gateway,
            event=event,
            domain="airline",
            task_id="3",
            index=1,
            raw_task={
                "id": "3",
                "instruction": "Look up anya_garcia_5901 before continuing.",
            },
            action_rows=[],
            enabled=False,
        )
    )

    assert active_tools == set()
    assert active_objects == {"tau2.airline.assistant.get_user_details"}
    assert record["executed"] is True
    assert runtime_binding["attempted"] is False
    assert activation_binding["attempted"] is True
    assert activation_binding["allowed"] is True
    assert activation_binding["args"] == {"user_id": "anya_garcia_5901"}
    assert activation_binding["lease_id"].startswith("tool-activation-live:airline:3:1")
    assert len(trace["leases"]) == 1


def test_write_tool_activation_binder_mints_one_shot_exact_lease():
    candidate = {
        "domain": "retail",
        "task_id": "2",
        "event_id": "retail:2:2_11",
        "tool": "return_delivered_order_items",
        "arguments": {
            "item_ids": ["cleaner_item", "headphone_item", "watch_item"],
            "order_id": "#O",
            "payment_method_id": "card",
        },
        "activation_kind": "write_or_high_impact_tool_activation_value_proof_complete",
        "proof_status": "write_activation_value_proof_complete",
        "tool_type": "write",
        "intent_evidence": "return the cleaner, headphone, and smart watch",
        "earliest_activation_step": 1,
    }
    order = {
        "order_id": "#O",
        "items": [
            {"name": "Vacuum Cleaner", "item_id": "cleaner_item"},
            {"name": "Headphones", "item_id": "headphone_item"},
            {"name": "Smart Watch", "item_id": "watch_item"},
        ],
        "payment_history": [{"payment_method_id": "card"}],
    }
    trace, active_tools, active_objects = runner.build_compiler_corpus_task_trace(
        domain="retail",
        task_id="2",
        compiler_record={"repaired_model_json": {"leases": []}},
        tools_by_name={},
    )
    activation_objects = runner.attach_read_tool_activation_templates(
        trace=trace,
        domain="retail",
        task_id="2",
        candidates=[candidate],
    )
    active_objects.update(activation_objects)
    gateway = LiveToolGateway(
        trace,
        {
            "tau2.retail.assistant.return_delivered_order_items": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )
    event = {
        "id": "retail:2:2_11",
        "op": "tool.call",
        "object": "tau2.retail.assistant.return_delivered_order_items",
        "args": candidate["arguments"],
        "decision": "retail.return_delivered_order_items.tool_choice",
        "mode": "tool_select",
        "control_provenance": [runner.TRUSTED_TASK_INTENT],
        "data_provenance": [runner.TRUSTED_TASK_INTENT],
        "intentcap_markers": {
            "_intentcap_synthesized_from_tool_activation": True,
            "_intentcap_tool_activation_event_id": "retail:2:2_11",
        },
    }

    record, runtime_binding, activation_binding = (
        runner.call_gateway_with_optional_runtime_binding(
            gateway=gateway,
            event=event,
            domain="retail",
            task_id="2",
            index=11,
            raw_task={"id": "2", "instruction": "Return selected delivered items."},
            action_rows=[
                {
                    "executed": True,
                    "tool_result_preview": json.dumps(order),
                    "tool_result_evidence": json.dumps(
                        {"content": json.dumps(order)}
                    ),
                }
            ],
            enabled=False,
        )
    )

    assert active_tools == set()
    assert active_objects == {"tau2.retail.assistant.return_delivered_order_items"}
    assert record["executed"] is True
    assert runtime_binding["attempted"] is False
    assert activation_binding["attempted"] is True
    assert activation_binding["allowed"] is True
    assert activation_binding["reason"] == "visible write-tool activation value-proof bound"
    assert activation_binding["args"] == candidate["arguments"]
    assert activation_binding["lease_id"].startswith("tool-activation-live:retail:2:11")
    assert len(trace["leases"]) == 1
    assert trace["leases"][0]["args"]["item_ids"]["equals"] == [
        "cleaner_item",
        "headphone_item",
        "watch_item",
    ]


def test_write_tool_activation_binder_blocks_missing_value_proof():
    candidate = {
        "domain": "retail",
        "task_id": "2",
        "event_id": "retail:2:2_11",
        "tool": "return_delivered_order_items",
        "arguments": {
            "item_ids": ["cleaner_item", "headphone_item", "watch_item"],
            "order_id": "#O",
            "payment_method_id": "card",
        },
        "activation_kind": "write_or_high_impact_tool_activation_value_proof_complete",
        "proof_status": "write_activation_value_proof_complete",
        "tool_type": "write",
        "intent_evidence": "return the cleaner, headphone, and smart watch",
        "earliest_activation_step": 1,
    }
    trace, _, _ = runner.build_compiler_corpus_task_trace(
        domain="retail",
        task_id="2",
        compiler_record={"repaired_model_json": {"leases": []}},
        tools_by_name={},
    )
    runner.attach_read_tool_activation_templates(
        trace=trace,
        domain="retail",
        task_id="2",
        candidates=[candidate],
    )
    gateway = LiveToolGateway(
        trace,
        {
            "tau2.retail.assistant.return_delivered_order_items": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )
    event = {
        "id": "retail:2:2_11",
        "op": "tool.call",
        "object": "tau2.retail.assistant.return_delivered_order_items",
        "args": candidate["arguments"],
        "decision": "retail.return_delivered_order_items.tool_choice",
        "mode": "tool_select",
        "control_provenance": [runner.TRUSTED_TASK_INTENT],
        "data_provenance": [runner.TRUSTED_TASK_INTENT],
        "intentcap_markers": {
            "_intentcap_synthesized_from_tool_activation": True,
            "_intentcap_tool_activation_event_id": "retail:2:2_11",
        },
    }

    record, runtime_binding, activation_binding = (
        runner.call_gateway_with_optional_runtime_binding(
            gateway=gateway,
            event=event,
            domain="retail",
            task_id="2",
            index=11,
            raw_task={
                "id": "2",
                "instruction": (
                    "Return #O cleaner_item headphone_item watch_item with card."
                ),
            },
            action_rows=[],
            enabled=False,
        )
    )

    assert record["executed"] is False
    assert runtime_binding["attempted"] is False
    assert activation_binding["attempted"] is True
    assert activation_binding["allowed"] is False
    assert "missing structured value proof" in activation_binding["reason"]
    assert len(trace["leases"]) == 0


def test_repair_map_priority_executes_visible_candidate_without_model(tmp_path: Path):
    candidate = {
        "domain": "mock",
        "task_id": "t",
        "event_id": "mock:t:create_1",
        "tool": "create_task",
        "arguments": {"user_id": "user_1", "title": "Important Meeting"},
        "repair_class": "visible_tool_argument_candidate_generation",
        "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
        "earliest_synthesis_step": 1,
    }
    action = ReferenceAction(
        event_id="mock:t:create_1",
        domain="mock",
        task_id="t",
        action_id="create_1",
        index=0,
        name="create_task",
        requestor="assistant",
        args={"user_id": "user_1", "title": "Important Meeting"},
        reward_basis=("ACTION",),
        object_name="tau2.mock.assistant.create_task",
    )
    trace = runner.build_task_trace("mock", "t", [action])
    gateway = LiveToolGateway(
        trace,
        {
            "tau2.mock.assistant.create_task": lambda **kwargs: {
                "ok": True,
                "kwargs": kwargs,
            }
        },
    )
    model_runner_called = False

    def fake_runner(command, timeout):
        nonlocal model_runner_called
        model_runner_called = True
        return '{"actions":[]}', "", 0, 0.0

    (tmp_path / "prompts").mkdir()
    (tmp_path / "raw").mkdir()
    result = runner.run_stepwise_model_loop(
        domain="mock",
        raw_task={"id": "t", "instruction": "user_1 needs Important Meeting"},
        tools=[{"name": "create_task", "parameters": {}}],
        tool_exposure="leased",
        active_tool_names={"create_task"},
        max_steps=1,
        empty_retries=0,
        state_grounded_arg_hints=False,
        compiler_lease_hints=False,
        runtime_evidence_lease_hints=False,
        runtime_evidence_rank_hints=False,
        compact_json_prompts=False,
        step_prompt_dir=tmp_path / "prompts",
        step_raw_dir=tmp_path / "raw",
        llama_bin=Path("llama"),
        model=Path("model.gguf"),
        n_predict=16,
        ctx_size=128,
        gpu_layers=0,
        timeout_seconds=1,
        dry_run=False,
        runner=fake_runner,
        single_hint_fallback=False,
        hint_choice_fallback=False,
        compiler_lease_fallback=False,
        runtime_evidence_fallback=False,
        runtime_evidence_ranked_fallback=False,
        runtime_evidence_ranked_fallback_min_score=50,
        runtime_evidence_ranked_fallback_margin=0,
        runtime_evidence_hint_choice_fallback=False,
        repair_map_candidates=[candidate],
        repair_map_fallback=False,
        repair_map_priority=True,
        pending_reference_actions=[action],
        reference_by_event={action.event_id: action},
        reference_event_ids=[action.event_id],
        gateway=gateway,
        trajectory=[],
        tool_call_cls=SimpleNamespace,
        assistant_message_cls=SimpleNamespace,
        action_rows=[],
        executed_reference_ids=[],
        bound_reference_ids=[],
        include_reference_event_ids=True,
        compiler_runtime_binding=False,
    )

    assert model_runner_called is False
    assert len(result["steps"]) == 1
    assert result["steps"][0]["repair_map_priority"] is True
    assert result["steps"][0]["repair_map_fallback"] is False
    assert result["steps"][0]["new_action_rows"][0]["executed"] is True
    assert result["steps"][0]["new_action_rows"][0]["bound_reference_event_id"] == "mock:t:create_1"


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


def test_step_prompt_can_include_compiler_lease_hints_without_reference_actions():
    prompt = runner.build_step_prompt(
        domain="mock",
        raw_task={
            "id": "t",
            "instruction": "Update the visible task.",
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
        action_rows=[],
        compiler_lease_arg_hints=[
            {
                "tool": "create_task",
                "arguments": {"title": "Visible compiler value"},
                "complete_arguments": True,
                "grounding": "active compiler lease strict argument constraints; no reference actions used",
            }
        ],
    )

    assert "active_compiler_lease_hints" in prompt
    assert "Visible compiler value" in prompt
    assert "Hidden reference" not in prompt
    assert "evaluation_criteria" not in prompt


def test_step_prompt_can_include_runtime_evidence_hints_without_reference_actions():
    prompt = runner.build_step_prompt(
        domain="airline",
        raw_task={
            "id": "t",
            "instruction": "Cancel the visible reservation.",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "cancel_reservation",
                        "arguments": {"reservation_id": "HIDDEN"},
                    }
                ]
            },
        },
        tools=[{"name": "cancel_reservation", "parameters": {}}],
        step_index=2,
        action_rows=[],
        runtime_evidence_lease_hints=[
            {
                "tool": "cancel_reservation",
                "arguments": {"reservation_id": "Q69X3R"},
                "complete_arguments": True,
                "grounding": "runtime-bindable compiler template plus executed tool-result evidence; no reference actions used",
            }
        ],
    )

    assert "runtime_evidence_compiler_hints" in prompt
    assert "Q69X3R" in prompt
    assert "HIDDEN" not in prompt
    assert "evaluation_criteria" not in prompt


def test_compact_step_prompt_forbids_reasoning_without_reference_actions():
    prompt = runner.build_step_prompt(
        domain="airline",
        raw_task={
            "id": "t",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "get_reservation_details",
                        "arguments": {"reservation_id": "HIDDEN"},
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
                "grounding": "visible",
            }
        ],
        compact_json_prompt=True,
    )

    assert "JSON-only tau2 step. /no_think" in prompt
    assert "Do not write <think>" in prompt
    assert '{"actions":[]}' in prompt
    assert "Q69X3R" in prompt
    assert "HIDDEN" not in prompt
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


def test_runtime_evidence_hint_choice_prompt_includes_intent_evidence_not_reference():
    prompt = runner.build_hint_choice_prompt(
        domain="airline",
        raw_task={
            "id": "t",
            "instruction": "Cancel the PHL to LGA reservation.",
            "evaluation_criteria": {
                "actions": [
                    {
                        "name": "cancel_reservation",
                        "arguments": {"reservation_id": "HIDDEN"},
                    }
                ]
            },
        },
        step_index=2,
        action_rows=[],
        complete_hints=[
            {
                "tool": "cancel_reservation",
                "arguments": {"reservation_id": "Q69X3R"},
                "complete_arguments": True,
                "grounding": "runtime evidence",
                "intent_evidence": "User wants to cancel the PHL to LGA reservation.",
                "lease_template_id": "template:cancel",
            }
        ],
        hint_label="runtime_evidence_compiler_hints",
    )

    assert "runtime_evidence_compiler_hints" in prompt
    assert "User wants to cancel the PHL to LGA reservation" in prompt
    assert "template:cancel" in prompt
    assert "HIDDEN" not in prompt
    assert "evaluation_criteria" not in prompt


def test_compact_hint_choice_prompt_forbids_reasoning_without_reference_actions():
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
        action_rows=[],
        complete_hints=[
            {
                "tool": "get_order_details",
                "arguments": {"order_id": "#W2378156"},
                "complete_arguments": True,
                "grounding": "visible",
            }
        ],
        compact_json_prompt=True,
    )

    assert "JSON-only selector. /no_think" in prompt
    assert "Do not write <think>" in prompt
    assert "selected_hint_id" in prompt
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

    runtime_call = runner.build_hint_choice_fallback_call_with_marker(
        hints,
        {"selected_hint_id": "hint_0"},
        marker_name="_intentcap_synthesized_from_runtime_evidence_hint_choice",
    )

    assert runtime_call == {
        "tool": "get_order_details",
        "arguments": {
            "order_id": "#W2378156",
            "_intentcap_synthesized_from_runtime_evidence_hint_choice": True,
            "_intentcap_hint_choice_id": "hint_0",
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
