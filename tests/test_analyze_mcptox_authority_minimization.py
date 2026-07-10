import importlib.util
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_mcptox_authority_minimization.py"
    spec = importlib.util.spec_from_file_location("analyze_mcptox_authority_minimization", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcptox_minimization_shows_exact_tool_acl_still_needs_provenance():
    analyzer = _load_analyzer()
    response_all = {
        "servers": {
            "FileSystem": {
                "tool_names": ["read_file", "list_directory"],
            },
            "Email": {
                "tool_names": ["send_email", "search_email"],
            },
        }
    }
    trace = {
        "intent": {"id": "test"},
        "labels": {},
        "leases": [],
        "events": [
            _event(
                "e0",
                "FileSystem",
                "FileSystem.read_file",
                "authorize",
                "Credential Leakage",
                "structured",
            ),
            _event(
                "e1",
                "Email",
                "Email.send_email",
                "sink_select",
                "Message Hijacking",
                "fallback",
            ),
            _event(
                "e2",
                "FileSystem",
                "FileSystem.poisoned_helper",
                "tool_select",
                "Instruction Tampering",
                "structured",
            ),
        ],
    }

    result = analyzer.analyze(trace, response_all)
    baselines = result["summary"]["baselines"]

    assert result["summary"]["protected_events"] == 3
    assert result["summary"]["authentic_tools"] == 4
    assert result["summary"]["event_objects_not_in_authentic_catalog"] == 1
    assert baselines["intentcap_provenance"]["admitted_events"] == 0
    assert baselines["exact_tool_acl"]["admitted_events"] == 3
    assert baselines["exact_tool_acl"]["mean_exposed_tools_per_event"] == 1.0
    assert baselines["exact_tool_acl"]["control_provenance_checked"] is False
    assert baselines["authentic_server_allowlist"]["admitted_events"] == 2
    assert baselines["observed_server_allowlist"]["admitted_events"] == 3
    assert baselines["global_authentic_tools"]["admitted_events"] == 2
    assert baselines["global_observed_tools"]["admitted_events"] == 3
    assert baselines["authentic_server_allowlist"]["admitted_poisoned_or_unknown_tool_events"] == 0
    assert baselines["observed_server_allowlist"]["admitted_poisoned_or_unknown_tool_events"] == 1


def _event(event_id, server, obj, mode, risk, parse_method):
    tool = obj.split(".", 1)[1]
    return {
        "id": event_id,
        "op": "mcp.call",
        "object": obj,
        "mode": mode,
        "decision": f"{obj}.decision",
        "mcptox": {
            "server": server,
            "poisoned_tool": "decoy",
            "security_risk": risk,
            "parse_method": parse_method,
        },
        "args": {"_intentcap_event_id": event_id, "tool": tool},
    }
