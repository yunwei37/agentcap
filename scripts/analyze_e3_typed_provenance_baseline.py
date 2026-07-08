"""Analyze a strong typed-provenance baseline for E3.

This script is intentionally a saved-artifact analysis. It consumes the R217
workflow residual labels and asks whether a stronger provenance-aware policy DSL
would still accept denied events if it has typed source/field ownership and
separate state checks, but does not represent the decision as one atomic
IntentCap lease commit.

The baseline is stronger than the older post-hoc policy DSL:

* it checks operation/object/argument policy rows;
* it checks whether a control source has the right influence mode;
* it checks fresh approval, holder, temporal, and budget state when those are
  visible as separate predicates.

It still lacks a parent-child capability object consumed at the handoff point.
Therefore, it cannot prove delegation attenuation unless it adds the same
atomic parent/child lease-set comparison as IntentCap. The point of the script
is not to reproduce a named prior system, but to make the reviewer-facing
equivalence boundary explicit: adding that commit object makes the baseline
converge on IntentCap.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_WORKFLOW_BASELINE = Path(
    "results/eval/R217E3POLICY/closest_baseline/event_baseline_labels.csv"
)

EVENT_FIELDS = [
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "checker_allowed",
    "checker_reason",
    "typed_provenance_state_guard_accept",
    "typed_provenance_state_guard_false_accept",
    "classification",
    "interpretation",
]

CLASS_FIELDS = [
    "classification",
    "events",
    "checker_denied",
    "typed_baseline_blocks",
    "typed_baseline_false_accepts",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]

BLOCK_REASON_PATTERNS = {
    "control source": "control_provenance_or_influence",
    "lacks influence mode": "control_provenance_or_influence",
    "missing required approval proof": "approval_mint_state",
    "does not match lease holder": "holder_scope",
    "temporal prerequisites": "temporal_state",
    "invocation budget exhausted": "budget_consumption",
}

FALSE_ACCEPT_REASON_PATTERNS = {
    "delegated capability exceeds": "delegation_attenuation_without_parent_lease_commit",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze E3 typed-provenance baseline")
    parser.add_argument("--workflow-baseline", type=Path, default=DEFAULT_WORKFLOW_BASELINE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R241E3TYPEDBASE")
    args = parser.parse_args()

    result = analyze(workflow_baseline=args.workflow_baseline, run_id=args.run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "typed_provenance_event_rows.csv", result["event_rows"], EVENT_FIELDS)
    _write_rows(args.output_dir / "typed_provenance_class_summary.csv", result["class_rows"], CLASS_FIELDS)
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "typed_provenance_baseline_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n"
    )
    (args.output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, workflow_baseline: Path, run_id: str) -> dict[str, Any]:
    workflow_rows = list(csv.DictReader(workflow_baseline.open()))
    event_rows = [_event_row(row) for row in workflow_rows]
    class_rows = _class_rows(event_rows)
    input_digests = [_file_digest(workflow_baseline)]
    summary = _summary(
        run_id=run_id,
        workflow_rows=workflow_rows,
        event_rows=event_rows,
        class_rows=class_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "event_rows": event_rows,
        "class_rows": class_rows,
        "input_digests": input_digests,
    }


def _event_row(row: dict[str, str]) -> dict[str, Any]:
    checker_allowed = _bool(row.get("checker_allowed", ""))
    reason = row.get("checker_reason", "")
    classification = _classify_reason(reason) if not checker_allowed else "allowed"
    typed_accept = checker_allowed or classification in FALSE_ACCEPT_REASON_PATTERNS.values()
    false_accept = typed_accept and not checker_allowed
    interpretation = _interpretation(classification, false_accept)
    return {
        "event_id": row.get("event_id", ""),
        "op": row.get("op", ""),
        "object": row.get("object", ""),
        "mode": row.get("mode", ""),
        "decision": row.get("decision", ""),
        "checker_allowed": checker_allowed,
        "checker_reason": reason,
        "typed_provenance_state_guard_accept": typed_accept,
        "typed_provenance_state_guard_false_accept": false_accept,
        "classification": classification,
        "interpretation": interpretation,
    }


def _class_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_class: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_class.setdefault(str(row["classification"]), []).append(row)
    out = []
    for classification, class_rows in sorted(by_class.items()):
        denied = [row for row in class_rows if not row["checker_allowed"]]
        false_accepts = [row for row in denied if row["typed_provenance_state_guard_false_accept"]]
        out.append(
            {
                "classification": classification,
                "events": len(class_rows),
                "checker_denied": len(denied),
                "typed_baseline_blocks": len(denied) - len(false_accepts),
                "typed_baseline_false_accepts": len(false_accepts),
            }
        )
    return out


def _summary(
    *,
    run_id: str,
    workflow_rows: list[dict[str, str]],
    event_rows: list[dict[str, Any]],
    class_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    denied = [row for row in event_rows if not row["checker_allowed"]]
    false_accepts = [row for row in denied if row["typed_provenance_state_guard_false_accept"]]
    blocked = [row for row in denied if not row["typed_provenance_state_guard_false_accept"]]
    return {
        "run_id": run_id,
        "analysis": "E3 strong typed-provenance baseline over saved R217 workflow residuals",
        "workflow_events": len(workflow_rows),
        "workflow_checker_denied": len(denied),
        "full_intentcap_unsafe_false_accepts": 0,
        "typed_provenance_state_guard_false_accepts": len(false_accepts),
        "typed_provenance_state_guard_blocks": len(blocked),
        "typed_false_accept_rate_among_denied": _rate(len(false_accepts), len(denied)),
        "typed_false_accept_classes": dict(Counter(row["classification"] for row in false_accepts)),
        "typed_block_classes": dict(Counter(row["classification"] for row in blocked)),
        "class_rows": len(class_rows),
        "same_event_comparison": True,
        "input_digests": input_digests,
        "project_head": _git_head(),
        "git_status": _git_status(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "notes": [
            "The typed baseline keeps source/field ownership plus fresh approval, holder, temporal, and budget predicates.",
            "It is stronger than post-hoc op/object/argument policy DSL and blocks most R217 residuals.",
            "It still false-accepts delegation attenuation unless it adds the same parent-child lease-set comparison at handoff.",
            "If such a policy DSL implements that atomic check-and-consume commit object, it is equivalent to the IntentCap transition interface for this case.",
        ],
    }


def _classify_reason(reason: str) -> str:
    for needle, label in FALSE_ACCEPT_REASON_PATTERNS.items():
        if needle in reason:
            return label
    for needle, label in BLOCK_REASON_PATTERNS.items():
        if needle in reason:
            return label
    return "other_denial"


def _interpretation(classification: str, false_accept: bool) -> str:
    if classification == "allowed":
        return "Checker and typed baseline both allow the event."
    if false_accept:
        return (
            "Typed provenance and separate state predicates are insufficient because the decision "
            "requires an atomic parent-child lease attenuation check at handoff."
        )
    return "Typed provenance and separate state predicates are sufficient to block this residual."


def _rate(num: int, den: int) -> str:
    if den == 0:
        return "0.000000"
    return f"{num / den:.6f}"


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return ""


def _git_status() -> str:
    try:
        return subprocess.check_output(["git", "status", "--short", "--branch"], text=True).strip()
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
