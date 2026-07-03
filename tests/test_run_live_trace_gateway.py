import importlib.util
from pathlib import Path

from intentcap.live_gateway import LiveToolGateway


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_live_trace_gateway.py"
    spec = importlib.util.spec_from_file_location("run_live_trace_gateway", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_live_trace_runner_executes_only_allowed_registered_callables():
    runner = _load_runner()
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "tool_select": ["BenignLookup.tool_choice"],
                }
            },
            "untrusted_tool_result": {
                "allowed": {
                    "summarize": ["user.visible_summary"],
                }
            },
        },
        "leases": [
            {
                "id": "intent:benign",
                "op": "tool.call",
                "object": "BenignLookup",
                "args": {"_intentcap_event_id": {"equals": "benign"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
            },
            {
                "id": "overbroad:attacker",
                "op": "tool.call",
                "object": "AttackerSendEmail",
                "args": {"_intentcap_event_id": {"equals": "attacker"}},
                "control_may_depend_on": ["untrusted_tool_result"],
                "data_may_depend_on": ["untrusted_tool_result"],
            },
        ],
        "events": [
            {
                "id": "benign",
                "op": "tool.call",
                "object": "BenignLookup",
                "args": {"_intentcap_event_id": "benign", "query": "laptop"},
                "decision": "BenignLookup.tool_choice",
                "mode": "tool_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
                "intentcap_event_type": "benign_user_tool",
            },
            {
                "id": "attacker",
                "op": "tool.call",
                "object": "AttackerSendEmail",
                "args": {"_intentcap_event_id": "attacker", "to": "attacker@example.com"},
                "decision": "AttackerSendEmail.sink",
                "mode": "sink_select",
                "control_provenance": ["untrusted_tool_result"],
                "data_provenance": ["untrusted_tool_result"],
                "intentcap_event_type": "injected_attacker_tool",
            },
        ],
    }
    callable_invocations = []
    tools = runner._tool_registry(trace, callable_invocations)
    gateway = LiveToolGateway(trace, tools)

    records = gateway.run_events()
    summary = runner._summary(trace, records, callable_invocations, gateway.summary(records), tools)

    assert sorted(tools) == ["AttackerSendEmail", "BenignLookup"]
    assert len(callable_invocations) == 1
    assert callable_invocations[0]["tool"] == "BenignLookup"
    assert summary["registered_tools"] == 2
    assert summary["registered_executed_events"] == 1
    assert summary["registered_blocked_events"] == 1
    assert summary["callable_invocation_event_type_counts"] == {"benign_user_tool": 1}
    assert summary["executed_event_type_counts"] == {"benign_user_tool": 1}
    assert summary["blocked_event_type_counts"] == {"injected_attacker_tool": 1}
    assert summary["missing_tool_events"] == 0
