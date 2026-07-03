"""Audit AgentDojo goal-inferred IntentCap events.

This script consumes an already exported AgentDojo IntentCap trace and separates
benchmark-provided ground-truth events from adapter-inferred goal events. It is
intentionally independent of AgentDojo so the audit is reproducible from saved
R011 artifacts alone.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


OFFICIAL_PAPER_USE = "paper-ready benchmark trajectory event"
INFERRED_PAPER_USE = "adapter-only coverage; do not report as benchmark trajectory"
OFFICIAL_LIMITATION = "Benchmark ground_truth() produced this protected-decision event."
INFERRED_LIMITATION = (
    "Event was inferred from the AgentDojo injection goal and environment templates; "
    "it is useful for adapter coverage but is not a benchmark-provided trajectory."
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit AgentDojo ground-truth and goal-inferred events")
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path)
    parser.add_argument("--gateway-decisions", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    trace = _load_json(args.trace)
    verdicts = _load_json(args.verdicts) if args.verdicts else []
    gateway_decisions = _load_json(args.gateway_decisions) if args.gateway_decisions else []

    task_audit, summary = audit_trace(trace, verdicts=verdicts, gateway_decisions=gateway_decisions)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "task_audit.json").write_text(json.dumps(task_audit, indent=2, sort_keys=True))
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    write_task_audit_csv(task_audit, args.output_dir / "task_audit.csv")
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def audit_trace(
    trace: dict[str, Any],
    *,
    verdicts: list[dict[str, Any]] | None = None,
    gateway_decisions: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    verdict_by_event = {str(verdict.get("event_id")): verdict for verdict in (verdicts or [])}
    gateway_by_event = {str(decision.get("event_id")): decision for decision in (gateway_decisions or [])}
    events_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for event in trace.get("events", []):
        events_by_task[_task_id(event)].append(event)

    task_audit: list[dict[str, Any]] = []
    for task_id in sorted(events_by_task, key=_task_sort_key):
        events = sorted(events_by_task[task_id], key=lambda event: str(event.get("id", "")))
        task_audit.append(_audit_task(task_id, events, verdict_by_event, gateway_by_event))

    summary = _summary(task_audit, verdicts or [], gateway_decisions or [])
    return task_audit, summary


def write_task_audit_csv(task_audit: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "task_id",
        "oracle_source",
        "audit_status",
        "event_count",
        "ground_truth_events",
        "goal_inferred_events",
        "unknown_events",
        "checker_allowed",
        "checker_denied",
        "gateway_executed",
        "gateway_blocked",
        "mode_counts",
        "object_counts",
        "decision_counts",
        "paper_use",
        "limitation",
    ]
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for task in task_audit:
            row = dict(task)
            row["mode_counts"] = json.dumps(task["mode_counts"], sort_keys=True)
            row["object_counts"] = json.dumps(task["object_counts"], sort_keys=True)
            row["decision_counts"] = json.dumps(task["decision_counts"], sort_keys=True)
            row.pop("events", None)
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _audit_task(
    task_id: str,
    events: list[dict[str, Any]],
    verdict_by_event: dict[str, dict[str, Any]],
    gateway_by_event: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ground_truth_events = 0
    goal_inferred_events = 0
    unknown_events = 0
    checker_allowed = 0
    checker_denied = 0
    gateway_executed = 0
    gateway_blocked = 0
    mode_counts: Counter[str] = Counter()
    object_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    event_rows: list[dict[str, Any]] = []

    for event in events:
        event_id = str(event.get("id", ""))
        source = _event_source(event)
        official_ground_truth = source == "ground_truth"
        if official_ground_truth:
            ground_truth_events += 1
        elif source == "goal_inferred":
            goal_inferred_events += 1
        else:
            unknown_events += 1

        verdict = verdict_by_event.get(event_id, {})
        gateway = gateway_by_event.get(event_id, {})
        if verdict:
            if verdict.get("allowed"):
                checker_allowed += 1
            else:
                checker_denied += 1
        if gateway:
            if gateway.get("action") == "execute":
                gateway_executed += 1
            elif gateway.get("action") == "block":
                gateway_blocked += 1

        mode = str(event.get("mode", "unknown"))
        obj = str(event.get("object", "unknown"))
        decision = str(event.get("decision", "unknown"))
        mode_counts[mode] += 1
        object_counts[obj] += 1
        decision_counts[decision] += 1

        event_rows.append(
            {
                "id": event_id,
                "object": obj,
                "mode": mode,
                "decision": decision,
                "event_source": source,
                "official_ground_truth": official_ground_truth,
                "inference_reason": _inference_reason(event),
                "verdict_allowed": verdict.get("allowed"),
                "verdict_reason": verdict.get("reason"),
                "gateway_action": gateway.get("action"),
                "gateway_reason": gateway.get("reason"),
            }
        )

    oracle_source, audit_status, paper_use, limitation = _task_status(
        ground_truth_events, goal_inferred_events, unknown_events
    )

    return {
        "task_id": task_id,
        "oracle_source": oracle_source,
        "audit_status": audit_status,
        "event_count": len(events),
        "ground_truth_events": ground_truth_events,
        "goal_inferred_events": goal_inferred_events,
        "unknown_events": unknown_events,
        "checker_allowed": checker_allowed,
        "checker_denied": checker_denied,
        "gateway_executed": gateway_executed,
        "gateway_blocked": gateway_blocked,
        "mode_counts": dict(sorted(mode_counts.items())),
        "object_counts": dict(sorted(object_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "paper_use": paper_use,
        "limitation": limitation,
        "events": event_rows,
    }


def _summary(
    task_audit: list[dict[str, Any]],
    verdicts: list[dict[str, Any]],
    gateway_decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    total_events = sum(task["event_count"] for task in task_audit)
    official_events = sum(task["ground_truth_events"] for task in task_audit)
    inferred_events = sum(task["goal_inferred_events"] for task in task_audit)
    unknown_events = sum(task["unknown_events"] for task in task_audit)
    checker_allowed = sum(task["checker_allowed"] for task in task_audit)
    checker_denied = sum(task["checker_denied"] for task in task_audit)
    gateway_executed = sum(task["gateway_executed"] for task in task_audit)
    gateway_blocked = sum(task["gateway_blocked"] for task in task_audit)
    mode_counts = Counter()
    object_counts = Counter()
    status_counts = Counter()

    for task in task_audit:
        mode_counts.update(task["mode_counts"])
        object_counts.update(task["object_counts"])
        status_counts[task["audit_status"]] += 1

    warnings: list[str] = []
    if inferred_events:
        warnings.append(
            "Goal-inferred events expand adapter coverage but cannot be reported as official benchmark trajectories."
        )
    if unknown_events:
        warnings.append(f"Found {unknown_events} events with unknown provenance.")
    if verdicts and len(verdicts) != total_events:
        warnings.append(f"Verdict count mismatch: {len(verdicts)} verdicts for {total_events} events.")
    if gateway_decisions and len(gateway_decisions) != total_events:
        warnings.append(
            f"Gateway decision count mismatch: {len(gateway_decisions)} decisions for {total_events} events."
        )

    return {
        "total_tasks": len(task_audit),
        "tasks_with_ground_truth": sum(1 for task in task_audit if task["ground_truth_events"] > 0),
        "tasks_with_goal_inferred": sum(1 for task in task_audit if task["goal_inferred_events"] > 0),
        "total_events": total_events,
        "official_ground_truth_events": official_events,
        "goal_inferred_events": inferred_events,
        "unknown_events": unknown_events,
        "paper_ready_trajectory_events": official_events,
        "adapter_only_events": inferred_events,
        "checker_allowed_events": checker_allowed,
        "checker_denied_events": checker_denied,
        "gateway_executed_events": gateway_executed,
        "gateway_blocked_events": gateway_blocked,
        "mode_counts": dict(sorted(mode_counts.items())),
        "object_counts": dict(sorted(object_counts.items())),
        "audit_status_counts": dict(sorted(status_counts.items())),
        "audit_verdict": "warn" if warnings else "pass",
        "warnings": warnings,
    }


def _task_status(
    ground_truth_events: int,
    goal_inferred_events: int,
    unknown_events: int,
) -> tuple[str, str, str, str]:
    if ground_truth_events and not goal_inferred_events and not unknown_events:
        return (
            "benchmark_ground_truth",
            "official_ground_truth_replay",
            OFFICIAL_PAPER_USE,
            OFFICIAL_LIMITATION,
        )
    if goal_inferred_events and not ground_truth_events and not unknown_events:
        return (
            "adapter_goal_inference",
            "goal_inferred_needs_review",
            INFERRED_PAPER_USE,
            INFERRED_LIMITATION,
        )
    return (
        "mixed_or_unknown",
        "mixed_oracle_review",
        "review before reporting",
        "Task contains mixed or unknown event provenance.",
    )


def _event_source(event: dict[str, Any]) -> str:
    event_type = event.get("intentcap_event_type")
    inference = event.get("agentdojo", {}).get("inference", {})
    if event_type == "ground_truth":
        return "ground_truth"
    if event_type == "goal_inferred" or inference.get("official_ground_truth") is False:
        return "goal_inferred"
    return "unknown"


def _inference_reason(event: dict[str, Any]) -> str | None:
    inference = event.get("agentdojo", {}).get("inference")
    if not inference:
        return None
    return str(inference.get("reason", ""))


def _task_id(event: dict[str, Any]) -> str:
    return str(event.get("agentdojo", {}).get("injection_task") or event.get("task_id") or "unknown")


def _task_sort_key(task_id: str) -> tuple[str, int | str]:
    prefix, _, suffix = task_id.rpartition("_")
    if suffix.isdigit():
        return (prefix, int(suffix))
    return (task_id, task_id)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


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
