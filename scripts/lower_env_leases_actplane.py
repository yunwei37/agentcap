"""Lower IntentCap env leases to an ActPlane-style policy target.

This script does not implement ActPlane. It produces a deterministic policy
artifact that an OS/env monitor could enforce before local side effects:
process, filesystem, network, and context-placement rules are derived from the
same leases checked by IntentCap. The experiment then replays the env suite
against both the checker and the lowered policy to verify that lowering keeps
the same side-effect boundary on the modeled events.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent / "src") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from intentcap.gateway import TraceGateway  # noqa: E402


DEFAULT_TRACE = Path("examples/env_adapter_side_effect_suite.json")

ROW_FIELDS = [
    "event_index",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "checker_allowed",
    "checker_reason",
    "checker_lease_id",
    "monitor_allowed",
    "monitor_reason",
    "monitor_rule_id",
    "unsafe_reference_event",
    "decision_match",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lower IntentCap env leases to an ActPlane-style policy"
    )
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R218ACTLOWER")
    args = parser.parse_args()

    result = run_lowering(trace_path=args.trace, output_dir=args.output_dir, run_id=args.run_id)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def run_lowering(*, trace_path: Path, output_dir: Path, run_id: str) -> dict[str, Any]:
    trace_bytes = trace_path.read_bytes()
    trace = json.loads(trace_bytes)
    output_dir.mkdir(parents=True, exist_ok=True)

    policy = lower_trace_to_policy(trace)
    rows = replay_lowered_policy(trace, policy)
    summary = summarize(
        run_id=run_id,
        trace_path=trace_path,
        trace_bytes=trace_bytes,
        output_dir=output_dir,
        policy=policy,
        rows=rows,
    )

    (output_dir / "actplane_policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n"
    )
    _write_rows(output_dir / "actplane_lowering_rows.csv", rows)
    (output_dir / "actplane_lowering_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "input_trace_digests.csv").write_text(
        "path,sha256,bytes\n"
        f"{trace_path},{hashlib.sha256(trace_bytes).hexdigest()},{len(trace_bytes)}\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"policy": policy, "rows": rows, "summary": summary}


def lower_trace_to_policy(trace: dict[str, Any]) -> dict[str, Any]:
    rules = []
    for lease in trace.get("leases", []):
        if not isinstance(lease, dict):
            continue
        rule = _lower_lease(lease)
        if rule is not None:
            rules.append(rule)
    return {
        "version": "intentcap-actplane-style-v0",
        "default_action": "deny",
        "contract": {
            "source": "IntentCap leases",
            "boundary": (
                "Generated rules are an env/OS monitor target. The deterministic "
                "checker remains responsible for issuing intent/provenance labels. "
                "The lowered monitor checks concrete event fields and the supplied "
                "label/influence contract before local side effects."
            ),
            "provenance": {
                "control": "adapter-supplied control_provenance must satisfy lowered influence rules",
                "data": "adapter-supplied data_provenance must satisfy lowered data rules",
            },
        },
        "context_labels": trace.get("labels", {}),
        "rules": rules,
    }


def _lower_lease(lease: dict[str, Any]) -> dict[str, Any] | None:
    op = str(lease.get("op", ""))
    rule_class = {
        "exec.run": "process.exec",
        "fs.read": "filesystem.read",
        "fs.write": "filesystem.write",
        "net.connect": "network.connect",
        "ctx.use": "context.use",
    }.get(op)
    if rule_class is None:
        return None

    return {
        "rule_id": str(lease.get("id", "<lease>")),
        "class": rule_class,
        "op": op,
        "holder": lease.get("holder"),
        "object": lease.get("object"),
        "arg_constraints": lease.get("args", {}),
        "allowed_arg_keys": lease.get("allowed_arg_keys"),
        "control_may_depend_on": lease.get("control_may_depend_on", []),
        "data_may_depend_on": lease.get("data_may_depend_on", []),
        "budget": lease.get("budget", {}),
        "lowering_notes": _lowering_notes(op, lease),
    }


def _lowering_notes(op: str, lease: dict[str, Any]) -> list[str]:
    notes = []
    if op == "exec.run":
        notes.append("monitor checks binary path and argv constraints before exec")
        notes.append("network is deny-by-default unless a separate net.connect rule exists")
    if op in {"fs.read", "fs.write"}:
        notes.append("monitor checks logical path constraints before filesystem side effect")
    if op == "ctx.use":
        notes.append("context constructor checks influence mode and decision class before placement")
    if lease.get("holder") is not None:
        notes.append("holder binding prevents cross-component reuse of the rule")
    if isinstance(lease.get("budget"), dict) and "invocations" in lease.get("budget", {}):
        notes.append("stateful monitor consumes invocation budget after allowed event")
    return notes


def replay_lowered_policy(
    trace: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    monitor = LoweredPolicyMonitor(policy)
    rows = []
    events = trace.get("events", [])
    for index, event in enumerate(events):
        checker_decision = _checker_decision(trace, index, event)
        monitor_decision = monitor.authorize(event)
        checker_allowed = bool(checker_decision.get("allowed"))
        monitor_allowed = bool(monitor_decision["allowed"])
        rows.append(
            {
                "event_index": index,
                "event_id": str(event.get("id", "")),
                "op": str(event.get("op", "")),
                "object": str(event.get("object", "")),
                "mode": str(event.get("mode", "")),
                "decision": str(event.get("decision", "")),
                "checker_allowed": checker_allowed,
                "checker_reason": str(checker_decision.get("reason", "")),
                "checker_lease_id": str(checker_decision.get("lease_id") or ""),
                "monitor_allowed": monitor_allowed,
                "monitor_reason": str(monitor_decision["reason"]),
                "monitor_rule_id": str(monitor_decision.get("rule_id") or ""),
                "unsafe_reference_event": not checker_allowed,
                "decision_match": checker_allowed == monitor_allowed,
            }
        )
    return rows


def _checker_decision(
    trace: dict[str, Any],
    index: int,
    event: dict[str, Any],
) -> dict[str, Any]:
    prefix = {**trace, "events": trace.get("events", [])[:index] + [event]}
    return TraceGateway(prefix).replay()[-1]


class LoweredPolicyMonitor:
    """Small stateful interpreter for the generated policy artifact."""

    def __init__(self, policy: dict[str, Any]) -> None:
        self.rules = [rule for rule in policy.get("rules", []) if isinstance(rule, dict)]
        labels = policy.get("context_labels", {})
        self.labels = labels if isinstance(labels, dict) else {}
        self.invocations: dict[str, int] = {}

    def authorize(self, event: dict[str, Any]) -> dict[str, Any]:
        rejection_reasons = []
        for rule in self.rules:
            reason = _rule_rejects(rule, event, self.invocations, self.labels)
            if reason is None:
                rule_id = str(rule.get("rule_id", "<rule>"))
                self.invocations[rule_id] = self.invocations.get(rule_id, 0) + 1
                return {
                    "allowed": True,
                    "reason": "lowered policy rule matched",
                    "rule_id": rule_id,
                }
            rejection_reasons.append(f"{rule.get('rule_id', '<rule>')}: {reason}")
        return {
            "allowed": False,
            "reason": "; ".join(rejection_reasons) if rejection_reasons else "no rules",
            "rule_id": None,
        }


def _rule_rejects(
    rule: dict[str, Any],
    event: dict[str, Any],
    invocations: dict[str, int],
    labels: dict[str, Any],
) -> str | None:
    if rule.get("op") != event.get("op"):
        return "op mismatch"
    if rule.get("object") != event.get("object"):
        return "object mismatch"
    holder = rule.get("holder")
    if holder is not None and event.get("holder") != holder:
        return "holder mismatch"

    allowed_keys = rule.get("allowed_arg_keys")
    if allowed_keys is not None:
        if not isinstance(allowed_keys, list):
            return "invalid allowed_arg_keys"
        if set(event.get("args", {})) != {str(key) for key in allowed_keys}:
            return "argument key mismatch"

    constraints = rule.get("arg_constraints", {})
    if not isinstance(constraints, dict):
        return "invalid arg constraints"
    event_args = event.get("args", {})
    if not isinstance(event_args, dict):
        return "invalid event args"
    for name, constraint in constraints.items():
        if not _value_matches(event_args.get(name), constraint):
            return f"argument {name!r} mismatch"

    decision = str(event.get("decision", "*"))
    mode = str(event.get("mode", "*"))
    allowed_control = {str(source) for source in rule.get("control_may_depend_on", [])}
    for source in event.get("control_provenance", []):
        source = str(source)
        if source not in allowed_control:
            return f"control source {source!r} not allowed by lowered rule"
        if not _label_allows(labels.get(source, {}), mode, decision):
            return (
                f"control source {source!r} lacks influence mode "
                f"{mode!r} for decision {decision!r}"
            )

    allowed_data = {str(source) for source in rule.get("data_may_depend_on", [])}
    for source in event.get("data_provenance", []):
        source = str(source)
        if source not in allowed_data:
            return f"data source {source!r} not allowed by lowered rule"

    budget = rule.get("budget", {})
    if isinstance(budget, dict) and "invocations" in budget:
        try:
            max_invocations = int(budget["invocations"])
        except (TypeError, ValueError):
            return "invalid invocation budget"
        rule_id = str(rule.get("rule_id", "<rule>"))
        used = invocations.get(rule_id, 0)
        if used >= max_invocations:
            return "invocation budget exhausted"

    return None


def _label_allows(label: dict[str, Any], mode: str, decision: str) -> bool:
    allowed = label.get("allowed", {})
    if not isinstance(allowed, dict):
        return False
    decisions = allowed.get(mode, [])
    return isinstance(decisions, list) and ("*" in decisions or decision in decisions)


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


def summarize(
    *,
    run_id: str,
    trace_path: Path,
    trace_bytes: bytes,
    output_dir: Path,
    policy: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    checker_allowed = sum(1 for row in rows if row["checker_allowed"])
    monitor_allowed = sum(1 for row in rows if row["monitor_allowed"])
    decision_mismatches = [row for row in rows if not row["decision_match"]]
    unsafe_monitor_allowed = [
        row for row in rows if row["unsafe_reference_event"] and row["monitor_allowed"]
    ]
    checker_allowed_monitor_denied = [
        row for row in rows if row["checker_allowed"] and not row["monitor_allowed"]
    ]
    rule_counts: dict[str, int] = {}
    for rule in policy.get("rules", []):
        rule_class = str(rule.get("class", ""))
        rule_counts[rule_class] = rule_counts.get(rule_class, 0) + 1
    return {
        "run_id": run_id,
        "analysis": "ActPlane-style lowering of IntentCap env leases",
        "trace_path": str(trace_path),
        "input_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "events": len(rows),
        "lowered_rules": len(policy.get("rules", [])),
        "rule_counts": dict(sorted(rule_counts.items())),
        "checker_allowed": checker_allowed,
        "checker_blocked": len(rows) - checker_allowed,
        "monitor_allowed": monitor_allowed,
        "monitor_blocked": len(rows) - monitor_allowed,
        "decision_mismatches": len(decision_mismatches),
        "unsafe_monitor_allowed": len(unsafe_monitor_allowed),
        "checker_allowed_monitor_denied": len(checker_allowed_monitor_denied),
        "default_action": policy.get("default_action"),
        "output_dir": str(output_dir),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This is a deterministic lowering target, not a production ActPlane integration.",
            "The generated policy is deny-by-default and derived only from active IntentCap leases.",
            "The deterministic checker remains the source of intent/provenance labels.",
            "The monitor interpreter checks concrete op/object/holder/argument/budget constraints and supplied influence labels before side effects.",
        ],
    }


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ROW_FIELDS, lineterminator="\n")
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


def _git_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
