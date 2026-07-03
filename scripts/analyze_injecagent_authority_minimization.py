"""Analyze authority breadth for an InjecAgent mixed IntentCap trace.

The script compares run-time IntentCap one-shot leases against several static
object-scope policies on the same set of InjecAgent cases. It does not run a
model. It asks a narrower question useful for C2: how much tool authority would
be exposed per case, and how many injected attacker-tool events would be
admitted if policy ignored context provenance and only checked object scope?
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASELINE_ORDER = (
    "intentcap_one_shot",
    "task_tool_allowlist",
    "toolkit_allowlist",
    "benchmark_user_tools",
    "observed_trace_tools",
    "catalog_all_tools",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze InjecAgent authority minimization")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--tool-catalog", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.trace.read_text())
    tool_catalog = json.loads(args.tool_catalog.read_text())
    result = analyze(trace, tool_catalog)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "authority_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "admitted_attacks.csv", result["admitted_attacks"])
    _write_rows(args.output_dir / "case_exposure.csv", result["case_exposure"])
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(trace: dict[str, Any], tool_catalog: list[dict[str, Any]]) -> dict[str, Any]:
    full_to_toolkit, toolkit_to_tools, catalog_tools = _catalog_index(tool_catalog)
    cases = _case_index(trace)
    user_tools = {
        case["user_tool"]
        for case in cases.values()
        if case.get("user_tool")
    }
    observed_tools = {
        str(event.get("object", ""))
        for event in trace.get("events", [])
        if event.get("op") == "tool.call" and event.get("object")
    }

    baselines = _baselines(user_tools, observed_tools, catalog_tools)
    baseline_summaries: dict[str, Any] = {}
    admitted_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []

    for baseline in BASELINE_ORDER:
        exposure_counts: list[int] = []
        admitted = 0
        admitted_by_mode: Counter[str] = Counter()
        admitted_by_family: Counter[str] = Counter()
        exposed_tool_slots = 0

        for case_key, case in sorted(cases.items()):
            scope = _scope_for_baseline(
                baseline,
                case,
                toolkit_to_tools,
                baselines,
                full_to_toolkit,
            )
            exposure_count = len(scope)
            exposure_counts.append(exposure_count)
            exposed_tool_slots += exposure_count
            case_rows.append(
                {
                    "baseline": baseline,
                    "case_id": case_key,
                    "attack_family": case["attack_family"],
                    "user_tool": case["user_tool"],
                    "user_toolkit": full_to_toolkit.get(case["user_tool"], ""),
                    "exposed_tools": exposure_count,
                    "attacker_events": len(case["attacker_events"]),
                }
            )

            for event in case["attacker_events"]:
                if _admits_attacker_event(baseline, event, scope, case):
                    admitted += 1
                    admitted_by_mode[str(event.get("mode", ""))] += 1
                    admitted_by_family[str(event.get("injecagent", {}).get("attack_family", ""))] += 1
                    admitted_rows.append(
                        {
                            "baseline": baseline,
                            "event_id": str(event.get("id", "")),
                            "attack_family": str(event.get("injecagent", {}).get("attack_family", "")),
                            "attack_type": str(event.get("injecagent", {}).get("attack_type", "")),
                            "user_tool": case["user_tool"],
                            "user_toolkit": full_to_toolkit.get(case["user_tool"], ""),
                            "attacker_tool": str(event.get("object", "")),
                            "attacker_toolkit": full_to_toolkit.get(str(event.get("object", "")), ""),
                            "mode": str(event.get("mode", "")),
                            "decision": str(event.get("decision", "")),
                        }
                    )

        total_attacks = sum(len(case["attacker_events"]) for case in cases.values())
        baseline_summaries[baseline] = {
            "description": _baseline_description(baseline),
            "cases": len(cases),
            "protected_attack_events": total_attacks,
            "admitted_attack_events": admitted,
            "blocked_attack_events": total_attacks - admitted,
            "admitted_attack_rate": admitted / total_attacks if total_attacks else 0.0,
            "exposed_tool_slots_total": exposed_tool_slots,
            "mean_exposed_tools_per_case": _mean(exposure_counts),
            "median_exposed_tools_per_case": _median(exposure_counts),
            "p95_exposed_tools_per_case": _percentile(exposure_counts, 0.95),
            "max_exposed_tools_per_case": max(exposure_counts, default=0),
            "broad_arguments": baseline != "intentcap_one_shot",
            "control_provenance_checked": baseline == "intentcap_one_shot",
            "admitted_by_mode": dict(sorted(admitted_by_mode.items())),
            "admitted_by_attack_family": dict(sorted(admitted_by_family.items())),
        }

    intentcap_slots = baseline_summaries["intentcap_one_shot"]["exposed_tool_slots_total"]
    for baseline, summary in baseline_summaries.items():
        summary["tool_slot_over_intentcap_ratio"] = (
            summary["exposed_tool_slots_total"] / intentcap_slots
            if intentcap_slots
            else 0.0
        )
        summary["extra_tool_slots_vs_intentcap"] = (
            summary["exposed_tool_slots_total"] - intentcap_slots
        )

    summary = {
        "benchmark": "InjecAgent",
        "trace_intent": trace.get("intent", {}),
        "cases": len(cases),
        "trace_events": len(trace.get("events", [])),
        "benign_user_tool_events": sum(1 for case in cases.values() if case.get("user_event")),
        "protected_attack_events": sum(len(case["attacker_events"]) for case in cases.values()),
        "unique_user_tools": len(user_tools),
        "unique_observed_tools": len(observed_tools),
        "catalog_tools": len(catalog_tools),
        "unique_toolkits": len(toolkit_to_tools),
        "baseline_order": list(BASELINE_ORDER),
        "baselines": baseline_summaries,
        "notes": [
            "IntentCap one-shot counts only the trusted user-tool lease for each case.",
            "Static baselines are object-scope policies and intentionally do not check control provenance.",
            "Admitted attack events are injected attacker-tool events whose object falls inside the baseline scope.",
        ],
    }
    return {
        "summary": summary,
        "admitted_attacks": admitted_rows,
        "case_exposure": case_rows,
    }


def _catalog_index(
    tool_catalog: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, set[str]], set[str]]:
    full_to_toolkit: dict[str, str] = {}
    toolkit_to_tools: dict[str, set[str]] = defaultdict(set)
    catalog_tools: set[str] = set()
    for toolkit in tool_catalog:
        toolkit_name = str(toolkit.get("toolkit", ""))
        for tool in toolkit.get("tools", []):
            tool_name = str(tool.get("name", ""))
            full_name = f"{toolkit_name}{tool_name}"
            full_to_toolkit[full_name] = toolkit_name
            toolkit_to_tools[toolkit_name].add(full_name)
            catalog_tools.add(full_name)
    return full_to_toolkit, dict(toolkit_to_tools), catalog_tools


def _case_index(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for event in trace.get("events", []):
        meta = event.get("injecagent", {})
        case_id = _case_id(meta)
        case = cases.setdefault(
            case_id,
            {
                "setting": str(meta.get("setting", "")),
                "attack_family": str(meta.get("attack_family", "")),
                "case_index": int(meta.get("case_index", -1)),
                "user_tool": str(meta.get("user_tool", "")),
                "user_event": None,
                "attacker_events": [],
            },
        )
        if event.get("intentcap_event_type") == "benign_user_tool":
            case["user_event"] = event
            case["user_tool"] = str(event.get("object", case["user_tool"]))
        elif event.get("intentcap_event_type") == "injected_attacker_tool":
            case["attacker_events"].append(event)
    return cases


def _case_id(meta: dict[str, Any]) -> str:
    return (
        f"{meta.get('setting', '')}:"
        f"{meta.get('attack_family', '')}:"
        f"{meta.get('case_index', '')}:"
        f"{meta.get('user_tool', '')}"
    )


def _baselines(
    user_tools: set[str],
    observed_tools: set[str],
    catalog_tools: set[str],
) -> dict[str, set[str]]:
    return {
        "benchmark_user_tools": set(user_tools),
        "observed_trace_tools": set(observed_tools),
        "catalog_all_tools": set(catalog_tools),
    }


def _scope_for_baseline(
    baseline: str,
    case: dict[str, Any],
    toolkit_to_tools: dict[str, set[str]],
    baselines: dict[str, set[str]],
    full_to_toolkit: dict[str, str],
) -> set[str]:
    user_tool = str(case.get("user_tool", ""))
    if baseline in {"intentcap_one_shot", "task_tool_allowlist"}:
        return {user_tool} if user_tool else set()
    if baseline == "toolkit_allowlist":
        return set(toolkit_to_tools.get(full_to_toolkit.get(user_tool, ""), set()))
    if baseline in baselines:
        return set(baselines[baseline])
    raise ValueError(f"unknown baseline: {baseline}")


def _admits_attacker_event(
    baseline: str,
    event: dict[str, Any],
    scope: set[str],
    case: dict[str, Any],
) -> bool:
    if baseline == "intentcap_one_shot":
        # The one-shot lease is bound to the benign event id and trusted intent.
        return False
    return str(event.get("object", "")) in scope


def _baseline_description(baseline: str) -> str:
    return {
        "intentcap_one_shot": "One trusted user-tool lease per case, exact event id, provenance checked.",
        "task_tool_allowlist": "Only the requested user tool is exposed for the case, but arguments/provenance are broad.",
        "toolkit_allowlist": "All tools in the requested user tool's toolkit/server are exposed for the case.",
        "benchmark_user_tools": "All benchmark user-facing tools are exposed for every case.",
        "observed_trace_tools": "All tools observed in the mixed trace are exposed for every case.",
        "catalog_all_tools": "All tools in the InjecAgent catalog are exposed for every case.",
    }[baseline]


def _mean(values: list[int]) -> float:
    return statistics.fmean(values) if values else 0.0


def _median(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def _percentile(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return float(ordered[index])


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
