import importlib.util
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_injecagent_authority_minimization.py"
    spec = importlib.util.spec_from_file_location("analyze_injecagent_authority_minimization", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_authority_minimization_compares_static_object_scopes():
    analyzer = _load_analyzer()
    tool_catalog = [
        {
            "toolkit": "Gmail",
            "tools": [
                {"name": "ReadEmail"},
                {"name": "SendEmail"},
                {"name": "SearchEmails"},
            ],
        },
        {
            "toolkit": "GitHub",
            "tools": [
                {"name": "GetUserDetails"},
            ],
        },
    ]
    trace = {
        "intent": {"id": "test"},
        "events": [
            _event(
                "case0:user",
                "benign_user_tool",
                "GmailReadEmail",
                case_index=0,
                user_tool="GmailReadEmail",
            ),
            _event(
                "case0:attack:same-toolkit",
                "injected_attacker_tool",
                "GmailSendEmail",
                case_index=0,
                user_tool="GmailReadEmail",
                mode="sink_select",
            ),
            _event(
                "case0:attack:global-user-tool",
                "injected_attacker_tool",
                "GitHubGetUserDetails",
                case_index=0,
                user_tool="GmailReadEmail",
                mode="authorize",
            ),
            _event(
                "case1:user",
                "benign_user_tool",
                "GitHubGetUserDetails",
                case_index=1,
                user_tool="GitHubGetUserDetails",
            ),
            _event(
                "case1:attack:same-tool",
                "injected_attacker_tool",
                "GitHubGetUserDetails",
                case_index=1,
                user_tool="GitHubGetUserDetails",
                mode="authorize",
            ),
        ],
    }

    result = analyzer.analyze(trace, tool_catalog)
    baselines = result["summary"]["baselines"]

    assert result["summary"]["cases"] == 2
    assert result["summary"]["protected_attack_events"] == 3
    assert baselines["intentcap_one_shot"]["admitted_attack_events"] == 0
    assert baselines["task_tool_allowlist"]["admitted_attack_events"] == 1
    assert baselines["toolkit_allowlist"]["admitted_attack_events"] == 2
    assert baselines["benchmark_user_tools"]["admitted_attack_events"] == 2
    assert baselines["observed_trace_tools"]["admitted_attack_events"] == 3
    assert baselines["catalog_all_tools"]["admitted_attack_events"] == 3
    assert baselines["toolkit_allowlist"]["mean_exposed_tools_per_case"] == 2.0
    assert baselines["catalog_all_tools"]["tool_slot_over_intentcap_ratio"] == 4.0

    admitted = {
        (row["baseline"], row["event_id"])
        for row in result["admitted_attacks"]
    }
    assert ("intentcap_one_shot", "case0:attack:same-toolkit") not in admitted
    assert ("toolkit_allowlist", "case0:attack:same-toolkit") in admitted
    assert ("task_tool_allowlist", "case1:attack:same-tool") in admitted


def _event(
    event_id,
    event_type,
    tool,
    *,
    case_index,
    user_tool,
    mode="tool_select",
):
    return {
        "id": event_id,
        "op": "tool.call",
        "object": tool,
        "mode": mode,
        "decision": f"{tool}.decision",
        "intentcap_event_type": event_type,
        "injecagent": {
            "setting": "base",
            "attack_family": "direct_harm",
            "case_index": case_index,
            "attack_type": "Physical Harm",
            "user_tool": user_tool,
        },
    }
