"""Analyze authority breadth for an MCPTox IntentCap trace.

This complements the InjecAgent minimization analysis with an MCP-specific
setting. MCPTox attacks often steer a model to call a legitimate tool through a
poisoned tool description, so an object-only ACL can be narrow and still unsafe.
The comparison therefore reports both exposed object breadth and whether a
baseline checks provenance.
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
    "intentcap_provenance",
    "exact_tool_acl",
    "authentic_server_allowlist",
    "observed_server_allowlist",
    "global_authentic_tools",
    "global_observed_tools",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze MCPTox authority minimization")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--response-all", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.trace.read_text())
    response_all = json.loads(args.response_all.read_text())
    result = analyze(trace, response_all)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "authority_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "admitted_events.csv", result["admitted_events"])
    _write_rows(args.output_dir / "event_exposure.csv", result["event_exposure"])
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(trace: dict[str, Any], response_all: dict[str, Any]) -> dict[str, Any]:
    authentic_by_server, authentic_tools = _authentic_tools(response_all)
    events = [
        event
        for event in trace.get("events", [])
        if event.get("op") == "mcp.call"
    ]
    observed_by_server = _observed_by_server(events)
    observed_tools = {
        str(event.get("object", ""))
        for event in events
        if event.get("object")
    }

    baselines: dict[str, Any] = {}
    admitted_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []

    for baseline in BASELINE_ORDER:
        exposed_counts: list[int] = []
        admitted_count = 0
        admitted_by_mode: Counter[str] = Counter()
        admitted_by_risk: Counter[str] = Counter()
        admitted_by_parse: Counter[str] = Counter()
        admitted_authentic_tool_events = 0
        admitted_poisoned_or_unknown_tool_events = 0

        for event in events:
            scope = _scope_for_baseline(
                baseline,
                event,
                authentic_by_server,
                authentic_tools,
                observed_by_server,
                observed_tools,
            )
            exposed_counts.append(len(scope))
            exposure_rows.append(
                {
                    "baseline": baseline,
                    "event_id": str(event.get("id", "")),
                    "server": str(event.get("mcptox", {}).get("server", "")),
                    "object": str(event.get("object", "")),
                    "security_risk": str(event.get("mcptox", {}).get("security_risk", "")),
                    "mode": str(event.get("mode", "")),
                    "parse_method": str(event.get("mcptox", {}).get("parse_method", "")),
                    "exposed_tools": len(scope),
                    "object_is_authentic": str(event.get("object", "")) in authentic_tools,
                }
            )
            if _admits_event(baseline, event, scope):
                admitted_count += 1
                meta = event.get("mcptox", {})
                admitted_by_mode[str(event.get("mode", ""))] += 1
                admitted_by_risk[str(meta.get("security_risk", ""))] += 1
                admitted_by_parse[str(meta.get("parse_method", ""))] += 1
                if str(event.get("object", "")) in authentic_tools:
                    admitted_authentic_tool_events += 1
                else:
                    admitted_poisoned_or_unknown_tool_events += 1
                admitted_rows.append(
                    {
                        "baseline": baseline,
                        "event_id": str(event.get("id", "")),
                        "server": str(meta.get("server", "")),
                        "object": str(event.get("object", "")),
                        "poisoned_tool": str(meta.get("poisoned_tool", "")),
                        "security_risk": str(meta.get("security_risk", "")),
                        "mode": str(event.get("mode", "")),
                        "decision": str(event.get("decision", "")),
                        "parse_method": str(meta.get("parse_method", "")),
                        "object_is_authentic": str(event.get("object", "")) in authentic_tools,
                    }
                )

        baselines[baseline] = {
            "description": _baseline_description(baseline),
            "protected_events": len(events),
            "admitted_events": admitted_count,
            "blocked_events": len(events) - admitted_count,
            "admitted_rate": admitted_count / len(events) if events else 0.0,
            "mean_exposed_tools_per_event": _mean(exposed_counts),
            "median_exposed_tools_per_event": _median(exposed_counts),
            "p95_exposed_tools_per_event": _percentile(exposed_counts, 0.95),
            "max_exposed_tools_per_event": max(exposed_counts, default=0),
            "control_provenance_checked": baseline == "intentcap_provenance",
            "argument_event_id_checked": baseline == "intentcap_provenance",
            "admitted_by_mode": dict(sorted(admitted_by_mode.items())),
            "admitted_by_security_risk": dict(sorted(admitted_by_risk.items())),
            "admitted_by_parse_method": dict(sorted(admitted_by_parse.items())),
            "admitted_authentic_tool_events": admitted_authentic_tool_events,
            "admitted_poisoned_or_unknown_tool_events": admitted_poisoned_or_unknown_tool_events,
        }

    intentcap_exposure = baselines["intentcap_provenance"]["mean_exposed_tools_per_event"]
    for baseline, summary in baselines.items():
        summary["mean_tool_exposure_over_intentcap"] = (
            summary["mean_exposed_tools_per_event"] / intentcap_exposure
            if intentcap_exposure
            else 0.0
        )

    summary = {
        "benchmark": "MCPTox",
        "trace_intent": trace.get("intent", {}),
        "protected_events": len(events),
        "labels": len(trace.get("labels", {})),
        "leases": len(trace.get("leases", [])),
        "servers_in_trace": len(observed_by_server),
        "authentic_servers": len(authentic_by_server),
        "authentic_tools": len(authentic_tools),
        "observed_trace_tools": len(observed_tools),
        "event_objects_not_in_authentic_catalog": len(observed_tools - authentic_tools),
        "event_objects_in_authentic_catalog": len(observed_tools & authentic_tools),
        "mode_counts": dict(sorted(Counter(str(event.get("mode", "")) for event in events).items())),
        "parse_method_counts": dict(
            sorted(Counter(str(event.get("mcptox", {}).get("parse_method", "")) for event in events).items())
        ),
        "baseline_order": list(BASELINE_ORDER),
        "baselines": baselines,
        "notes": [
            "IntentCap provenance baseline models the checker outcome: poisoned descriptions may be quoted or summarized, not used as control provenance for protected MCP calls.",
            "Object-only baselines intentionally ignore control provenance and argument event-id constraints.",
            "Authentic tool counts come from response_all.json server tool_names; observed tools include parsed successful calls and may include poisoned/generated tool names.",
        ],
    }
    return {
        "summary": summary,
        "admitted_events": admitted_rows,
        "event_exposure": exposure_rows,
    }


def _authentic_tools(response_all: dict[str, Any]) -> tuple[dict[str, set[str]], set[str]]:
    by_server: dict[str, set[str]] = {}
    all_tools: set[str] = set()
    for server_name, server in response_all.get("servers", {}).items():
        tools = {
            f"{server_name}.{tool_name}"
            for tool_name in server.get("tool_names", [])
        }
        by_server[server_name] = tools
        all_tools.update(tools)
    return by_server, all_tools


def _observed_by_server(events: list[dict[str, Any]]) -> dict[str, set[str]]:
    by_server: dict[str, set[str]] = defaultdict(set)
    for event in events:
        server = str(event.get("mcptox", {}).get("server", ""))
        obj = str(event.get("object", ""))
        if server and obj:
            by_server[server].add(obj)
    return dict(by_server)


def _scope_for_baseline(
    baseline: str,
    event: dict[str, Any],
    authentic_by_server: dict[str, set[str]],
    authentic_tools: set[str],
    observed_by_server: dict[str, set[str]],
    observed_tools: set[str],
) -> set[str]:
    obj = str(event.get("object", ""))
    server = str(event.get("mcptox", {}).get("server", ""))
    if baseline in {"intentcap_provenance", "exact_tool_acl"}:
        return {obj} if obj else set()
    if baseline == "authentic_server_allowlist":
        return set(authentic_by_server.get(server, set()))
    if baseline == "observed_server_allowlist":
        return set(observed_by_server.get(server, set()))
    if baseline == "global_authentic_tools":
        return set(authentic_tools)
    if baseline == "global_observed_tools":
        return set(observed_tools)
    raise ValueError(f"unknown baseline: {baseline}")


def _admits_event(baseline: str, event: dict[str, Any], scope: set[str]) -> bool:
    if baseline == "intentcap_provenance":
        return False
    return str(event.get("object", "")) in scope


def _baseline_description(baseline: str) -> str:
    return {
        "intentcap_provenance": "Exact MCP object plus event-id/provenance check; poisoned tool descriptions cannot control protected decisions.",
        "exact_tool_acl": "Only the called MCP tool object is exposed, but provenance and argument event-id constraints are not checked.",
        "authentic_server_allowlist": "All authentic tools for the event's MCP server are exposed, using response_all.json tool_names.",
        "observed_server_allowlist": "All MCP tools observed in successful parsed calls for the event's server are exposed.",
        "global_authentic_tools": "All authentic MCP tools from response_all.json are exposed.",
        "global_observed_tools": "All MCP tools observed in successful parsed calls are exposed.",
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
