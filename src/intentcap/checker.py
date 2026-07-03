"""Minimal offline checker for IntentCap traces.

The first prototype is intentionally small: it checks whether an event is
covered by a lease and whether the event's control/data provenance is allowed
by both the lease and the context labels.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Verdict:
    event_id: str
    allowed: bool
    reason: str
    lease_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "allowed": self.allowed,
            "reason": self.reason,
            "lease_id": self.lease_id,
        }


def check_trace(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Check all events in a trace and return JSON-serializable verdicts."""

    labels = trace.get("labels", {})
    leases = trace.get("leases", [])
    verdicts = [
        check_event(event, leases, labels)
        for event in trace.get("events", [])
    ]
    return verdicts


def check_event(
    event: dict[str, Any],
    leases: list[dict[str, Any]],
    labels: dict[str, Any],
) -> dict[str, Any]:
    """Check one event against active leases and labels."""

    return _check_event(event, leases, labels).to_dict()


def _check_event(
    event: dict[str, Any],
    leases: list[dict[str, Any]],
    labels: dict[str, Any],
) -> Verdict:
    event_id = str(event.get("id", "<unknown>"))
    candidates = [lease for lease in leases if _lease_matches_event(lease, event)]
    if not candidates:
        return Verdict(event_id, False, "no matching lease")

    denial_reasons: list[str] = []
    for lease in candidates:
        reason = _check_provenance(event, lease, labels)
        if reason is None:
            return Verdict(event_id, True, "allowed", str(lease.get("id", "<lease>")))
        denial_reasons.append(f"{lease.get('id', '<lease>')}: {reason}")

    return Verdict(event_id, False, "; ".join(denial_reasons))


def _lease_matches_event(lease: dict[str, Any], event: dict[str, Any]) -> bool:
    if lease.get("op") != event.get("op"):
        return False
    if lease.get("object") != event.get("object"):
        return False

    arg_constraints = lease.get("args", {})
    event_args = event.get("args", {})
    for name, constraint in arg_constraints.items():
        if not _value_matches(event_args.get(name), constraint):
            return False
    return True


def _value_matches(value: Any, constraint: Any) -> bool:
    if not isinstance(constraint, dict):
        return value == constraint
    if "equals" in constraint:
        return value == constraint["equals"]
    if "one_of" in constraint:
        return value in constraint["one_of"]
    if "prefix" in constraint:
        return isinstance(value, str) and value.startswith(str(constraint["prefix"]))
    if "suffix" in constraint:
        return isinstance(value, str) and value.endswith(str(constraint["suffix"]))
    return False


def _check_provenance(
    event: dict[str, Any],
    lease: dict[str, Any],
    labels: dict[str, Any],
) -> str | None:
    decision = str(event.get("decision", "*"))
    mode = str(event.get("mode", "*"))

    allowed_control = set(lease.get("control_may_depend_on", []))
    for source in event.get("control_provenance", []):
        if source not in allowed_control:
            return f"control source {source!r} not allowed by lease"
        if not _label_allows(labels.get(source, {}), mode, decision):
            return (
                f"control source {source!r} lacks influence mode "
                f"{mode!r} for decision {decision!r}"
            )

    allowed_data = set(lease.get("data_may_depend_on", []))
    for source in event.get("data_provenance", []):
        if source not in allowed_data:
            return f"data source {source!r} not allowed by lease"

    return None


def _label_allows(label: dict[str, Any], mode: str, decision: str) -> bool:
    allowed = label.get("allowed", {})
    decisions = allowed.get(mode, [])
    return "*" in decisions or decision in decisions


def main() -> int:
    parser = argparse.ArgumentParser(description="Check an IntentCap JSON trace")
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()

    trace = json.loads(args.trace.read_text())
    print(json.dumps(check_trace(trace), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
