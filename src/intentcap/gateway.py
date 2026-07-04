"""IntentCap gateway replay utilities.

The gateway is a small runtime-facing layer over the deterministic checker. It
does not execute tools; it decides whether an attempted action would be exposed
and allowed by the active leases and context-authority labels.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from intentcap.checker import check_event, check_trace


@dataclass(frozen=True)
class GatewayDecision:
    event_id: str
    op: str
    object: str
    mode: str
    decision: str
    action: str
    allowed: bool
    reason: str
    lease_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "op": self.op,
            "object": self.object,
            "mode": self.mode,
            "decision": self.decision,
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "lease_id": self.lease_id,
        }


class TraceGateway:
    """Replay a trace through a gateway-style allow/block interface."""

    def __init__(self, trace: dict[str, Any]) -> None:
        self.trace = trace
        self.labels = trace.get("labels", {})
        self.leases = trace.get("leases", [])
        self.events = trace.get("events", [])

    def exposed_objects(self) -> list[dict[str, str]]:
        """Return leased operation/object pairs visible to the agent."""

        exposed = {
            (str(lease.get("op", "")), str(lease.get("object", "")))
            for lease in self.leases
        }
        return [
            {
                "op": op,
                "object": obj,
            }
            for op, obj in sorted(exposed)
        ]

    def authorize(self, event: dict[str, Any]) -> GatewayDecision:
        verdict = check_event(event, self.leases, self.labels)
        return self._decision_from_verdict(event, verdict)

    def _decision_from_verdict(
        self,
        event: dict[str, Any],
        verdict: dict[str, Any],
    ) -> GatewayDecision:
        allowed = bool(verdict["allowed"])
        return GatewayDecision(
            event_id=str(event.get("id", "<unknown>")),
            op=str(event.get("op", "")),
            object=str(event.get("object", "")),
            mode=str(event.get("mode", "")),
            decision=str(event.get("decision", "")),
            action="execute" if allowed else "block",
            allowed=allowed,
            reason=str(verdict["reason"]),
            lease_id=verdict.get("lease_id"),
        )

    def replay(self) -> list[dict[str, Any]]:
        verdicts = check_trace(self.trace)
        return [
            self._decision_from_verdict(event, verdict).to_dict()
            for event, verdict in zip(self.events, verdicts)
        ]

    def summary(self, decisions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if decisions is None:
            decisions = self.replay()

        attempts = len(decisions)
        allowed = sum(1 for decision in decisions if decision["allowed"])
        blocked = attempts - allowed
        by_mode = Counter(str(decision.get("mode", "")) for decision in decisions)
        blocked_by_mode = Counter(
            str(decision.get("mode", ""))
            for decision in decisions
            if not decision["allowed"]
        )
        by_op = Counter(str(decision.get("op", "")) for decision in decisions)
        blocked_by_op = Counter(
            str(decision.get("op", ""))
            for decision in decisions
            if not decision["allowed"]
        )

        return {
            "attempted_events": attempts,
            "executed_events": allowed,
            "blocked_events": blocked,
            "exposed_objects": len(self.exposed_objects()),
            "active_leases": len(self.leases),
            "labels": len(self.labels),
            "mode_counts": dict(sorted(by_mode.items())),
            "blocked_mode_counts": dict(sorted(blocked_by_mode.items())),
            "op_counts": dict(sorted(by_op.items())),
            "blocked_op_counts": dict(sorted(blocked_by_op.items())),
        }
