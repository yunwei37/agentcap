"""Build E3 weak-variant false-accept evidence from saved annotations.

This script is intentionally read-only. It consumes existing R220 authority
characterization rows and R217 residual workflow baseline labels, then reports
how natural collapsed variants would behave on the same protected events.

The variants are not reproductions of named prior systems. They are mechanism
ablations that remove the runtime commit-object obligations IntentCap adds:

* full_intentcap: the checker verdict in the saved trace.
* no_owner_collapsed_context: a generic trusted-context namespace can fill any
  required authority field, so denied class-substitution attempts become accepts.
* per-edge collapsed variants: one issuer boundary is collapsed into another.
* post_hoc_policy_dsl: op/object/argument predicates accept the R217 workflow
  residuals while ignoring owner, temporal, budget, and delegation state.
* split_lifecycle_state: owner/provenance predicates remain, but temporal,
  budget, fresh approval, holder, and delegation state are not consumed in the
  same protected transition.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_AUTHORITY_EVENTS = Path("results/eval/R220AUTHCHAR/event_authority_characterization.csv")
DEFAULT_WORKFLOW_BASELINE = Path(
    "results/eval/R217E3POLICY/closest_baseline/event_baseline_labels.csv"
)

VARIANT_FIELDS = [
    "corpus",
    "variant",
    "events",
    "checker_allowed",
    "checker_denied",
    "variant_accepts",
    "variant_blocks",
    "unsafe_false_accepts",
    "false_accept_rate_among_denied",
    "same_event_comparison",
    "interpretation",
]

MODE_FIELDS = [
    "mode",
    "events",
    "checker_denied",
    "no_owner_false_accepts",
    "false_accept_rate_among_denied",
    "substitution_edges",
]

SOURCE_FIELDS = [
    "source",
    "events",
    "checker_denied",
    "no_owner_false_accepts",
    "false_accept_rate_among_denied",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]

LIFECYCLE_REASON_PATTERNS = {
    "temporal prerequisites": "temporal_state",
    "invocation budget exhausted": "budget_consumption",
    "delegated capability exceeds": "delegation_attenuation",
    "does not match lease holder": "holder_scope",
    "missing required approval proof": "approval_mint_state",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze E3 weak-variant ablations")
    parser.add_argument("--authority-events", type=Path, default=DEFAULT_AUTHORITY_EVENTS)
    parser.add_argument("--workflow-baseline", type=Path, default=DEFAULT_WORKFLOW_BASELINE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R239E3WEAKABL")
    args = parser.parse_args()

    result = analyze(
        authority_events=args.authority_events,
        workflow_baseline=args.workflow_baseline,
        run_id=args.run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "e3_weak_variant_summary.csv", result["variant_rows"], VARIANT_FIELDS)
    _write_rows(args.output_dir / "e3_no_owner_by_mode.csv", result["mode_rows"], MODE_FIELDS)
    _write_rows(args.output_dir / "e3_no_owner_by_source.csv", result["source_rows"], SOURCE_FIELDS)
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "e3_weak_variant_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n"
    )
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, authority_events: Path, workflow_baseline: Path, run_id: str) -> dict[str, Any]:
    authority_rows = list(csv.DictReader(authority_events.open()))
    workflow_rows = list(csv.DictReader(workflow_baseline.open()))

    variant_rows = []
    variant_rows.extend(_authority_variant_rows(authority_rows))
    variant_rows.extend(_workflow_variant_rows(workflow_rows))
    mode_rows = _mode_rows(authority_rows)
    source_rows = _source_rows(authority_rows)
    input_digests = [_file_digest(authority_events), _file_digest(workflow_baseline)]

    summary = _summary(
        run_id=run_id,
        authority_rows=authority_rows,
        workflow_rows=workflow_rows,
        variant_rows=variant_rows,
        mode_rows=mode_rows,
        source_rows=source_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "variant_rows": variant_rows,
        "mode_rows": mode_rows,
        "source_rows": source_rows,
        "input_digests": input_digests,
    }


def _authority_variant_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    events = len(rows)
    checker_allowed = sum(_bool(row["checker_allowed"]) for row in rows)
    checker_denied = events - checker_allowed
    substitution_false_accepts = [
        row for row in rows if not _bool(row["checker_allowed"]) and _bool(row["has_class_substitution_attempt"])
    ]
    edge_counter = _edge_counter(substitution_false_accepts)

    variants = [
        _variant_row(
            corpus="R220 authority traces",
            variant="full_intentcap",
            events=events,
            checker_allowed=checker_allowed,
            checker_denied=checker_denied,
            unsafe_false_accepts=0,
            interpretation="Full checker keeps issuer-owner and lifecycle checks in the commit object.",
        ),
        _variant_row(
            corpus="R220 authority traces",
            variant="no_owner_collapsed_context",
            events=events,
            checker_allowed=checker_allowed,
            checker_denied=checker_denied,
            unsafe_false_accepts=len(substitution_false_accepts),
            interpretation=(
                "Collapses issuer-owned fields into generic trusted context; denied class-substitution "
                "attempts become accepts."
            ),
        ),
    ]
    for edge in ("tool->agent", "env->agent", "env->tool", "instruction->agent"):
        variants.append(
            _variant_row(
                corpus="R220 authority traces",
                variant=f"collapse_{edge.replace('->', '_to_')}",
                events=events,
                checker_allowed=checker_allowed,
                checker_denied=checker_denied,
                unsafe_false_accepts=edge_counter[edge],
                interpretation=f"Collapses the {edge} proof boundary while leaving the protected event unchanged.",
            )
        )
    return variants


def _workflow_variant_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    events = len(rows)
    checker_allowed = sum(_bool(row["checker_allowed"]) for row in rows)
    checker_denied = events - checker_allowed
    policy_false_accepts = sum(_bool(row["policy_dsl_false_accept"]) for row in rows)
    lifecycle_false_accepts = [
        row for row in rows if not _bool(row["checker_allowed"]) and _lifecycle_reason(row)
    ]
    return [
        _variant_row(
            corpus="R217 workflow residuals",
            variant="full_intentcap",
            events=events,
            checker_allowed=checker_allowed,
            checker_denied=checker_denied,
            unsafe_false_accepts=0,
            interpretation="Full checker blocks workflow residuals before side effects or handoff.",
        ),
        _variant_row(
            corpus="R217 workflow residuals",
            variant="post_hoc_policy_dsl",
            events=events,
            checker_allowed=checker_allowed,
            checker_denied=checker_denied,
            unsafe_false_accepts=policy_false_accepts,
            interpretation=(
                "Operation/object/argument policy predicates accept the residuals while ignoring commit-object "
                "owner, temporal, budget, and delegation state."
            ),
        ),
        _variant_row(
            corpus="R217 workflow residuals",
            variant="split_lifecycle_state",
            events=events,
            checker_allowed=checker_allowed,
            checker_denied=checker_denied,
            unsafe_false_accepts=len(lifecycle_false_accepts),
            interpretation=(
                "Stateful proof, holder, approval, budget, temporal, and delegation checks are split from "
                "the action/provenance guard."
            ),
        ),
    ]


def _variant_row(
    *,
    corpus: str,
    variant: str,
    events: int,
    checker_allowed: int,
    checker_denied: int,
    unsafe_false_accepts: int,
    interpretation: str,
) -> dict[str, Any]:
    variant_accepts = checker_allowed + unsafe_false_accepts
    return {
        "corpus": corpus,
        "variant": variant,
        "events": events,
        "checker_allowed": checker_allowed,
        "checker_denied": checker_denied,
        "variant_accepts": variant_accepts,
        "variant_blocks": events - variant_accepts,
        "unsafe_false_accepts": unsafe_false_accepts,
        "false_accept_rate_among_denied": _rate(unsafe_false_accepts, checker_denied),
        "same_event_comparison": True,
        "interpretation": interpretation,
    }


def _mode_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_mode: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_mode.setdefault(row["mode"], []).append(row)
    out = []
    for mode, mode_rows in sorted(by_mode.items()):
        denied = [row for row in mode_rows if not _bool(row["checker_allowed"])]
        false_accepts = [
            row for row in denied if _bool(row["has_class_substitution_attempt"])
        ]
        out.append(
            {
                "mode": mode,
                "events": len(mode_rows),
                "checker_denied": len(denied),
                "no_owner_false_accepts": len(false_accepts),
                "false_accept_rate_among_denied": _rate(len(false_accepts), len(denied)),
                "substitution_edges": _format_counter(_edge_counter(false_accepts)),
            }
        )
    return out


def _source_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)
    out = []
    for source, source_rows in sorted(by_source.items()):
        denied = [row for row in source_rows if not _bool(row["checker_allowed"])]
        false_accepts = [
            row for row in denied if _bool(row["has_class_substitution_attempt"])
        ]
        out.append(
            {
                "source": source,
                "events": len(source_rows),
                "checker_denied": len(denied),
                "no_owner_false_accepts": len(false_accepts),
                "false_accept_rate_among_denied": _rate(len(false_accepts), len(denied)),
            }
        )
    return out


def _summary(
    *,
    run_id: str,
    authority_rows: list[dict[str, str]],
    workflow_rows: list[dict[str, str]],
    variant_rows: list[dict[str, Any]],
    mode_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    authority_denied = [row for row in authority_rows if not _bool(row["checker_allowed"])]
    substitution_false_accepts = [
        row for row in authority_denied if _bool(row["has_class_substitution_attempt"])
    ]
    workflow_denied = [row for row in workflow_rows if not _bool(row["checker_allowed"])]
    workflow_lifecycle = [row for row in workflow_denied if _lifecycle_reason(row)]
    return {
        "run_id": run_id,
        "analysis": "E3 weak-variant ablation over saved authority annotations",
        "authority_events": len(authority_rows),
        "authority_checker_allowed": len(authority_rows) - len(authority_denied),
        "authority_checker_denied": len(authority_denied),
        "full_intentcap_unsafe_false_accepts": 0,
        "no_owner_collapsed_context_false_accepts": len(substitution_false_accepts),
        "no_owner_false_accept_rate_among_denied": _rate(
            len(substitution_false_accepts), len(authority_denied)
        ),
        "collapse_edge_false_accepts": dict(_edge_counter(substitution_false_accepts)),
        "workflow_events": len(workflow_rows),
        "workflow_checker_denied": len(workflow_denied),
        "workflow_policy_dsl_false_accepts": sum(
            _bool(row["policy_dsl_false_accept"]) for row in workflow_rows
        ),
        "workflow_split_lifecycle_false_accepts": len(workflow_lifecycle),
        "workflow_lifecycle_classes": dict(Counter(_lifecycle_reason(row) for row in workflow_lifecycle)),
        "mode_rows": len(mode_rows),
        "source_rows": len(source_rows),
        "variant_rows": len(variant_rows),
        "same_event_comparison": True,
        "input_digests": input_digests,
        "project_head": _git_head(),
        "git_status": _git_status(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "notes": [
            "Rows are same-event ablations: op/object/arguments/provenance records are unchanged.",
            "No-owner/collapsed variants use existing R220 class-substitution annotations.",
            "Post-hoc policy DSL and split-lifecycle variants use existing R217 residual labels and checker reasons.",
            "These are mechanism ablations, not reproductions of named prior systems.",
        ],
    }


def _lifecycle_reason(row: dict[str, str]) -> str:
    reason = row.get("checker_reason", "")
    for needle, label in LIFECYCLE_REASON_PATTERNS.items():
        if needle in reason:
            return label
    return ""


def _edge_counter(rows: list[dict[str, str]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for edge in str(row.get("substitution_edges", "")).split("|"):
            edge = edge.strip()
            if edge:
                counter[edge] += 1
    return counter


def _format_counter(counter: Counter[str]) -> str:
    return "|".join(f"{key}:{value}" for key, value in sorted(counter.items()))


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


def _command_text() -> str:
    return " ".join(["python", *(__import__("sys").argv)]) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
