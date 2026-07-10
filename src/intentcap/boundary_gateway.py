"""Live context-placement and delegation boundary adapters for IntentCap."""

from __future__ import annotations

from collections import Counter
from typing import Any

from intentcap.checker import CheckerSession


class LiveContextPlacementGateway:
    """Authorize context placement before content enters a prompt section."""

    def __init__(self, trace: dict[str, Any]) -> None:
        self.session = CheckerSession.from_trace(trace)
        self.sections: dict[str, list[dict[str, Any]]] = {}
        self.records: list[dict[str, Any]] = []

    def place(self, event: dict[str, Any], content: Any) -> dict[str, Any]:
        verdict = self.session.check(event)
        destination = _destination(event)
        if not verdict["allowed"]:
            record = _context_record(event, verdict, destination, placed=False)
            self.records.append(record)
            return record

        item = {
            "event_id": str(event.get("id", "<unknown>")),
            "source": str(event.get("object", "")),
            "mode": str(event.get("mode", "")),
            "content": content,
        }
        self.sections.setdefault(destination, []).append(item)
        record = _context_record(event, verdict, destination, placed=True)
        self.records.append(record)
        return record

    def summary(self) -> dict[str, Any]:
        placed = sum(1 for record in self.records if record["placed"])
        blocked = len(self.records) - placed
        destinations = Counter(record["destination"] for record in self.records)
        return {
            "attempted_placements": len(self.records),
            "placed_contexts": placed,
            "blocked_contexts": blocked,
            "destination_counts": dict(sorted(destinations.items())),
            "section_counts": {
                destination: len(items)
                for destination, items in sorted(self.sections.items())
            },
        }


class LiveDelegationMonitor:
    """Authorize subagent handoff before a child receives capabilities."""

    def __init__(self, trace: dict[str, Any]) -> None:
        self.session = CheckerSession.from_trace(trace)
        self.children: list[dict[str, Any]] = []
        self.records: list[dict[str, Any]] = []

    def spawn(self, event: dict[str, Any]) -> dict[str, Any]:
        verdict = self.session.check(event)
        if not verdict["allowed"]:
            record = _delegation_record(event, verdict, spawned=False)
            self.records.append(record)
            return record

        child = {
            "event_id": str(event.get("id", "<unknown>")),
            "subagent": str(event.get("object", "")),
            "role": _event_args(event).get("role"),
            "capabilities": _event_args(event).get("capabilities", []),
        }
        self.children.append(child)
        record = _delegation_record(event, verdict, spawned=True)
        self.records.append(record)
        return record

    def summary(self) -> dict[str, Any]:
        spawned = sum(1 for record in self.records if record["spawned"])
        blocked = len(self.records) - spawned
        return {
            "attempted_spawns": len(self.records),
            "spawned_subagents": spawned,
            "blocked_spawns": blocked,
            "children": len(self.children),
        }


def _context_record(
    event: dict[str, Any],
    verdict: dict[str, Any],
    destination: str,
    *,
    placed: bool,
) -> dict[str, Any]:
    return {
        "event_id": str(event.get("id", "<unknown>")),
        "source": str(event.get("object", "")),
        "mode": str(event.get("mode", "")),
        "decision": str(event.get("decision", "")),
        "destination": destination,
        "placed": placed,
        "verdict": verdict,
    }


def _delegation_record(
    event: dict[str, Any],
    verdict: dict[str, Any],
    *,
    spawned: bool,
) -> dict[str, Any]:
    return {
        "event_id": str(event.get("id", "<unknown>")),
        "subagent": str(event.get("object", "")),
        "role": _event_args(event).get("role"),
        "capability_count": len(_event_args(event).get("capabilities", [])),
        "spawned": spawned,
        "verdict": verdict,
    }


def _destination(event: dict[str, Any]) -> str:
    args = _event_args(event)
    return str(args.get("destination") or event.get("decision") or event.get("object") or "<unknown>")


def _event_args(event: dict[str, Any]) -> dict[str, Any]:
    args = event.get("args", {})
    return args if isinstance(args, dict) else {}
