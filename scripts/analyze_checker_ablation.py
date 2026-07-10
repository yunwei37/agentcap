"""Ablate deterministic checking against no-provenance lease acceptance.

The C3 claim says that LLM-assisted lease synthesis must remain outside the TCB:
candidate leases are useful proposals, but a deterministic checker must validate
argument constraints and context provenance. This script turns existing
benchmark-derived IntentCap traces into a small ablation corpus.

For each event, it compares:

* IntentCap checker: full lease + label/provenance validation.
* Object-only policy: accept if any lease exposes the same op/object.
* Lease-constraints/no-provenance policy: accept if a saved lease's declared
  op/object/argument constraints match, but ignore label and control/data
  provenance checks. Saved leases may be event-scoped in benchmark traces.
* Full-event-args/no-provenance policy: synthesize a candidate lease from the
  event's visible op/object/args and accept it while ignoring label and
  control/data provenance checks.

The last policy models a risky "LLM proposed a complete-looking lease, trust it"
baseline. Any event it accepts while the checker denies is an invalid proposal
rejected only because deterministic provenance/label validation remains in the
trusted path.
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

from intentcap.checker import _lease_matches_event, check_event


DEFAULT_TRACE_PATHS = (
    Path("examples/local_pdf_wrong_sink.json"),
    Path("results/agentdojo/R011/intentcap_trace.json"),
    Path("results/mcptox/R007/intentcap_trace.json"),
    Path("results/online/R010/export/intentcap_trace.json"),
    Path("results/tau2/R024/intentcap_traces.json"),
)

EVENT_ROW_FIELDS = [
    "source",
    "source_path",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "checker_allowed",
    "checker_reason",
    "checker_lease_id",
    "object_only_accept",
    "lease_constraints_no_provenance_accept",
    "full_event_args_no_provenance_accept",
    "object_only_false_accept",
    "lease_constraints_no_provenance_false_accept",
    "full_event_args_no_provenance_false_accept",
]

SOURCE_ROW_FIELDS = [
    "source",
    "source_path",
    "events",
    "leases",
    "labels",
    "checker_allowed",
    "checker_denied",
    "object_only_accept",
    "object_only_false_accept",
    "lease_constraints_no_provenance_accept",
    "lease_constraints_no_provenance_false_accept",
    "full_event_args_no_provenance_accept",
    "full_event_args_no_provenance_false_accept",
]

INPUT_DIGEST_FIELDS = [
    "path",
    "sha256",
    "bytes",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze IntentCap checker ablations")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--trace",
        dest="traces",
        action="append",
        type=Path,
        default=None,
        help="IntentCap trace JSON path; may be repeated. Defaults to the R025 corpus.",
    )
    args = parser.parse_args()

    trace_paths = tuple(args.traces) if args.traces else DEFAULT_TRACE_PATHS
    result = analyze(trace_paths)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "checker_ablation_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "event_ablation.csv", result["event_rows"], EVENT_ROW_FIELDS)
    _write_rows(args.output_dir / "source_ablation.csv", result["source_rows"], SOURCE_ROW_FIELDS)
    _write_rows(args.output_dir / "input_trace_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(trace_paths: tuple[Path, ...]) -> dict[str, Any]:
    event_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []

    for path in trace_paths:
        for source_name, trace in _load_trace_units(path):
            source_event_rows = _analyze_trace(
                source=source_name,
                source_path=path,
                trace=trace,
            )
            event_rows.extend(source_event_rows)
            source_rows.append(_source_row(source_name, path, trace, source_event_rows))

    input_digests = [_file_digest(path) for path in trace_paths]
    summary = _summary(trace_paths, event_rows, source_rows, input_digests)
    return {
        "summary": summary,
        "event_rows": event_rows,
        "source_rows": source_rows,
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
    rows: list[dict[str, Any]] = []
    exposed_op_objects = {
        (lease.get("op"), lease.get("object"))
        for lease in leases
    }
    for event in trace.get("events", []):
        verdict = check_event(event, leases, labels)
        checker_allowed = bool(verdict["allowed"])
        object_only_accept = (event.get("op"), event.get("object")) in exposed_op_objects
        lease_constraints_no_provenance_accept = any(
            _lease_matches_event(lease, event)
            for lease in leases
        )
        full_event_args_no_provenance_accept = _full_event_args_candidate_matches(event)
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
                "checker_lease_id": verdict.get("lease_id") or "",
                "object_only_accept": object_only_accept,
                "lease_constraints_no_provenance_accept": lease_constraints_no_provenance_accept,
                "full_event_args_no_provenance_accept": full_event_args_no_provenance_accept,
                "object_only_false_accept": object_only_accept and not checker_allowed,
                "lease_constraints_no_provenance_false_accept": (
                    lease_constraints_no_provenance_accept and not checker_allowed
                ),
                "full_event_args_no_provenance_false_accept": (
                    full_event_args_no_provenance_accept and not checker_allowed
                ),
            }
        )
    return rows


def _full_event_args_candidate_matches(event: dict[str, Any]) -> bool:
    event_args = event.get("args", {})
    if not isinstance(event_args, dict):
        event_args = {}
    candidate = {
        "op": event.get("op"),
        "object": event.get("object"),
        "args": {
            key: {"equals": value}
            for key, value in event_args.items()
        },
    }
    return _lease_matches_event(candidate, event)


def _source_row(
    source: str,
    source_path: Path,
    trace: dict[str, Any],
    event_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    checker_allowed = sum(1 for row in event_rows if row["checker_allowed"])
    object_only_accept = sum(1 for row in event_rows if row["object_only_accept"])
    object_only_false_accept = sum(1 for row in event_rows if row["object_only_false_accept"])
    lease_constraints_accept = sum(
        1 for row in event_rows if row["lease_constraints_no_provenance_accept"]
    )
    lease_constraints_false_accept = sum(
        1 for row in event_rows if row["lease_constraints_no_provenance_false_accept"]
    )
    full_args_accept = sum(1 for row in event_rows if row["full_event_args_no_provenance_accept"])
    full_args_false_accept = sum(
        1 for row in event_rows if row["full_event_args_no_provenance_false_accept"]
    )
    return {
        "source": source,
        "source_path": str(source_path),
        "events": len(event_rows),
        "leases": len(trace.get("leases", [])),
        "labels": len(trace.get("labels", {})),
        "checker_allowed": checker_allowed,
        "checker_denied": len(event_rows) - checker_allowed,
        "object_only_accept": object_only_accept,
        "object_only_false_accept": object_only_false_accept,
        "lease_constraints_no_provenance_accept": lease_constraints_accept,
        "lease_constraints_no_provenance_false_accept": lease_constraints_false_accept,
        "full_event_args_no_provenance_accept": full_args_accept,
        "full_event_args_no_provenance_false_accept": full_args_false_accept,
    }


def _summary(
    trace_paths: tuple[Path, ...],
    event_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    mode_counts = Counter(row["mode"] for row in event_rows)
    denied_mode_counts = Counter(row["mode"] for row in event_rows if not row["checker_allowed"])
    lease_constraints_false_accept_mode_counts = Counter(
        row["mode"]
        for row in event_rows
        if row["lease_constraints_no_provenance_false_accept"]
    )
    full_args_false_accept_mode_counts = Counter(
        row["mode"]
        for row in event_rows
        if row["full_event_args_no_provenance_false_accept"]
    )
    checker_allowed = sum(1 for row in event_rows if row["checker_allowed"])
    object_only_accept = sum(1 for row in event_rows if row["object_only_accept"])
    object_only_false_accept = sum(1 for row in event_rows if row["object_only_false_accept"])
    lease_constraints_accept = sum(
        1 for row in event_rows if row["lease_constraints_no_provenance_accept"]
    )
    lease_constraints_false_accept = sum(
        1 for row in event_rows if row["lease_constraints_no_provenance_false_accept"]
    )
    full_args_accept = sum(1 for row in event_rows if row["full_event_args_no_provenance_accept"])
    full_args_false_accept = sum(
        1 for row in event_rows if row["full_event_args_no_provenance_false_accept"]
    )
    return {
        "benchmark": "IntentCap checker ablation corpus",
        "trace_paths": [str(path) for path in trace_paths],
        "sources": len(source_rows),
        "events": len(event_rows),
        "checker_allowed": checker_allowed,
        "checker_denied": len(event_rows) - checker_allowed,
        "object_only_accept": object_only_accept,
        "object_only_false_accept": object_only_false_accept,
        "lease_constraints_no_provenance_accept": lease_constraints_accept,
        "lease_constraints_no_provenance_false_accept": lease_constraints_false_accept,
        "full_event_args_no_provenance_accept": full_args_accept,
        "full_event_args_no_provenance_false_accept": full_args_false_accept,
        "valid_events_preserved_by_checker": checker_allowed,
        "invalid_lease_constraint_proposals_rejected": lease_constraints_false_accept,
        "invalid_full_event_arg_proposals_rejected": full_args_false_accept,
        "invalid_object_only_proposals_rejected": object_only_false_accept,
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "input_trace_digests": input_digests,
        "mode_counts": dict(sorted(mode_counts.items())),
        "checker_denied_by_mode": dict(sorted(denied_mode_counts.items())),
        "lease_constraints_no_provenance_false_accept_by_mode": dict(
            sorted(lease_constraints_false_accept_mode_counts.items())
        ),
        "full_event_args_no_provenance_false_accept_by_mode": dict(
            sorted(full_args_false_accept_mode_counts.items())
        ),
        "notes": [
            "The checker column is the current IntentCap deterministic checker over saved traces.",
            "Object-only accept ignores argument constraints and provenance labels.",
            "Lease-constraints/no-provenance accept uses saved lease op/object/argument constraints but ignores context labels and control/data provenance.",
            "Full-event-args/no-provenance accept synthesizes a candidate lease from each event's visible op/object/args and ignores context labels and control/data provenance.",
            "False accepts are events accepted by an ablated policy and denied by the checker.",
            "tau2 R024 traces contribute valid reference-action acceptance, not adversarial denials.",
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
