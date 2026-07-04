"""Run a saved IntentCap trace through LiveToolGateway.

The script registers a local Python callable for every object in the trace,
then executes events only after the deterministic checker allows them. It is a
benchmark-derived live execution smoke: the attempted actions come from saved
benchmark adapters, while the tools are local no-op callables so the run does
not need external APIs or credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.live_gateway import LiveToolGateway


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a saved trace through the live IntentCap tool gateway")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    trace_bytes = args.trace.read_bytes()
    trace = json.loads(trace_bytes)
    if args.max_events is not None:
        trace = {**trace, "events": trace.get("events", [])[: args.max_events]}

    args.output_dir.mkdir(parents=True, exist_ok=True)
    callable_invocations: list[dict[str, Any]] = []
    tools = _tool_registry(trace, callable_invocations)
    gateway = LiveToolGateway(trace, tools)
    records = gateway.run_events()
    summary = {
        **_summary(trace, records, callable_invocations, gateway.summary(records), tools),
        "run_id": args.run_id,
        "trace_path": str(args.trace),
        "input_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }

    (args.output_dir / "live_gateway_records.json").write_text(json.dumps(records, indent=2, sort_keys=True))
    (args.output_dir / "live_gateway_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (args.output_dir / "callable_invocations.json").write_text(
        json.dumps(callable_invocations, indent=2, sort_keys=True)
    )
    (args.output_dir / "registered_tools.json").write_text(json.dumps(sorted(tools), indent=2))
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _tool_registry(trace: dict[str, Any], callable_invocations: list[dict[str, Any]]):
    objects = {
        str(event.get("object", ""))
        for event in trace.get("events", [])
        if event.get("object")
    }
    return {
        obj: _make_recording_tool(obj, callable_invocations)
        for obj in objects
    }


def _make_recording_tool(tool_name: str, callable_invocations: list[dict[str, Any]]):
    def tool(**kwargs: Any) -> dict[str, Any]:
        callable_invocations.append(
            {
                "tool": tool_name,
                "args": kwargs,
            }
        )
        return {
            "tool": tool_name,
            "status": "executed",
        }

    return tool


def _summary(
    trace: dict[str, Any],
    records: list[dict[str, Any]],
    callable_invocations: list[dict[str, Any]],
    gateway_summary: dict[str, Any],
    tools: dict[str, Any],
) -> dict[str, Any]:
    event_by_id = {str(event.get("id", "")): event for event in trace.get("events", [])}
    attempted_event_types = Counter()
    executed_event_types = Counter()
    blocked_event_types = Counter()
    executed_modes = Counter()
    blocked_modes = Counter()
    registered_blocked = 0
    registered_executed = 0
    tool_errors = 0

    for record in records:
        decision = record.get("decision", {})
        event_id = str(decision.get("event_id", ""))
        event = event_by_id.get(event_id, {})
        event_type = str(event.get("intentcap_event_type") or event.get("id") or "unknown")
        mode = str(event.get("mode", "unknown"))
        obj = str(decision.get("object", ""))
        attempted_event_types[event_type] += 1
        if record.get("executed"):
            executed_event_types[event_type] += 1
            executed_modes[mode] += 1
            registered_executed += int(obj in tools)
        else:
            blocked_event_types[event_type] += 1
            blocked_modes[mode] += 1
            registered_blocked += int(obj in tools)
        if record.get("error"):
            tool_errors += 1

    return {
        **gateway_summary,
        "registered_tools": len(tools),
        "registered_executed_events": registered_executed,
        "registered_blocked_events": registered_blocked,
        "callable_invocations": len(callable_invocations),
        "callable_invocation_event_type_counts": dict(sorted(executed_event_types.items())),
        "attempted_event_type_counts": dict(sorted(attempted_event_types.items())),
        "executed_event_type_counts": dict(sorted(executed_event_types.items())),
        "blocked_event_type_counts": dict(sorted(blocked_event_types.items())),
        "executed_mode_counts": dict(sorted(executed_modes.items())),
        "blocked_mode_counts": dict(sorted(blocked_modes.items())),
        "tool_errors": tool_errors,
        "missing_tool_events": sum(
            1 for record in records if record.get("decision", {}).get("action") == "missing_tool"
        ),
    }


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
