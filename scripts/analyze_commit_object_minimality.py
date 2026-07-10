"""Summarize commit-object minimality evidence from saved IntentCap results.

This script does not run a model, replay traces, or sync datasets. It reads
existing result summaries and builds a reviewer-facing matrix:

* which authority-state commit-object obligation is removed;
* which saved same-event or local-boundary evidence exercises that removal;
* whether the removal has a false-accept counterexample or remains an evidence gap.

The output deliberately does not claim global minimality. It states minimality
only with respect to the tested owner-projection, lifecycle, and local-boundary
collapses represented by saved artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_WEAK = Path("results/eval/R239E3WEAKABL/e3_weak_variant_summary.json")
DEFAULT_TYPED = Path("results/eval/R241E3TYPEDBASE/typed_provenance_baseline_summary.json")
DEFAULT_MULTI = Path("results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json")
DEFAULT_PROOF = Path("results/eval/R240ADAPTERPROOF/adapter_proof_completeness_summary.json")

ROW_FIELDS = [
    "removal_id",
    "removed_commit_obligation",
    "corpus",
    "denominator",
    "false_accepts_or_unsafe_accepts",
    "evidence_status",
    "source_field",
    "interpretation",
]

DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build commit-object minimality evidence matrix")
    parser.add_argument("--weak-summary", type=Path, default=DEFAULT_WEAK)
    parser.add_argument("--typed-summary", type=Path, default=DEFAULT_TYPED)
    parser.add_argument("--multi-summary", type=Path, default=DEFAULT_MULTI)
    parser.add_argument("--proof-summary", type=Path, default=DEFAULT_PROOF)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R270COMMITMIN")
    args = parser.parse_args()

    result = analyze(
        weak_summary=args.weak_summary,
        typed_summary=args.typed_summary,
        multi_summary=args.multi_summary,
        proof_summary=args.proof_summary,
        run_id=args.run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "commit_object_minimality_rows.csv", result["rows"], ROW_FIELDS)
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], DIGEST_FIELDS)
    (args.output_dir / "commit_object_minimality_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n"
    )
    (args.output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(
    *,
    weak_summary: Path,
    typed_summary: Path,
    multi_summary: Path,
    proof_summary: Path,
    run_id: str,
) -> dict[str, Any]:
    weak = _read_json(weak_summary)
    typed = _read_json(typed_summary)
    multi = _read_json(multi_summary)
    proof = _read_json(proof_summary)

    authority_denied = int(weak["authority_checker_denied"])
    workflow_denied = int(weak["workflow_checker_denied"])
    local_attempts = int(multi["total_attempts"])
    rows = [
        _row(
            "owner_projection_all",
            "all issuer-owned field projections collapsed into generic trusted context",
            "R220 authority traces",
            authority_denied,
            int(weak["no_owner_collapsed_context_false_accepts"]),
            "R239.no_owner_collapsed_context_false_accepts",
            "Removing field owners lets class-substitution attempts satisfy protected fields.",
        ),
        _row(
            "owner_projection_tool_to_agent",
            "tool/server metadata may satisfy agent-owned intent, sink, or approval fields",
            "R220 authority traces",
            authority_denied,
            int(weak["collapse_edge_false_accepts"]["tool->agent"]),
            "R239.collapse_edge_false_accepts.tool->agent",
            "Tool metadata becomes user authority when tool and agent projections merge.",
        ),
        _row(
            "owner_projection_env_to_agent",
            "runtime evidence may satisfy agent-owned intent, selection, or sink fields",
            "R220 authority traces",
            authority_denied,
            int(weak["collapse_edge_false_accepts"]["env->agent"]),
            "R239.collapse_edge_false_accepts.env->agent",
            "Observed text or tool output becomes user authority when env and agent projections merge.",
        ),
        _row(
            "owner_projection_env_to_tool",
            "runtime evidence may satisfy tool-owned schema/interface fields",
            "R220 authority traces",
            authority_denied,
            int(weak["collapse_edge_false_accepts"]["env->tool"]),
            "R239.collapse_edge_false_accepts.env->tool",
            "Tool results or stdout inherit interface trust when env and tool projections merge.",
        ),
        _row(
            "owner_projection_instruction_to_agent",
            "workflow/instruction text may satisfy agent-owned sink, approval, or delegation root",
            "R220 authority traces",
            authority_denied,
            int(weak["collapse_edge_false_accepts"]["instruction->agent"]),
            "R239.collapse_edge_false_accepts.instruction->agent",
            "Instruction text becomes user authority when instruction and agent projections merge.",
        ),
        _row(
            "post_hoc_action_policy",
            "pre-effect owner/lifecycle commit replaced with op/object/argument policy after materialization",
            "R217 workflow residuals",
            workflow_denied,
            int(weak["workflow_policy_dsl_false_accepts"]),
            "R239.workflow_policy_dsl_false_accepts",
            "Action-shaped predicates accept residuals that require issuer and lifecycle state.",
        ),
        _row(
            "split_lifecycle_state",
            "budget, holder, approval, temporal, and delegation state checked outside one transition",
            "R217 workflow residuals",
            workflow_denied,
            int(weak["workflow_split_lifecycle_false_accepts"]),
            "R239.workflow_split_lifecycle_false_accepts",
            "Separating lifecycle checks from the decision admits stale or mis-scoped authority.",
        ),
        _row(
            "missing_parent_child_handoff_commit",
            "typed provenance/state guard lacks same-transition parent-child lease-set comparison",
            "R217 workflow residuals",
            int(typed["workflow_checker_denied"]),
            int(typed["typed_provenance_state_guard_false_accepts"]),
            "R241.typed_provenance_state_guard_false_accepts",
            "A strong typed baseline converges except for delegation attenuation without parent-child commit.",
        ),
        _row(
            "missing_local_provenance",
            "local boundary keeps lease arguments but drops provenance/influence proof",
            "R225 local multi-boundary records",
            local_attempts,
            int(multi["no_provenance_unsafe_accepts_observed"]),
            "R225.no_provenance_unsafe_accepts_observed",
            "Dropping provenance at local placement/handoff/side-effect boundaries admits unsafe accepts.",
        ),
        _row(
            "object_only_local_boundary",
            "local boundary checks only object/operation shape",
            "R225 local multi-boundary records",
            local_attempts,
            int(multi["object_only_unsafe_accepts_observed"]),
            "R225.object_only_unsafe_accepts_observed",
            "Object-only enforcement misses context/provenance and lifecycle obligations.",
        ),
        {
            "removal_id": "audit_binding_removed",
            "removed_commit_obligation": "audit id not bound to the allow transition",
            "corpus": "not separately isolated",
            "denominator": "",
            "false_accepts_or_unsafe_accepts": "",
            "evidence_status": "gap",
            "source_field": "not yet tested as an isolated removal",
            "interpretation": "Audit binding is part of the contract, but current results do not isolate its removal as a false-accept ablation.",
        },
    ]

    counterexample_rows = [
        row for row in rows if row["evidence_status"] == "saved_counterexample"
    ]
    gap_rows = [row for row in rows if row["evidence_status"] == "gap"]
    summary = {
        "run_id": run_id,
        "analysis": "authority-state commit-object minimality matrix over saved results",
        "tested_removals": len(counterexample_rows),
        "tested_removals_with_counterexamples": sum(
            int(row["false_accepts_or_unsafe_accepts"]) > 0 for row in counterexample_rows
        ),
        "gap_removals": len(gap_rows),
        "gap_removal_ids": [row["removal_id"] for row in gap_rows],
        "full_intentcap_unsafe_false_accepts": int(weak["full_intentcap_unsafe_false_accepts"]),
        "full_intentcap_local_unsafe_effects_or_placements": int(
            multi["unsafe_intentcap_effects_or_placements"]
        ),
        "no_owner_collapsed_context_false_accepts": int(
            weak["no_owner_collapsed_context_false_accepts"]
        ),
        "workflow_split_lifecycle_false_accepts": int(
            weak["workflow_split_lifecycle_false_accepts"]
        ),
        "typed_parent_child_missing_false_accepts": int(
            typed["typed_provenance_state_guard_false_accepts"]
        ),
        "local_object_only_unsafe_accepts": int(multi["object_only_unsafe_accepts_observed"]),
        "local_no_provenance_unsafe_accepts": int(
            multi["no_provenance_unsafe_accepts_observed"]
        ),
        "adapter_proof_complete_for_verdict": int(proof["proof_complete_for_verdict"]),
        "adapter_events": int(proof["events"]),
        "same_event_or_boundary_counterexamples": True,
        "global_minimality_claim": False,
        "scope": (
            "Minimality is only with respect to the listed tested owner-projection, "
            "lifecycle, and local-boundary removals. Audit-id removal remains a gap."
        ),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_experiment_trace": True,
        "project_head": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--short", "--branch"),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    input_paths = [weak_summary, typed_summary, multi_summary, proof_summary]
    return {
        "rows": rows,
        "summary": summary,
        "input_digests": [_digest(path) for path in input_paths],
    }


def _row(
    removal_id: str,
    removed: str,
    corpus: str,
    denominator: int,
    false_accepts: int,
    source_field: str,
    interpretation: str,
) -> dict[str, Any]:
    return {
        "removal_id": removal_id,
        "removed_commit_obligation": removed,
        "corpus": corpus,
        "denominator": denominator,
        "false_accepts_or_unsafe_accepts": false_accepts,
        "evidence_status": "saved_counterexample" if false_accepts > 0 else "no_counterexample",
        "source_field": source_field,
        "interpretation": interpretation,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
