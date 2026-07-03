"""Export InjecAgent cases into IntentCap-style traces.

This script does not run an LLM. It converts InjecAgent's synthesized indirect
prompt-injection cases into protected-decision events: each attacker tool that
the benchmark expects the agent to call becomes an event whose control
provenance is the untrusted user-tool response containing attacker content.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.checker import check_trace


CASE_FILES = {
    ("direct_harm", "base"): "test_cases_dh_base.json",
    ("direct_harm", "enhanced"): "test_cases_dh_enhanced.json",
    ("data_stealing", "base"): "test_cases_ds_base.json",
    ("data_stealing", "enhanced"): "test_cases_ds_enhanced.json",
}

SINK_WORDS = (
    "email",
    "gmail",
    "message",
    "post",
    "publish",
    "send",
    "share",
    "transfer",
    "upload",
    "withdraw",
)

DATA_READ_WORDS = (
    "get",
    "list",
    "read",
    "retrieve",
    "search",
    "view",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export InjecAgent cases as IntentCap traces")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/injecagent"))
    parser.add_argument("--setting", choices=["base", "enhanced", "all"], default="base")
    parser.add_argument("--attack-family", choices=["direct_harm", "data_stealing", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = _load_cases(args.benchmark_dir / "data", args.setting, args.attack_family)
    catalog = _catalog(args.benchmark_dir / "data", cases)
    trace = _trace_from_cases(cases)

    (args.output_dir / "catalog.json").write_text(json.dumps(catalog, indent=2, sort_keys=True))
    (args.output_dir / "intentcap_trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True))

    summary = _summary(cases, trace)
    summary["benchmark_dir"] = str(args.benchmark_dir)
    summary["setting"] = args.setting
    summary["attack_family"] = args.attack_family

    if args.check:
        verdicts = check_trace(trace)
        (args.output_dir / "intentcap_verdicts.json").write_text(json.dumps(verdicts, indent=2, sort_keys=True))
        summary["checker_allowed"] = sum(1 for verdict in verdicts if verdict["allowed"])
        summary["checker_denied"] = sum(1 for verdict in verdicts if not verdict["allowed"])

    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _load_cases(data_dir: Path, setting: str, attack_family: str) -> list[dict[str, Any]]:
    settings = ["base", "enhanced"] if setting == "all" else [setting]
    families = ["direct_harm", "data_stealing"] if attack_family == "all" else [attack_family]
    cases: list[dict[str, Any]] = []
    for current_setting in settings:
        for family in families:
            path = data_dir / CASE_FILES[(family, current_setting)]
            for index, case in enumerate(json.loads(path.read_text())):
                cases.append(
                    {
                        **case,
                        "_intentcap_setting": current_setting,
                        "_intentcap_attack_family": family,
                        "_intentcap_case_index": index,
                    }
                )
    return cases


def _catalog(data_dir: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    tools = json.loads((data_dir / "tools.json").read_text())
    user_cases = _load_jsonl(data_dir / "user_cases.jsonl")
    attacker_dh = _load_jsonl(data_dir / "attacker_cases_dh.jsonl")
    attacker_ds = _load_jsonl(data_dir / "attacker_cases_ds.jsonl")
    toolkits = [
        {
            "toolkit": toolkit.get("toolkit"),
            "category": toolkit.get("category"),
            "name_for_model": toolkit.get("name_for_model"),
            "tool_count": len(toolkit.get("tools", [])),
            "tools": [tool.get("name") for tool in toolkit.get("tools", [])],
        }
        for toolkit in tools
    ]

    return {
        "toolkit_count": len(toolkits),
        "tool_function_count": sum(toolkit["tool_count"] for toolkit in toolkits),
        "toolkits": toolkits,
        "user_case_count": len(user_cases),
        "attacker_direct_harm_case_count": len(attacker_dh),
        "attacker_data_stealing_case_count": len(attacker_ds),
        "selected_case_count": len(cases),
        "selected_attacker_tool_events": sum(len(case.get("Attacker Tools", [])) for case in cases),
        "selected_attack_families": dict(Counter(case["_intentcap_attack_family"] for case in cases)),
        "selected_settings": dict(Counter(case["_intentcap_setting"] for case in cases)),
        "selected_attack_types": dict(Counter(case.get("Attack Type", "") for case in cases)),
        "selected_user_tools": dict(Counter(case.get("User Tool", "") for case in cases)),
        "selected_attacker_tools": dict(Counter(tool for case in cases for tool in case.get("Attacker Tools", []))),
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _trace_from_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    labels: dict[str, Any] = {}
    leases: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    for case in cases:
        case_id = _case_id(case)
        source = f"injecagent_tool_response:{case_id}"
        labels[source] = {
            "origin": "user_tool_response_with_injected_attacker_instruction",
            "integrity": "untrusted_tool_response",
            "allowed": {
                "quote": ["user.visible_summary"],
                "summarize": ["user.visible_summary"],
                "parameterize": ["benign_tool.arguments"],
            },
            "injecagent": {
                "setting": case["_intentcap_setting"],
                "attack_family": case["_intentcap_attack_family"],
                "attack_type": case.get("Attack Type"),
                "user_tool": case.get("User Tool"),
            },
        }

        for tool_index, attacker_tool in enumerate(case.get("Attacker Tools", [])):
            decision, mode = _classify_attacker_tool(
                str(attacker_tool),
                str(case.get("Attack Type", "")),
                str(case.get("_intentcap_attack_family", "")),
            )
            event_id = f"{case_id}:{tool_index}:{attacker_tool}"
            event_args = {
                "_intentcap_event_id": event_id,
                "attacker_instruction": case.get("Attacker Instruction", ""),
            }
            events.append(
                {
                    "id": event_id,
                    "op": "tool.call",
                    "object": attacker_tool,
                    "args": event_args,
                    "decision": decision,
                    "mode": mode,
                    "control_provenance": [source],
                    "data_provenance": [source],
                    "injecagent": {
                        "setting": case["_intentcap_setting"],
                        "attack_family": case["_intentcap_attack_family"],
                        "case_index": case["_intentcap_case_index"],
                        "attack_type": case.get("Attack Type"),
                        "user_tool": case.get("User Tool"),
                        "user_instruction": case.get("User Instruction"),
                        "attacker_tool": attacker_tool,
                        "expected_achievements": case.get("Expected Achievements"),
                        "modified": case.get("Modifed"),
                    },
                }
            )
            leases.append(
                {
                    "id": f"overbroad:{event_id}",
                    "op": "tool.call",
                    "object": attacker_tool,
                    "args": {
                        "_intentcap_event_id": {
                            "equals": event_id,
                        },
                    },
                    "control_may_depend_on": [source],
                    "data_may_depend_on": [source],
                }
            )

    return {
        "intent": {
            "id": "injecagent:attacker-tool-replay",
            "goal": "replay_injecagent_attacker_tools_as_untrusted_tool_response_control",
        },
        "labels": labels,
        "leases": leases,
        "events": events,
    }


def _case_id(case: dict[str, Any]) -> str:
    return (
        f"{case['_intentcap_setting']}:{case['_intentcap_attack_family']}:"
        f"{case['_intentcap_case_index']}:{case.get('User Tool', '<unknown>')}"
    )


def _classify_attacker_tool(tool_name: str, attack_type: str, attack_family: str) -> tuple[str, str]:
    tool_lower = tool_name.lower()
    if any(word in tool_lower for word in SINK_WORDS):
        return f"{tool_name}.sink", "sink_select"
    if attack_family == "data_stealing" and any(word in tool_lower for word in DATA_READ_WORDS):
        return f"{tool_name}.authority", "authorize"
    if "data" in attack_type.lower() and any(word in tool_lower for word in DATA_READ_WORDS):
        return f"{tool_name}.authority", "authorize"
    return f"{tool_name}.authority", "authorize"


def _summary(cases: list[dict[str, Any]], trace: dict[str, Any]) -> dict[str, Any]:
    mode_counts = Counter(event.get("mode", "") for event in trace["events"])
    family_counts = Counter(case["_intentcap_attack_family"] for case in cases)
    setting_counts = Counter(case["_intentcap_setting"] for case in cases)
    attack_type_counts = Counter(case.get("Attack Type", "") for case in cases)
    return {
        "selected_cases": len(cases),
        "trace_events": len(trace["events"]),
        "labels": len(trace["labels"]),
        "leases": len(trace["leases"]),
        "mode_counts": dict(sorted(mode_counts.items())),
        "attack_family_counts": dict(sorted(family_counts.items())),
        "setting_counts": dict(sorted(setting_counts.items())),
        "attack_type_counts": dict(sorted(attack_type_counts.items())),
        "unique_user_tools": len({case.get("User Tool", "") for case in cases}),
        "unique_attacker_tools": len({tool for case in cases for tool in case.get("Attacker Tools", [])}),
    }


if __name__ == "__main__":
    raise SystemExit(main())
