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
    state = _initial_state()
    verdicts = []
    for event in trace.get("events", []):
        verdict = _check_event(event, leases, labels, state).to_dict()
        verdicts.append(verdict)
        if verdict["allowed"]:
            _record_allowed_event(event, verdict, state)
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
    state: dict[str, Any] | None = None,
) -> Verdict:
    event_id = str(event.get("id", "<unknown>"))
    if state is None:
        state = _initial_state()
    candidates = [lease for lease in leases if _lease_matches_event(lease, event)]
    if not candidates:
        return Verdict(event_id, False, "no matching lease")

    denial_reasons: list[str] = []
    for lease in candidates:
        reason = _check_lease_conditions(event, lease, state)
        if reason is None:
            reason = _check_provenance(event, lease, labels)
        if reason is None:
            return Verdict(event_id, True, "allowed", str(lease.get("id", "<lease>")))
        denial_reasons.append(f"{lease.get('id', '<lease>')}: {reason}")

    return Verdict(event_id, False, "; ".join(denial_reasons))


def _initial_state() -> dict[str, Any]:
    return {
        "completed_events": set(),
        "lease_invocations": {},
    }


def _record_allowed_event(
    event: dict[str, Any],
    verdict: dict[str, Any],
    state: dict[str, Any],
) -> None:
    state["completed_events"].add(str(event.get("id", "<unknown>")))
    lease_id = verdict.get("lease_id")
    if lease_id:
        counts = state["lease_invocations"]
        counts[lease_id] = counts.get(lease_id, 0) + 1


def _lease_matches_event(lease: dict[str, Any], event: dict[str, Any]) -> bool:
    if lease.get("op") != event.get("op"):
        return False
    if lease.get("object") != event.get("object"):
        return False

    arg_constraints = lease.get("args", {})
    event_args = event.get("args", {})
    if not isinstance(arg_constraints, dict) or not isinstance(event_args, dict):
        return False
    allowed_arg_keys = lease.get("allowed_arg_keys")
    if allowed_arg_keys is not None:
        if not isinstance(allowed_arg_keys, list):
            return False
        if set(event_args) != {str(name) for name in allowed_arg_keys}:
            return False
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


def _check_lease_conditions(
    event: dict[str, Any],
    lease: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    for check in (
        _check_holder,
        _check_temporal,
        _check_budget,
        _check_intent_derivation,
        _check_delegation,
    ):
        reason = check(event, lease, state)
        if reason is not None:
            return reason
    return None


def _check_holder(
    event: dict[str, Any],
    lease: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    del state
    holder = lease.get("holder")
    if holder is None:
        return None
    event_holder = event.get("holder")
    if event_holder != holder:
        return f"holder {event_holder!r} does not match lease holder {holder!r}"
    return None


def _check_temporal(
    event: dict[str, Any],
    lease: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    del event
    temporal = lease.get("temporal", {})
    required = []
    if isinstance(temporal, dict):
        required.extend(_as_list(temporal.get("after", [])))
    required.extend(_as_list(lease.get("after", [])))
    completed = state["completed_events"]
    missing = [str(event_id) for event_id in required if str(event_id) not in completed]
    if missing:
        return f"temporal prerequisites not satisfied: {missing}"
    return None


def _check_budget(
    event: dict[str, Any],
    lease: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    del event
    budget = lease.get("budget", {})
    if not isinstance(budget, dict) or "invocations" not in budget:
        return None
    try:
        max_invocations = int(budget["invocations"])
    except (TypeError, ValueError):
        return "invalid invocation budget"

    lease_id = str(lease.get("id", "<lease>"))
    used = state["lease_invocations"].get(lease_id, 0)
    if used >= max_invocations:
        return f"invocation budget exhausted: {used}/{max_invocations}"
    return None


def _check_intent_derivation(
    event: dict[str, Any],
    lease: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    del state
    intent = lease.get("intent", {})
    if not isinstance(intent, dict):
        return None

    required_sources = _as_list(intent.get("must_derive_from", []))
    proof = event.get("proof", {})
    proof_sources = _as_list(event.get("intent_provenance", []))
    if isinstance(proof, dict):
        proof_sources.extend(_as_list(proof.get("intent_sources", [])))
    missing_sources = [
        str(source)
        for source in required_sources
        if str(source) not in {str(proof_source) for proof_source in proof_sources}
    ]
    if missing_sources:
        return f"missing intent derivation proof: {missing_sources}"

    required_approvals = _as_list(intent.get("requires_approval", []))
    approvals = _as_list(event.get("approvals", []))
    if isinstance(proof, dict):
        approvals.extend(_as_list(proof.get("approvals", [])))
    missing_approvals = [
        str(approval)
        for approval in required_approvals
        if str(approval) not in {str(present) for present in approvals}
    ]
    if missing_approvals:
        return f"missing required approval proof: {missing_approvals}"
    return None


def _check_delegation(
    event: dict[str, Any],
    lease: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    del state
    if event.get("op") != "subagent.spawn":
        return None
    delegation = lease.get("delegation")
    if delegation is None:
        return None
    if delegation == "none":
        return "delegation forbidden by lease"
    if not isinstance(delegation, dict):
        return "invalid delegation constraint"
    if delegation.get("allowed") is False:
        return "delegation forbidden by lease"

    requested = event.get("args", {}).get("capabilities", [])
    allowed = delegation.get("capabilities", [])
    if not isinstance(requested, list) or not isinstance(allowed, list):
        return "invalid delegated capability list"
    for capability in requested:
        if not isinstance(capability, dict):
            return "invalid delegated capability"
        if not any(_capability_allows(allowed_capability, capability) for allowed_capability in allowed):
            return f"delegated capability exceeds lease attenuation: {capability}"
    return None


def _capability_allows(allowed: Any, requested: dict[str, Any]) -> bool:
    if not isinstance(allowed, dict):
        return False
    return (
        _field_allows(requested.get("op"), allowed.get("op", "*"))
        and _field_allows(requested.get("object"), allowed.get("object", "*"))
        and _field_allows(requested.get("mode"), allowed.get("mode", "*"))
    )


def _field_allows(value: Any, allowed: Any) -> bool:
    if allowed == "*":
        return True
    if isinstance(allowed, list):
        return value in allowed or "*" in allowed
    return value == allowed


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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
