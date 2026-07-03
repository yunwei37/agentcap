"""Live tool gateway utilities for IntentCap.

Unlike TraceGateway, this wrapper executes registered Python callables after a
checker allow decision. It is intentionally small and local-only: the goal is to
exercise the runtime shape of an allow/block tool gateway without depending on
external APIs or model credentials.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from intentcap.gateway import TraceGateway


ToolRegistry = dict[str, Callable[..., Any]]


class LiveToolGateway:
    """Authorize attempted tool calls and execute registered tools when allowed."""

    def __init__(self, trace: dict[str, Any], tools: ToolRegistry) -> None:
        self.trace_gateway = TraceGateway(trace)
        self.tools = tools
        self.records: list[dict[str, Any]] = []

    def exposed_objects(self) -> list[dict[str, str]]:
        return self.trace_gateway.exposed_objects()

    def call(self, event: dict[str, Any]) -> dict[str, Any]:
        decision = self.trace_gateway.authorize(event).to_dict()
        if not decision["allowed"]:
            record = _record(decision, executed=False)
            self.records.append(record)
            return record

        tool_name = str(event.get("object", ""))
        tool = self.tools.get(tool_name)
        if tool is None:
            missing_decision = {
                **decision,
                "allowed": False,
                "action": "missing_tool",
                "reason": f"no registered tool for {tool_name!r}",
            }
            record = _record(missing_decision, executed=False, error=missing_decision["reason"])
            self.records.append(record)
            return record

        args = _call_args(event.get("args", {}))
        try:
            result = tool(**args)
        except Exception as exc:  # pragma: no cover - exercised only by fault-injection callers
            record = _record(
                decision,
                executed=True,
                error=f"{type(exc).__name__}: {exc}",
                tool_args=args,
            )
        else:
            record = _record(decision, executed=True, result=result, tool_args=args)

        self.records.append(record)
        return record

    def run_events(self, events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        if events is None:
            events = self.trace_gateway.events
        return [self.call(event) for event in events]

    def summary(self, records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if records is None:
            records = self.records

        attempted = len(records)
        executed = sum(1 for record in records if record["executed"])
        blocked = attempted - executed
        errors = sum(1 for record in records if record.get("error"))
        actions = Counter(str(record["decision"].get("action", "")) for record in records)
        executed_objects = Counter(
            str(record["decision"].get("object", ""))
            for record in records
            if record["executed"]
        )
        blocked_objects = Counter(
            str(record["decision"].get("object", ""))
            for record in records
            if not record["executed"]
        )

        return {
            "attempted_events": attempted,
            "executed_events": executed,
            "blocked_events": blocked,
            "tool_errors": errors,
            "exposed_objects": len(self.exposed_objects()),
            "action_counts": dict(sorted(actions.items())),
            "executed_object_counts": dict(sorted(executed_objects.items())),
            "blocked_object_counts": dict(sorted(blocked_objects.items())),
        }


def _record(
    decision: dict[str, Any],
    *,
    executed: bool,
    result: Any = None,
    error: str | None = None,
    tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "decision": decision,
        "executed": executed,
        "result": result,
        "error": error,
        "tool_args": tool_args or {},
    }


def _call_args(args: Any) -> dict[str, Any]:
    if not isinstance(args, dict):
        return {}
    return {
        key: value
        for key, value in args.items()
        if not str(key).startswith("_intentcap_")
    }
