"""Audit proof obligations across local IntentCap adapter boundaries.

This script is read-only. It consumes existing E4 boundary records and the
local traces that generated them, then checks whether each adapter-submitted
event has an attributable proof shape and whether each denial maps to a modeled
proof-obligation class.

The result is not a formal proof of adapter correctness and not production
ActPlane/kernel enforcement. It is an audit of the local pre-side-effect,
pre-placement, and pre-handoff adapter contract used in the paper.
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
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("results/eval/R240ADAPTERPROOF")
DEFAULT_INPUTS = {
    "env_trace": Path("examples/env_adapter_side_effect_suite.json"),
    "workflow_trace": Path("examples/residual_workflow_policy_suite.json"),
    "skill_trace": Path("examples/skill_instruction_boundary_suite.json"),
    "env_backend_rows": Path("results/eval/R211ENVBACKEND/env_backend_rows.csv"),
    "env_llm_rows": Path("results/eval/R212ENVLLM/env_llm_backend_rows.csv"),
    "actplane_rows": Path("results/eval/R218ACTLOWER/actplane_lowering_rows.csv"),
    "boundary_rows": Path("results/eval/R222BOUNDARY/boundary_gateway_records.csv"),
    "skill_rows": Path("results/eval/R224SKILLBOUNDARY/skill_instruction_boundary_records.csv"),
}

ROW_FIELDS = [
    "boundary",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "allowed",
    "effect_applied",
    "unsafe_reference_event",
    "submitted_authority_inputs",
    "proof_obligations",
    "denial_class",
    "proof_complete_for_verdict",
    "blockpoint",
    "reason",
]

SUMMARY_ROW_FIELDS = ["name", "count"]
INPUT_DIGEST_FIELDS = ["input_name", "path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze adapter proof completeness")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default="R240ADAPTERPROOF")
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
    traces = {
        "env": _read_json(inputs["env_trace"]),
        "workflow": _read_json(inputs["workflow_trace"]),
        "skill": _read_json(inputs["skill_trace"]),
    }
    rows = []
    rows.extend(_env_backend_rows(_read_rows(inputs["env_backend_rows"]), traces["env"]))
    rows.extend(_env_llm_rows(_read_rows(inputs["env_llm_rows"]), traces["env"]))
    rows.extend(_actplane_rows(_read_rows(inputs["actplane_rows"]), traces["env"]))
    rows.extend(
        _boundary_rows(_read_rows(inputs["boundary_rows"]), traces["env"], traces["workflow"])
    )
    rows.extend(_skill_rows(_read_rows(inputs["skill_rows"]), traces["skill"]))

    digests = [_file_digest(name, path) for name, path in sorted(inputs.items())]
    summary = _summary(rows=rows, digests=digests, run_id=run_id)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "adapter_proof_completeness.csv", rows, ROW_FIELDS)
    _write_counter_rows(output_dir / "denial_classes.csv", Counter(row["denial_class"] for row in rows))
    _write_counter_rows(
        output_dir / "authority_input_classes.csv",
        Counter(
            proof_class
            for row in rows
            for proof_class in _split_set(row["submitted_authority_inputs"])
        ),
    )
    _write_rows(output_dir / "input_digests.csv", digests, INPUT_DIGEST_FIELDS)
    (output_dir / "adapter_proof_completeness_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


def _env_backend_rows(csv_rows: list[dict[str, str]], trace: dict[str, Any]) -> list[dict[str, Any]]:
    events = _events_by_id(trace)
    leases = trace.get("leases", [])
    out = []
    for row in csv_rows:
        if row["backend"] != "intentcap":
            continue
        event = events[row["event_id"]]
        out.append(
            _audit_row(
                boundary="local_env_side_effect",
                event=event,
                leases=leases,
                allowed=_bool(row["allowed"]),
                effect_applied=_bool(row["executed"]),
                unsafe_reference_event=_bool(row["unsafe_reference_event"]),
                reason=row["reason"],
                blockpoint="before local side-effect handler",
            )
        )
    return out


def _env_llm_rows(csv_rows: list[dict[str, str]], trace: dict[str, Any]) -> list[dict[str, Any]]:
    events = _events_by_id(trace)
    leases = trace.get("leases", [])
    out = []
    for row in csv_rows:
        if row["model_action"] != "call":
            continue
        event = events[row["event_id"]]
        out.append(
            _audit_row(
                boundary="local_qwen_env_proposer",
                event=event,
                leases=leases,
                allowed=_bool(row["intentcap_allowed"]),
                effect_applied=_bool(row["intentcap_executed"]),
                unsafe_reference_event=_bool(row["llm_only_unsafe_call"]),
                reason=row["intentcap_reason"],
                blockpoint="before model-proposed side-effect handler",
            )
        )
    return out


def _actplane_rows(csv_rows: list[dict[str, str]], trace: dict[str, Any]) -> list[dict[str, Any]]:
    events = _events_by_id(trace)
    leases = trace.get("leases", [])
    out = []
    for row in csv_rows:
        event = events[row["event_id"]]
        out.append(
            _audit_row(
                boundary="os_monitor_style_lowering",
                event=event,
                leases=leases,
                allowed=_bool(row["checker_allowed"]),
                effect_applied=_bool(row["monitor_allowed"]),
                unsafe_reference_event=_bool(row["unsafe_reference_event"]),
                reason=row["checker_reason"],
                blockpoint="monitor replay before env side effect",
                extra_obligations=["monitor_lowering"],
            )
        )
    return out


def _boundary_rows(
    csv_rows: list[dict[str, str]],
    env_trace: dict[str, Any],
    workflow_trace: dict[str, Any],
) -> list[dict[str, Any]]:
    events = {**_events_by_id(env_trace), **_events_by_id(workflow_trace)}
    events["calendar_subagent_summary_only"] = {
        "id": "calendar_subagent_summary_only",
        "op": "subagent.spawn",
        "object": "calendar_summary_subagent",
        "args": {
            "role": "calendar_digest",
            "capabilities": [
                {"op": "ctx.use", "object": "calendar_events", "mode": "summarize"}
            ],
        },
        "decision": "calendar_subagent.capabilities",
        "mode": "delegate",
        "control_provenance": ["trusted_calendar_policy"],
        "data_provenance": ["trusted_meeting_summary"],
    }
    leases = [*env_trace.get("leases", []), *workflow_trace.get("leases", [])]
    out = []
    for row in csv_rows:
        event = events[row["event_id"]]
        boundary = "context_placement" if row["boundary"] == "context" else "delegation_handoff"
        blockpoint = (
            "before prompt-section write"
            if boundary == "context_placement"
            else "before subagent capability handoff"
        )
        out.append(
            _audit_row(
                boundary=boundary,
                event=event,
                leases=leases,
                allowed=_bool(row["allowed"]),
                effect_applied=_bool(row["effect_applied"]),
                unsafe_reference_event=not _bool(row["allowed"]) and row["event_id"]
                in {"script_output_promotes_instruction", "calendar_subagent_overdelegates_email"},
                reason=row["reason"],
                blockpoint=blockpoint,
            )
        )
    return out


def _skill_rows(csv_rows: list[dict[str, str]], trace: dict[str, Any]) -> list[dict[str, Any]]:
    events = _events_by_id(trace)
    leases = trace.get("leases", [])
    out = []
    for row in csv_rows:
        event = events[row["event_id"]]
        out.append(
            _audit_row(
                boundary="skill_instruction_placement",
                event=event,
                leases=leases,
                allowed=_bool(row["checker_allowed"]),
                effect_applied=_bool(row["effect_applied"]),
                unsafe_reference_event=_bool(row["unsafe_probe"]),
                reason=row["reason"],
                blockpoint="before trusted instruction-section placement",
            )
        )
    return out


def _audit_row(
    *,
    boundary: str,
    event: dict[str, Any],
    leases: list[dict[str, Any]],
    allowed: bool,
    effect_applied: bool,
    unsafe_reference_event: bool,
    reason: str,
    blockpoint: str,
    extra_obligations: list[str] | None = None,
) -> dict[str, Any]:
    denial_class = _denial_class(reason, allowed)
    obligations = _proof_obligations(event, leases, reason)
    if extra_obligations:
        obligations.extend(extra_obligations)
    proof_inputs = _authority_inputs(event)
    proof_complete = allowed or denial_class != "unclassified_denial"
    return {
        "boundary": boundary,
        "event_id": str(event.get("id", "")),
        "op": str(event.get("op", "")),
        "object": str(event.get("object", "")),
        "mode": str(event.get("mode", "")),
        "decision": str(event.get("decision", "")),
        "allowed": allowed,
        "effect_applied": effect_applied,
        "unsafe_reference_event": unsafe_reference_event,
        "submitted_authority_inputs": _format_set(proof_inputs),
        "proof_obligations": _format_set(obligations),
        "denial_class": denial_class,
        "proof_complete_for_verdict": proof_complete,
        "blockpoint": blockpoint,
        "reason": reason,
    }


def _authority_inputs(event: dict[str, Any]) -> list[str]:
    classes = set()
    for source in _as_list(event.get("control_provenance", [])):
        classes.add(_source_class(str(source)))
    for source in _as_list(event.get("data_provenance", [])):
        classes.add(_source_class(str(source)))
    if event.get("op") in {"exec.run", "mcp.call", "fs.read", "fs.write", "net.connect"}:
        classes.add("tool_or_env_contract")
    return sorted(classes)


def _source_class(source: str) -> str:
    if source in {"trusted_user_intent", "trusted_repo_selection", "trusted_calendar_policy"}:
        return "agent"
    if source.startswith("signed_") or source == "unsigned_skill_text":
        return "instruction"
    if "tool_metadata" in source or source.endswith("_schema"):
        return "tool"
    return "env"


def _proof_obligations(event: dict[str, Any], leases: list[dict[str, Any]], reason: str) -> list[str]:
    obligations = {"operation_object_argument_contract"}
    if event.get("holder") is not None or _related_lease_has(leases, event, "holder"):
        obligations.add("holder_scope")
    if event.get("control_provenance"):
        obligations.add("control_provenance")
    if event.get("data_provenance"):
        obligations.add("data_provenance")
    if event.get("proof") or event.get("intent_provenance") or event.get("approvals"):
        obligations.add("intent_or_approval_proof")
    if _related_lease_has(leases, event, "intent") or "approval" in reason:
        obligations.add("intent_or_approval_proof")
    if _related_lease_has(leases, event, "temporal") or "temporal prerequisites" in reason:
        obligations.add("temporal_state")
    if _related_lease_has(leases, event, "budget") or "invocation budget" in reason:
        obligations.add("budget_consumption")
    if event.get("op") == "subagent.spawn":
        obligations.add("delegation_attenuation")
    return sorted(obligations)


def _related_lease_has(leases: list[dict[str, Any]], event: dict[str, Any], field: str) -> bool:
    for lease in leases:
        if lease.get("op") == event.get("op") and lease.get("object") == event.get("object"):
            if field in lease and lease.get(field) not in (None, {}, [], ""):
                return True
    return False


def _denial_class(reason: str, allowed: bool) -> str:
    if allowed:
        return "allowed"
    reason = reason or ""
    if "no matching lease" in reason:
        return "operation_object_argument_or_no_lease"
    if "argument" in reason or "object mismatch" in reason or "op mismatch" in reason:
        return "operation_object_argument"
    if "holder" in reason:
        return "holder_scope"
    if "control source" in reason or "lacks influence mode" in reason:
        return "control_provenance_or_influence"
    if "data source" in reason:
        return "data_provenance"
    if "temporal prerequisites" in reason:
        return "temporal_state"
    if "invocation budget" in reason:
        return "budget_consumption"
    if "missing required approval proof" in reason or "missing intent derivation proof" in reason:
        return "intent_or_approval_proof"
    if "delegated capability exceeds" in reason or "delegation" in reason:
        return "delegation_attenuation"
    return "unclassified_denial"


def _summary(rows: list[dict[str, Any]], digests: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    denied = [row for row in rows if not row["allowed"]]
    unsafe_effects = [
        row for row in rows if row["unsafe_reference_event"] and row["effect_applied"]
    ]
    denial_counter = Counter(row["denial_class"] for row in rows)
    boundary_counter = Counter(row["boundary"] for row in rows)
    obligation_counter = Counter(
        obligation
        for row in rows
        for obligation in _split_set(row["proof_obligations"])
    )
    authority_counter = Counter(
        proof_class
        for row in rows
        for proof_class in _split_set(row["submitted_authority_inputs"])
    )
    incomplete = [row for row in rows if not row["proof_complete_for_verdict"]]
    return {
        "run_id": run_id,
        "analysis": "adapter proof-completeness audit over existing E4 local records",
        "events": len(rows),
        "allowed": sum(1 for row in rows if row["allowed"]),
        "blocked": len(denied),
        "unsafe_effects_or_placements": len(unsafe_effects),
        "proof_complete_for_verdict": len(rows) - len(incomplete),
        "incomplete_or_unclassified_denials": len(incomplete),
        "denial_classes": dict(sorted(denial_counter.items())),
        "boundary_events": dict(sorted(boundary_counter.items())),
        "proof_obligation_counts": dict(sorted(obligation_counter.items())),
        "submitted_authority_input_counts": dict(sorted(authority_counter.items())),
        "pre_effect_or_pre_handoff_blockpoints": len(rows),
        "input_digests": digests,
        "project_head": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--short", "--branch"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_execution": True,
        "scope": (
            "Audits local adapter records and trace metadata only; it supports the "
            "adapter contract claim, not production prompt-builder, MCP broker, "
            "subagent runtime, or kernel/ActPlane mediation."
        ),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _events_by_id(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(event.get("id", "")): event for event in trace.get("events", [])}


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _format_set(values: list[str]) -> str:
    return "|".join(sorted({str(value) for value in values if value}))


def _split_set(value: Any) -> list[str]:
    return [part for part in str(value).split("|") if part]


def _file_digest(name: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "input_name": name,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_counter_rows(path: Path, counter: Counter[str]) -> None:
    rows = [{"name": name, "count": count} for name, count in sorted(counter.items())]
    _write_rows(path, rows, SUMMARY_ROW_FIELDS)


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return ""


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
