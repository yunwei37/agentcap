"""Label saved IntentCap traces with closest-prior-work-style baselines.

This script is intentionally a trace-level partial baseline, not a reproduction
of AuthGraph, PACT, AIRGuard, FIDES, RTBAS, NeuroTaint, Progent, PCAS,
AgentSpec, AgentGuard, or AgentBound artifacts.

It answers a narrower reviewer-facing question over saved IntentCap traces:
when the checker denies an event, would simpler predicates inspired by the
closest baselines also reject it, or is the denial residual evidence for
IntentCap's proof-carrying lease semantics?
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.checker import _lease_matches_event, check_trace


DEFAULT_TRACE_PATHS = (
    Path("examples/local_pdf_wrong_sink.json"),
    Path("results/agentdojo/R011/intentcap_trace.json"),
    Path("results/mcptox/R007/intentcap_trace.json"),
    Path("results/online/R010/export/intentcap_trace.json"),
    Path("results/tau2/R024/intentcap_traces.json"),
)

AUTHORITY_MODES = {
    "authorize",
    "sink_select",
    "tool_select",
    "delegate",
    "policy_update",
    "execute",
}

EVENT_FIELDS = [
    "source",
    "source_path",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "checker_allowed",
    "checker_reason",
    "protected_decision",
    "control_trust",
    "control_untrusted",
    "data_untrusted",
    "policy_dsl_accept",
    "static_tool_acl_accept",
    "authgraph_pact_airguard_accept",
    "ifc_taint_accept",
    "closest_all_accept",
    "policy_dsl_false_accept",
    "static_tool_acl_false_accept",
    "authgraph_pact_airguard_false_accept",
    "ifc_taint_false_accept",
    "residual_after_closest_baselines",
    "explained_by_authgraph_pact_airguard",
    "explained_by_ifc_taint",
    "explained_by_policy_dsl",
]

SOURCE_FIELDS = [
    "source",
    "source_path",
    "events",
    "checker_allowed",
    "checker_denied",
    "denied_explained_by_authgraph_pact_airguard",
    "denied_explained_by_ifc_taint",
    "denied_explained_by_policy_dsl",
    "denied_residual_after_closest_baselines",
    "policy_dsl_false_accept",
    "static_tool_acl_false_accept",
    "authgraph_pact_airguard_false_accept",
    "ifc_taint_false_accept",
]

BASELINE_FIELDS = [
    "baseline",
    "accept",
    "block",
    "false_accept",
    "false_reject",
    "denied_explained",
    "interpretation",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze closest-baseline trace labelers")
    parser.add_argument("--run-id", default="R082")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--trace",
        dest="traces",
        action="append",
        type=Path,
        default=None,
        help="IntentCap trace JSON path; may be repeated. Defaults to saved R011/R007/R010/R024 traces.",
    )
    args = parser.parse_args()

    trace_paths = tuple(args.traces) if args.traces else DEFAULT_TRACE_PATHS
    result = analyze(run_id=args.run_id, trace_paths=trace_paths)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "closest_baseline_labeler_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "event_baseline_labels.csv", result["event_rows"], EVENT_FIELDS)
    _write_rows(args.output_dir / "source_baseline_summary.csv", result["source_rows"], SOURCE_FIELDS)
    _write_rows(args.output_dir / "baseline_summary.csv", result["baseline_rows"], BASELINE_FIELDS)
    _write_rows(args.output_dir / "input_trace_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, run_id: str, trace_paths: tuple[Path, ...]) -> dict[str, Any]:
    event_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for path in trace_paths:
        for source_name, trace in _load_trace_units(path):
            rows = _analyze_trace(source=source_name, source_path=path, trace=trace)
            event_rows.extend(rows)
            source_rows.append(_source_row(source_name, path, rows))

    baseline_rows = _baseline_rows(event_rows)
    input_digests = [_file_digest(path) for path in trace_paths]
    summary = _summary(
        run_id=run_id,
        trace_paths=trace_paths,
        event_rows=event_rows,
        source_rows=source_rows,
        baseline_rows=baseline_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "event_rows": event_rows,
        "source_rows": source_rows,
        "baseline_rows": baseline_rows,
        "input_digests": input_digests,
    }


def _load_trace_units(path: Path) -> list[tuple[str, dict[str, Any]]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        units: list[tuple[str, dict[str, Any]]] = []
        for index, item in enumerate(payload):
            trace = item.get("trace", item)
            source = _source_name(path, item, index)
            units.append((source, trace))
        return units
    return [(_source_name(path, payload, 0), payload)]


def _source_name(path: Path, item: dict[str, Any], index: int) -> str:
    if "domain" in item and "task_id" in item:
        return f"{path.parent.name}:{item['domain']}:{item['task_id']}"
    intent = item.get("intent", {}) if isinstance(item, dict) else {}
    if "id" in intent:
        return f"{path.parent.name}:{intent['id']}"
    return f"{path.parent.name}:{path.stem}:{index}"


def _analyze_trace(*, source: str, source_path: Path, trace: dict[str, Any]) -> list[dict[str, Any]]:
    leases = trace.get("leases", [])
    labels = trace.get("labels", {})
    exposed_op_objects = {(lease.get("op"), lease.get("object")) for lease in leases}
    verdicts = check_trace(trace)
    rows: list[dict[str, Any]] = []

    for index, event in enumerate(trace.get("events", [])):
        verdict = verdicts[index]
        checker_allowed = bool(verdict["allowed"])
        protected = _is_protected_decision(event)
        control_sources = [str(source) for source in event.get("control_provenance", [])]
        data_sources = [str(source) for source in event.get("data_provenance", [])]
        control_trust = _provenance_trust(control_sources)
        control_untrusted = control_trust == "untrusted"
        data_untrusted = any(_source_is_untrusted(source) for source in data_sources)

        policy_dsl_accept = any(_lease_matches_event(lease, event) for lease in leases)
        static_tool_acl_accept = (event.get("op"), event.get("object")) in exposed_op_objects
        authgraph_pact_airguard_accept = _authgraph_pact_airguard_accept(
            protected=protected,
            control_untrusted=control_untrusted,
        )
        ifc_taint_accept = _ifc_taint_accept(
            event=event,
            protected=protected,
            control_untrusted=control_untrusted,
            data_untrusted=data_untrusted,
        )
        closest_all_accept = (
            authgraph_pact_airguard_accept
            and ifc_taint_accept
            and policy_dsl_accept
        )
        checker_denied = not checker_allowed

        rows.append(
            {
                "source": source,
                "source_path": str(source_path),
                "event_id": str(event.get("id", "")),
                "op": str(event.get("op", "")),
                "object": str(event.get("object", "")),
                "mode": str(event.get("mode", "")),
                "decision": str(event.get("decision", "")),
                "checker_allowed": checker_allowed,
                "checker_reason": str(verdict["reason"]),
                "protected_decision": protected,
                "control_trust": control_trust,
                "control_untrusted": control_untrusted,
                "data_untrusted": data_untrusted,
                "policy_dsl_accept": policy_dsl_accept,
                "static_tool_acl_accept": static_tool_acl_accept,
                "authgraph_pact_airguard_accept": authgraph_pact_airguard_accept,
                "ifc_taint_accept": ifc_taint_accept,
                "closest_all_accept": closest_all_accept,
                "policy_dsl_false_accept": checker_denied and policy_dsl_accept,
                "static_tool_acl_false_accept": checker_denied and static_tool_acl_accept,
                "authgraph_pact_airguard_false_accept": checker_denied and authgraph_pact_airguard_accept,
                "ifc_taint_false_accept": checker_denied and ifc_taint_accept,
                "residual_after_closest_baselines": checker_denied and closest_all_accept,
                "explained_by_authgraph_pact_airguard": checker_denied and not authgraph_pact_airguard_accept,
                "explained_by_ifc_taint": checker_denied and not ifc_taint_accept,
                "explained_by_policy_dsl": checker_denied and not policy_dsl_accept,
            }
        )
    return rows


def _is_protected_decision(event: dict[str, Any]) -> bool:
    mode = str(event.get("mode", ""))
    if mode in AUTHORITY_MODES:
        return True
    decision = str(event.get("decision", ""))
    return any(token in decision for token in ("sink", "authority", "policy", "delegate"))


def _authgraph_pact_airguard_accept(*, protected: bool, control_untrusted: bool) -> bool:
    # Models the closest-family insight: data may inform, but untrusted control
    # provenance may not authorize a protected decision or authority-bearing arg.
    return not (protected and control_untrusted)


def _ifc_taint_accept(
    *,
    event: dict[str, Any],
    protected: bool,
    control_untrusted: bool,
    data_untrusted: bool,
) -> bool:
    if protected and control_untrusted:
        return False
    mode = str(event.get("mode", ""))
    if mode in {"authorize", "sink_select", "delegate", "policy_update"} and data_untrusted:
        return False
    return True


def _provenance_trust(sources: list[str]) -> str:
    if not sources:
        return "unknown"
    if any(_source_is_untrusted(source) for source in sources):
        return "untrusted"
    if all(_source_is_trusted(source) for source in sources):
        return "trusted"
    return "unknown"


def _source_is_trusted(source: str) -> bool:
    normalized = source.lower()
    trusted_markers = (
        "trusted",
        "user_intent",
        "user_request",
        "admin_policy",
        "signed",
        "intent_cert",
    )
    return any(marker in normalized for marker in trusted_markers)


def _source_is_untrusted(source: str) -> bool:
    normalized = source.lower()
    untrusted_markers = (
        "untrusted",
        "injection",
        "tool_response",
        "tool_description",
        "mcptox",
        "uploaded",
        "webpage",
        "poison",
        "attacker",
        "mcp_tool_result",
        "unsigned",
    )
    return any(marker in normalized for marker in untrusted_markers)


def _source_row(source: str, source_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    checker_denied = sum(1 for row in rows if not row["checker_allowed"])
    return {
        "source": source,
        "source_path": str(source_path),
        "events": len(rows),
        "checker_allowed": sum(1 for row in rows if row["checker_allowed"]),
        "checker_denied": checker_denied,
        "denied_explained_by_authgraph_pact_airguard": sum(
            1 for row in rows if row["explained_by_authgraph_pact_airguard"]
        ),
        "denied_explained_by_ifc_taint": sum(
            1 for row in rows if row["explained_by_ifc_taint"]
        ),
        "denied_explained_by_policy_dsl": sum(
            1 for row in rows if row["explained_by_policy_dsl"]
        ),
        "denied_residual_after_closest_baselines": sum(
            1 for row in rows if row["residual_after_closest_baselines"]
        ),
        "policy_dsl_false_accept": sum(1 for row in rows if row["policy_dsl_false_accept"]),
        "static_tool_acl_false_accept": sum(1 for row in rows if row["static_tool_acl_false_accept"]),
        "authgraph_pact_airguard_false_accept": sum(
            1 for row in rows if row["authgraph_pact_airguard_false_accept"]
        ),
        "ifc_taint_false_accept": sum(1 for row in rows if row["ifc_taint_false_accept"]),
    }


def _baseline_rows(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    configs = [
        (
            "authgraph_pact_airguard_style",
            "Blocks protected decisions whose control provenance is untrusted.",
            "authgraph_pact_airguard_accept",
            "explained_by_authgraph_pact_airguard",
        ),
        (
            "ifc_taint_style",
            "Blocks untrusted control over protected decisions and untrusted data into sensitive authority/sink modes.",
            "ifc_taint_accept",
            "explained_by_ifc_taint",
        ),
        (
            "policy_dsl_access_control_style",
            "Matches saved operation/object/argument constraints but ignores provenance and influence modes.",
            "policy_dsl_accept",
            "explained_by_policy_dsl",
        ),
        (
            "static_tool_acl_style",
            "Matches only exposed operation/object pairs.",
            "static_tool_acl_accept",
            "",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for baseline, interpretation, accept_key, explained_key in configs:
        accept = sum(1 for row in event_rows if row[accept_key])
        false_accept = sum(1 for row in event_rows if row[accept_key] and not row["checker_allowed"])
        false_reject = sum(1 for row in event_rows if not row[accept_key] and row["checker_allowed"])
        denied_explained = sum(1 for row in event_rows if explained_key and row[explained_key])
        rows.append(
            {
                "baseline": baseline,
                "accept": accept,
                "block": len(event_rows) - accept,
                "false_accept": false_accept,
                "false_reject": false_reject,
                "denied_explained": denied_explained,
                "interpretation": interpretation,
            }
        )
    return rows


def _summary(
    *,
    run_id: str,
    trace_paths: tuple[Path, ...],
    event_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    checker_allowed = sum(1 for row in event_rows if row["checker_allowed"])
    checker_denied = len(event_rows) - checker_allowed
    residual = sum(1 for row in event_rows if row["residual_after_closest_baselines"])
    mode_counts = Counter(row["mode"] for row in event_rows)
    denied_mode_counts = Counter(row["mode"] for row in event_rows if not row["checker_allowed"])
    residual_mode_counts = Counter(
        row["mode"] for row in event_rows if row["residual_after_closest_baselines"]
    )
    explained_any = sum(
        1
        for row in event_rows
        if not row["checker_allowed"]
        and (
            row["explained_by_authgraph_pact_airguard"]
            or row["explained_by_ifc_taint"]
            or row["explained_by_policy_dsl"]
        )
    )
    return {
        "run_id": run_id,
        "trace_paths": [str(path) for path in trace_paths],
        "sources": len(source_rows),
        "events": len(event_rows),
        "checker_allowed": checker_allowed,
        "checker_denied": checker_denied,
        "denied_explained_by_any_closest_baseline": explained_any,
        "denied_residual_after_closest_baselines": residual,
        "residual_rate_among_checker_denied": residual / checker_denied if checker_denied else 0.0,
        "mode_counts": dict(sorted(mode_counts.items())),
        "checker_denied_by_mode": dict(sorted(denied_mode_counts.items())),
        "residual_after_closest_baselines_by_mode": dict(sorted(residual_mode_counts.items())),
        "baseline_rows": baseline_rows,
        "input_trace_digests": input_digests,
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "notes": [
            "This is a trace-level partial baseline labeler, not artifact reproduction.",
            "AuthGraph/PACT/AIRGuard-style accepts protected decisions only when control provenance is not untrusted.",
            "IFC/taint-style additionally rejects untrusted data flowing into authority, sink, delegation, or policy modes.",
            "Policy-DSL/access-control style uses saved operation/object/argument constraints but ignores provenance labels.",
            "Residual events are checker-denied events accepted by the provenance-authority, IFC/taint, and policy-DSL labelers.",
        ],
    }


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": _sha256(data),
        "bytes": len(data),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


if __name__ == "__main__":
    raise SystemExit(main())
