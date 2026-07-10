"""Build a paper-facing evidence matrix for IntentCap owner classes.

This analyzer is intentionally read-only. It consolidates already committed
owner-merge, commit-object, prompt-placement, multi-boundary, and recovery
summaries into one artifact that answers a narrow paper question: what evidence
currently backs the four proof-owner classes used by the Chinese paper?
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


DEFAULT_OUTPUT_DIR = Path("results/eval/R307OWNERMATRIX")
DEFAULT_RUN_ID = "R307OWNERMATRIX"
DEFAULT_INPUTS = {
    "weak_variant": Path("results/eval/R239E3WEAKABL/e3_weak_variant_summary.json"),
    "commit_minimality": Path("results/eval/R270COMMITMIN/commit_object_minimality_summary.json"),
    "merge_coverage": Path("results/eval/R281MERGECOV/three_class_merge_coverage_summary.json"),
    "boundary_coverage": Path("results/eval/R294BOUNDARYCOVERAGE/multiboundary_system_summary.json"),
    "prompt_builder": Path("results/eval/R292PROMPTBUILDER/prompt_builder_context_summary.json"),
    "recovery": Path("results/eval/R305MULTIBOUNDARYRECOVERY/closed_loop_recovery_summary.json"),
}

OWNER_FIELDS = [
    "owner_class",
    "proof_question",
    "representative_fields",
    "cannot_prove",
    "merge_counterexample_sources",
    "adapter_or_recovery_coverage",
    "scope_note",
]
PAIR_FIELDS = [
    "merged_pair",
    "covered_by_counterexample",
    "evidence_source",
    "scope_note",
]
DIGEST_FIELDS = ["input_name", "path", "sha256", "bytes"]


OWNER_ROWS = [
    {
        "owner_class": "agent",
        "proof_question": "who authorized this run, sink, approval, and delegation root",
        "representative_fields": "goal; selected object; authorized sink; approval scope; delegation root",
        "cannot_prove": "tool schema; binary path; runtime existence; observed output",
        "merge_counterexample_sources": "R239 tool->agent/env->agent/instruction->agent; R281 pairwise coverage",
        "adapter_or_recovery_coverage": "R292 prompt sections; R305 owner-class recovery metadata",
        "scope_note": "trusted issuer/canonicalization boundary, not arbitrary model-authored text",
    },
    {
        "owner_class": "instruction",
        "proof_question": "which endorsed procedure may guide the workflow or prompt placement",
        "representative_fields": "workflow scope; procedure step; prompt section; formatting preference",
        "cannot_prove": "fresh user intent; approval scope; sink authorization; callable schema",
        "merge_counterexample_sources": "R239 instruction->agent; R281 instruction+tool; R224/R281 instruction+env",
        "adapter_or_recovery_coverage": "R292 instruction placement; R305 Skill/cmd and prompt-builder tasks",
        "scope_note": "only endorsed Skill/manual/workflow cells enter this owner class",
    },
    {
        "owner_class": "tool",
        "proof_question": "which interface, schema, credential scope, binary, or sandbox contract is callable",
        "representative_fields": "callable; schema; credential scope; binary descriptor; sandbox contract",
        "cannot_prove": "current user goal; sink choice; approval token; runtime observed value",
        "merge_counterexample_sources": "R239 tool->agent/env->tool; R281 instruction+tool",
        "adapter_or_recovery_coverage": "R292 tool-routing sections; R303 MCP-style broker; R305 MCP-style broker task",
        "scope_note": "MCP/tool/cmd metadata is interface authority, not user authority",
    },
    {
        "owner_class": "env",
        "proof_question": "what this run actually observed or caused at runtime",
        "representative_fields": "observed path; concrete argument; tool result; stdout; file state; side-effect evidence",
        "cannot_prove": "authority minting; instruction endorsement; schema trust; approval widening",
        "merge_counterexample_sources": "R239 env->agent/env->tool; R224/R281 instruction+env",
        "adapter_or_recovery_coverage": "R294 env/local boundaries; R292 env prompt cells; R305 env side-effect task",
        "scope_note": "runtime observation can bind or narrow an active lease, but cannot refresh or widen it",
    },
]

PAIR_ROWS = [
    {
        "merged_pair": "agent+instruction",
        "covered_by_counterexample": True,
        "evidence_source": "R239 instruction->agent",
        "scope_note": "workflow text promoted to approval/sink/delegation root",
    },
    {
        "merged_pair": "agent+tool",
        "covered_by_counterexample": True,
        "evidence_source": "R239 tool->agent",
        "scope_note": "tool/server metadata promoted to user/admin authority",
    },
    {
        "merged_pair": "agent+env",
        "covered_by_counterexample": True,
        "evidence_source": "R239 env->agent",
        "scope_note": "runtime text promoted to user selection or sink authority",
    },
    {
        "merged_pair": "instruction+tool",
        "covered_by_counterexample": True,
        "evidence_source": "R281 controlled instruction+tool cases",
        "scope_note": "procedure text substituted for callable/schema proof and vice versa",
    },
    {
        "merged_pair": "instruction+env",
        "covered_by_counterexample": True,
        "evidence_source": "R224/R281 Skill placement substitutions",
        "scope_note": "script/tool output or unsigned text promoted to trusted instruction slot",
    },
    {
        "merged_pair": "tool+env",
        "covered_by_counterexample": True,
        "evidence_source": "R239 env->tool",
        "scope_note": "runtime observation promoted to static interface proof",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build context-owner evidence matrix")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Override an input summary path.",
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
    summaries = {name: _read_json(path) for name, path in inputs.items()}
    _validate_inputs(summaries)
    digests = [_file_digest(name, path) for name, path in sorted(inputs.items())]
    summary = _summary(summaries=summaries, digests=digests, run_id=run_id)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "context_owner_matrix.csv", OWNER_ROWS, OWNER_FIELDS)
    _write_rows(output_dir / "owner_merge_counterexamples.csv", PAIR_ROWS, PAIR_FIELDS)
    _write_rows(output_dir / "input_digests.csv", digests, DIGEST_FIELDS)
    (output_dir / "context_owner_matrix_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    return {"summary": summary, "owner_rows": OWNER_ROWS, "pair_rows": PAIR_ROWS}


def _validate_inputs(summaries: dict[str, dict[str, Any]]) -> None:
    required = set(DEFAULT_INPUTS)
    missing = required - set(summaries)
    if missing:
        raise ValueError(f"missing input summaries: {', '.join(sorted(missing))}")

    checks = [
        ("weak_variant", "no_owner_collapsed_context_false_accepts", 3593),
        ("merge_coverage", "pairwise_merges_with_counterexamples", 6),
        ("merge_coverage", "all_pairwise_merges_have_counterexample", True),
        ("commit_minimality", "tested_removals_with_counterexamples", 10),
        ("prompt_builder", "owner_class_count", 4),
        ("recovery", "owner_classes_covered", ["agent", "env", "instruction", "tool"]),
        ("recovery", "surfaces_covered", 6),
        ("boundary_coverage", "unsafe_intentcap_effects_or_placements", 0),
    ]
    for input_name, field, expected in checks:
        actual = _field(summaries[input_name], field)
        if actual != expected:
            raise ValueError(
                f"{input_name}.{field} expected {expected!r}, observed {actual!r}"
            )


def _summary(
    *,
    summaries: dict[str, dict[str, Any]],
    digests: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    weak = summaries["weak_variant"]
    commit = summaries["commit_minimality"]
    merge = summaries["merge_coverage"]
    boundary = summaries["boundary_coverage"]
    prompt = summaries["prompt_builder"]
    recovery = summaries["recovery"]
    return {
        "analysis": "context-owner evidence matrix over saved IntentCap artifacts",
        "run_id": run_id,
        "owner_classes": [row["owner_class"] for row in OWNER_ROWS],
        "owner_class_count": len(OWNER_ROWS),
        "pairwise_merges": int(merge["pairwise_merges"]),
        "pairwise_merges_with_counterexamples": int(
            merge["pairwise_merges_with_counterexamples"]
        ),
        "all_pairwise_merges_have_counterexample": bool(
            merge["all_pairwise_merges_have_counterexample"]
        ),
        "tested_removals": int(commit["tested_removals"]),
        "tested_removals_with_counterexamples": int(
            commit["tested_removals_with_counterexamples"]
        ),
        "audit_binding_gap_removals": int(commit["gap_removals"]),
        "global_taxonomy_claim": bool(merge["global_taxonomy_claim"]),
        "global_minimality_claim": bool(commit["global_minimality_claim"]),
        "no_owner_false_accepts": int(weak["no_owner_collapsed_context_false_accepts"]),
        "no_owner_denied_total": int(weak["authority_checker_denied"]),
        "prompt_builder_owner_class_count": int(prompt["owner_class_count"]),
        "prompt_builder_unsafe_authority_placements": int(
            prompt["intentcap_unsafe_authority_placements"]
        ),
        "local_boundary_rows": int(boundary["system_boundary_rows"]),
        "local_boundary_attempts": int(boundary["total_attempts"]),
        "local_boundary_unsafe_effects_or_placements": int(
            boundary["unsafe_intentcap_effects_or_placements"]
        ),
        "local_boundary_object_only_unsafe_accepts": int(
            boundary["object_only_unsafe_accepts_observed"]
        ),
        "recovery_tasks": int(recovery["tasks"]),
        "recovery_surfaces_covered": int(recovery["surfaces_covered"]),
        "recovery_owner_classes_covered": list(recovery["owner_classes_covered"]),
        "recovery_initial_blocks": int(recovery["initial_gateway_blocked_unsafe"]),
        "recovery_object_only_would_allow": int(recovery["initial_object_only_would_allow"]),
        "recovery_authorized_alternatives": int(recovery["recovered_to_allowed_alternative"]),
        "recovery_dangerous_executions": int(recovery["final_dangerous_executes"]),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_benchmark": True,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "project_head": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--short", "--branch"),
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "input_digests": digests,
        "notes": [
            "This is a read-only consolidation over saved local artifacts.",
            "It does not run a model, execute tools, replay traces, clone repositories, sync datasets, or download data.",
            "It supports the paper's scoped four-owner proof-boundary story and no-three-class-collapse evidence, not a global taxonomy-minimality claim.",
            "The recovery input includes a previous local Qwen3.6 run; this analyzer itself is not a model run.",
        ],
    }


def _field(data: dict[str, Any], dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        value = value[part]
    return value


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _file_digest(name: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "input_name": name,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
