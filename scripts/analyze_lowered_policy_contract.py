"""Audit the executable contract shape of an ActPlane-style lowering artifact.

This analysis is read-only. It consumes the existing R218 lowered policy and
the local env side-effect suite, then checks two things:

1. the generated policy carries the expected executable contract fields; and
2. removing one field family at a time creates false accepts on targeted
   challenge events.

The result is not a production ActPlane or kernel experiment. It is a focused
contract audit for the local lowering target used by the paper.
"""

from __future__ import annotations

import argparse
import copy
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


DEFAULT_OUTPUT_DIR = Path("results/eval/R296LOWERINGCONTRACT")
DEFAULT_INPUTS = {
    "trace": Path("examples/env_adapter_side_effect_suite.json"),
    "policy": Path("results/eval/R218ACTLOWER/actplane_policy.json"),
    "lowering_rows": Path("results/eval/R218ACTLOWER/actplane_lowering_rows.csv"),
    "lowering_summary": Path("results/eval/R218ACTLOWER/actplane_lowering_summary.json"),
}

ROW_FIELDS = [
    "variant",
    "challenge_id",
    "event_index",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "checker_allowed",
    "monitor_allowed",
    "unsafe_reference_event",
    "unsafe_accept",
    "decision_match",
    "monitor_reason",
    "monitor_rule_id",
]
VARIANT_FIELDS = [
    "variant",
    "unsafe_accepts",
    "decision_mismatches",
    "monitor_allowed",
    "checker_allowed",
]
INPUT_DIGEST_FIELDS = ["input_name", "path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit lowered-policy contract fields")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default="R296LOWERINGCONTRACT")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Override a default input path.",
    )
    args = parser.parse_args()

    inputs = dict(DEFAULT_INPUTS)
    for item in args.input:
        name, sep, value = item.partition("=")
        if not sep or not name:
            raise SystemExit(f"invalid --input override: {item!r}")
        inputs[name] = Path(value)

    result = analyze(output_dir=args.output_dir, inputs=inputs, run_id=args.run_id)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, output_dir: Path, inputs: dict[str, Path], run_id: str) -> dict[str, Any]:
    trace = _read_json(inputs["trace"])
    policy = _read_json(inputs["policy"])
    lowering_rows = _read_rows(inputs["lowering_rows"])
    lowering_summary = _read_json(inputs["lowering_summary"])
    _validate_r218_inputs(policy=policy, rows=lowering_rows, summary=lowering_summary)

    challenges = _challenge_sequences(trace)
    variants = _policy_variants(policy, _all_challenge_events(challenges))
    rows = _replay_variants(trace, variants, challenges)
    digests = [_file_digest(name, path) for name, path in sorted(inputs.items())]
    summary = _summary(
        run_id=run_id,
        policy=policy,
        challenges=challenges,
        rows=rows,
        digests=digests,
    )
    variant_rows = _variant_rows(rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "lowered_policy_contract_rows.csv", rows, ROW_FIELDS)
    _write_rows(output_dir / "lowered_policy_variant_summary.csv", variant_rows, VARIANT_FIELDS)
    _write_rows(output_dir / "input_digests.csv", digests, INPUT_DIGEST_FIELDS)
    (output_dir / "lowered_policy_contract_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows, "variant_rows": variant_rows}


def _validate_r218_inputs(
    *,
    policy: dict[str, Any],
    rows: list[dict[str, str]],
    summary: dict[str, Any],
) -> None:
    if policy.get("default_action") != "deny":
        raise ValueError("R218 policy is not deny-by-default")
    if int(summary.get("decision_mismatches", -1)) != 0:
        raise ValueError("R218 lowering summary contains checker/monitor mismatches")
    if int(summary.get("unsafe_monitor_allowed", -1)) != 0:
        raise ValueError("R218 lowering summary contains unsafe monitor accepts")
    if len(rows) != int(summary.get("events", -1)):
        raise ValueError("R218 rows do not match summary event count")


def _challenge_sequences(trace: dict[str, Any]) -> list[dict[str, Any]]:
    events = {str(event["id"]): event for event in trace.get("events", [])}
    duplicate_exec = copy.deepcopy(events["exec_pdf_skill_allowed"])
    duplicate_exec["id"] = "exec_pdf_skill_allowed_duplicate"
    return [
        {
            "challenge_id": "holder_binding",
            "events": [copy.deepcopy(events["exec_holder_mismatch"])],
        },
        {
            "challenge_id": "argument_output_constraint",
            "events": [copy.deepcopy(events["exec_wrong_output_path"])],
        },
        {
            "challenge_id": "argument_write_constraint",
            "events": [copy.deepcopy(events["write_path_traversal"])],
        },
        {
            "challenge_id": "control_influence",
            "events": [copy.deepcopy(events["script_output_promotes_instruction"])],
        },
        {
            "challenge_id": "budget_consume",
            "events": [copy.deepcopy(events["exec_pdf_skill_allowed"]), duplicate_exec],
        },
        {
            "challenge_id": "default_deny_network",
            "events": [copy.deepcopy(events["net_connect_attacker"])],
        },
        {
            "challenge_id": "default_deny_secret_read",
            "events": [copy.deepcopy(events["read_secret_env"])],
        },
    ]


def _all_challenge_events(challenges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for challenge in challenges for event in challenge["events"]]


def _policy_variants(
    policy: dict[str, Any],
    challenge_events: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        "full_policy": copy.deepcopy(policy),
        "no_holder_binding": _mutate_policy(policy, drop_holder=True),
        "no_argument_constraints": _mutate_policy(policy, drop_args=True),
        "no_provenance_influence": _mutate_policy(
            policy,
            trust_all_sources=True,
            challenge_events=challenge_events,
        ),
        "no_budget_state": _mutate_policy(policy, drop_budget=True),
        "default_allow_unmatched": _mutate_policy(policy, default_allow=True),
    }


def _mutate_policy(
    policy: dict[str, Any],
    *,
    drop_holder: bool = False,
    drop_args: bool = False,
    trust_all_sources: bool = False,
    challenge_events: list[dict[str, Any]] | None = None,
    drop_budget: bool = False,
    default_allow: bool = False,
) -> dict[str, Any]:
    mutated = copy.deepcopy(policy)
    labels = mutated.get("context_labels", {})
    label_names = sorted(labels) if isinstance(labels, dict) else []
    for rule in mutated.get("rules", []):
        if not isinstance(rule, dict):
            continue
        if drop_holder:
            rule["holder"] = None
        if drop_args:
            rule["arg_constraints"] = {}
            rule["allowed_arg_keys"] = None
        if trust_all_sources:
            rule["control_may_depend_on"] = label_names
            rule["data_may_depend_on"] = label_names
        if drop_budget:
            rule["budget"] = {}
    if trust_all_sources and isinstance(labels, dict):
        modes: dict[str, set[str]] = {}
        for event in challenge_events or []:
            modes.setdefault(str(event.get("mode", "")), set()).add(str(event.get("decision", "")))
        for label in labels.values():
            if not isinstance(label, dict):
                continue
            label["allowed"] = {
                mode: sorted(decisions | {"*"})
                for mode, decisions in sorted(modes.items())
            }
    if default_allow:
        mutated["default_action"] = "allow"
    return mutated


def _replay_variants(
    trace: dict[str, Any],
    variants: dict[str, dict[str, Any]],
    challenges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for variant_name, policy in variants.items():
        for challenge in challenges:
            checker_decisions = TraceGateway(
                {**trace, "events": challenge["events"]}
            ).replay()
            monitor = VariantMonitor(policy)
            for index, (event, checker_decision) in enumerate(
                zip(challenge["events"], checker_decisions)
            ):
                monitor_decision = monitor.authorize(event)
                checker_allowed = bool(checker_decision["allowed"])
                monitor_allowed = bool(monitor_decision["allowed"])
                unsafe = not checker_allowed
                rows.append(
                    {
                        "variant": variant_name,
                        "challenge_id": challenge["challenge_id"],
                        "event_index": index,
                        "event_id": str(event.get("id", "")),
                        "op": str(event.get("op", "")),
                        "object": str(event.get("object", "")),
                        "mode": str(event.get("mode", "")),
                        "decision": str(event.get("decision", "")),
                        "checker_allowed": checker_allowed,
                        "monitor_allowed": monitor_allowed,
                        "unsafe_reference_event": unsafe,
                        "unsafe_accept": unsafe and monitor_allowed,
                        "decision_match": checker_allowed == monitor_allowed,
                        "monitor_reason": str(monitor_decision["reason"]),
                        "monitor_rule_id": str(monitor_decision.get("rule_id") or ""),
                    }
                )
    return rows


class VariantMonitor:
    """Stateful interpreter for full and intentionally weakened policies."""

    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy
        self.rules = [rule for rule in policy.get("rules", []) if isinstance(rule, dict)]
        labels = policy.get("context_labels", {})
        self.labels = labels if isinstance(labels, dict) else {}
        self.invocations: dict[str, int] = {}

    def authorize(self, event: dict[str, Any]) -> dict[str, Any]:
        rejection_reasons = []
        for rule in self.rules:
            reason = self._rule_rejects(rule, event)
            if reason is None:
                rule_id = str(rule.get("rule_id", "<rule>"))
                self.invocations[rule_id] = self.invocations.get(rule_id, 0) + 1
                return {
                    "allowed": True,
                    "reason": "lowered policy rule matched",
                    "rule_id": rule_id,
                }
            rejection_reasons.append(f"{rule.get('rule_id', '<rule>')}: {reason}")
        if self.policy.get("default_action") == "allow":
            return {"allowed": True, "reason": "default allow unmatched", "rule_id": None}
        return {
            "allowed": False,
            "reason": "; ".join(rejection_reasons) if rejection_reasons else "no rules",
            "rule_id": None,
        }

    def _rule_rejects(self, rule: dict[str, Any], event: dict[str, Any]) -> str | None:
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
            if not _label_allows(self.labels.get(source, {}), mode, decision):
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
            used = self.invocations.get(rule_id, 0)
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


def _summary(
    *,
    run_id: str,
    policy: dict[str, Any],
    challenges: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    digests: list[dict[str, Any]],
) -> dict[str, Any]:
    variant_rows = _variant_rows(rows)
    unsafe_by_variant = {
        row["variant"]: int(row["unsafe_accepts"])
        for row in variant_rows
    }
    full_rows = [row for row in rows if row["variant"] == "full_policy"]
    weakened_rows = [row for row in rows if row["variant"] != "full_policy"]
    rules = [rule for rule in policy.get("rules", []) if isinstance(rule, dict)]
    return {
        "run_id": run_id,
        "analysis": "ActPlane-style lowered-policy contract audit",
        "challenge_sequences": len(challenges),
        "challenge_events": len(_all_challenge_events(challenges)),
        "variants": len(variant_rows),
        "full_policy_unsafe_accepts": unsafe_by_variant.get("full_policy", 0),
        "full_policy_decision_mismatches": sum(
            1 for row in full_rows if not row["decision_match"]
        ),
        "weakened_variant_unsafe_accepts": sum(
            1 for row in weakened_rows if row["unsafe_accept"]
        ),
        "unsafe_accepts_by_variant": unsafe_by_variant,
        "contract": {
            "default_action": policy.get("default_action"),
            "rules": len(rules),
            "rule_classes": sorted({str(rule.get("class", "")) for rule in rules}),
            "rules_with_holder_binding": sum(1 for rule in rules if rule.get("holder") is not None),
            "rules_with_argument_constraints": sum(
                1 for rule in rules if bool(rule.get("arg_constraints"))
            ),
            "rules_with_control_policy": sum(
                1 for rule in rules if bool(rule.get("control_may_depend_on"))
            ),
            "rules_with_data_policy": sum(
                1 for rule in rules if bool(rule.get("data_may_depend_on"))
            ),
            "stateful_budget_rules": sum(
                1
                for rule in rules
                if isinstance(rule.get("budget"), dict) and "invocations" in rule["budget"]
            ),
        },
        "input_digests": digests,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "notes": [
            "This run is read-only: it does not run models, execute tools, or sync datasets.",
            "The full policy is the existing R218 lowering artifact; weakened variants remove one contract field family at a time.",
            "The audit supports a local lowering-contract claim, not production ActPlane/kernel integration.",
        ],
    }


def _variant_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants = sorted({str(row["variant"]) for row in rows})
    out = []
    for variant in variants:
        variant_rows = [row for row in rows if row["variant"] == variant]
        out.append(
            {
                "variant": variant,
                "unsafe_accepts": sum(1 for row in variant_rows if row["unsafe_accept"]),
                "decision_mismatches": sum(1 for row in variant_rows if not row["decision_match"]),
                "monitor_allowed": sum(1 for row in variant_rows if row["monitor_allowed"]),
                "checker_allowed": sum(1 for row in variant_rows if row["checker_allowed"]),
            }
        )
    return out


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _file_digest(name: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "input_name": name,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
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
