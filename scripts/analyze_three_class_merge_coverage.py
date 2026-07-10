"""Build pairwise three-class owner-merge coverage evidence.

This analyzer is intentionally read-only over saved summaries plus one local
controlled suite. It closes the paper-facing gap left by the earlier
three-class merge table: instruction+tool had no isolated counterexample row.
The script does not claim natural prevalence. It reports whether each pairwise
merge has at least one saved or controlled false-accept counterexample.
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

from intentcap.checker import CheckerSession  # noqa: E402


DEFAULT_WEAK_SUMMARY = Path("results/eval/R239E3WEAKABL/e3_weak_variant_summary.json")
DEFAULT_SKILL_SUMMARY = Path(
    "results/eval/R224SKILLBOUNDARY/skill_instruction_boundary_summary.json"
)
DEFAULT_CONTROLLED_SUITE = Path("examples/three_class_merge_coverage_suite.json")

MERGE_FIELDS = [
    "merged_pair",
    "direction_or_substitution",
    "false_accept_counterexamples",
    "denominator",
    "evidence_source",
    "coverage_status",
    "notes",
]
CASE_FIELDS = [
    "case_id",
    "merge_pair",
    "direction",
    "full_checker_allowed",
    "weak_variant_allowed",
    "weak_false_accept",
    "checker_reason",
    "artifact_family",
    "unsafe_substitution",
]
INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze pairwise owner-merge coverage")
    parser.add_argument("--weak-summary", type=Path, default=DEFAULT_WEAK_SUMMARY)
    parser.add_argument("--skill-summary", type=Path, default=DEFAULT_SKILL_SUMMARY)
    parser.add_argument("--controlled-suite", type=Path, default=DEFAULT_CONTROLLED_SUITE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R281MERGECOV")
    args = parser.parse_args()

    result = analyze(
        weak_summary_path=args.weak_summary,
        skill_summary_path=args.skill_summary,
        controlled_suite_path=args.controlled_suite,
        run_id=args.run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(args.output_dir / "three_class_merge_coverage.csv", result["merge_rows"], MERGE_FIELDS)
    _write_rows(args.output_dir / "controlled_case_rows.csv", result["case_rows"], CASE_FIELDS)
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "three_class_merge_coverage_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n"
    )
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(
    *,
    weak_summary_path: Path,
    skill_summary_path: Path,
    controlled_suite_path: Path,
    run_id: str,
) -> dict[str, Any]:
    weak_summary = json.loads(weak_summary_path.read_text())
    skill_summary = json.loads(skill_summary_path.read_text())
    controlled_suite = json.loads(controlled_suite_path.read_text())
    case_rows = _controlled_case_rows(controlled_suite)
    merge_rows = _merge_rows(
        weak_summary=weak_summary,
        skill_summary=skill_summary,
        case_rows=case_rows,
    )
    input_digests = [
        _file_digest(weak_summary_path),
        _file_digest(skill_summary_path),
        _file_digest(controlled_suite_path),
    ]
    summary = _summary(
        run_id=run_id,
        merge_rows=merge_rows,
        case_rows=case_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "merge_rows": merge_rows,
        "case_rows": case_rows,
        "input_digests": input_digests,
    }


def _controlled_case_rows(suite: dict[str, Any]) -> list[dict[str, Any]]:
    base_trace = {
        "labels": suite.get("labels", {}),
        "leases": suite.get("leases", []),
    }
    rows = []
    for case in suite.get("cases", []):
        event = case["event"]
        verdict = CheckerSession.from_trace(base_trace).check(event)
        full_allowed = bool(verdict["allowed"])
        weak_allowed = bool(case.get("weak_variant_accepts", False))
        rows.append(
            {
                "case_id": str(case.get("id", event.get("id", ""))),
                "merge_pair": str(case.get("merge_pair", "")),
                "direction": str(case.get("direction", "")),
                "full_checker_allowed": full_allowed,
                "weak_variant_allowed": weak_allowed,
                "weak_false_accept": weak_allowed and not full_allowed,
                "checker_reason": str(verdict["reason"]),
                "artifact_family": str(case.get("artifact_family", "")),
                "unsafe_substitution": str(case.get("unsafe_substitution", "")),
            }
        )
    return rows


def _merge_rows(
    *,
    weak_summary: dict[str, Any],
    skill_summary: dict[str, Any],
    case_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    edge_counts = weak_summary.get("collapse_edge_false_accepts", {})
    instruction_tool_false_accepts = sum(
        1
        for row in case_rows
        if row["merge_pair"] == "instruction+tool" and row["weak_false_accept"]
    )
    instruction_tool_cases = sum(
        1 for row in case_rows if row["merge_pair"] == "instruction+tool"
    )
    skill_substitutions = int(skill_summary["blocked_instruction_substitutions"])
    return [
        _row(
            pair="agent+tool",
            substitution="tool/server metadata -> agent-owned intent/sink/approval/policy",
            false_accepts=int(edge_counts["tool->agent"]),
            denominator=int(weak_summary["authority_checker_denied"]),
            source="R239 same-event authority traces",
            status="tested aggregate",
            notes="tool owner collapsed into agent owner",
        ),
        _row(
            pair="agent+env",
            substitution="runtime text/tool result -> agent-owned selection/sink",
            false_accepts=int(edge_counts["env->agent"]),
            denominator=int(weak_summary["authority_checker_denied"]),
            source="R239 same-event authority traces",
            status="tested aggregate",
            notes="env owner collapsed into agent owner",
        ),
        _row(
            pair="tool+env",
            substitution="runtime observation -> tool-owned schema/interface proof",
            false_accepts=int(edge_counts["env->tool"]),
            denominator=int(weak_summary["authority_checker_denied"]),
            source="R239 same-event authority traces",
            status="tested aggregate",
            notes="env owner collapsed into tool owner",
        ),
        _row(
            pair="agent+instruction",
            substitution="workflow text -> agent-owned approval/sink/delegation root",
            false_accepts=int(edge_counts["instruction->agent"]),
            denominator=int(weak_summary["authority_checker_denied"]),
            source="R239 same-event authority traces",
            status="tested aggregate",
            notes="instruction owner collapsed into agent owner",
        ),
        _row(
            pair="instruction+env",
            substitution="script/tool output or unsigned text -> trusted instruction slot",
            false_accepts=skill_substitutions,
            denominator=skill_substitutions,
            source="R224 Skill placement substitutions",
            status="local counterexample",
            notes="env-like runtime/output text collapsed into instruction owner",
        ),
        _row(
            pair="instruction+tool",
            substitution="procedure text <-> callable/schema/interface proof",
            false_accepts=instruction_tool_false_accepts,
            denominator=instruction_tool_cases,
            source="controlled Skill/cmd and MCP/Skill placement suite",
            status="controlled counterexample",
            notes="new isolated pairwise merge cases in examples/three_class_merge_coverage_suite.json",
        ),
    ]


def _row(
    *,
    pair: str,
    substitution: str,
    false_accepts: int,
    denominator: int,
    source: str,
    status: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "merged_pair": pair,
        "direction_or_substitution": substitution,
        "false_accept_counterexamples": false_accepts,
        "denominator": denominator,
        "evidence_source": source,
        "coverage_status": status,
        "notes": notes,
    }


def _summary(
    *,
    run_id: str,
    merge_rows: list[dict[str, Any]],
    case_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    pairs_with_counterexamples = sum(
        1 for row in merge_rows if int(row["false_accept_counterexamples"]) > 0
    )
    controlled_false_accepts = sum(1 for row in case_rows if row["weak_false_accept"])
    return {
        "run_id": run_id,
        "analysis": "pairwise three-class owner-merge coverage",
        "pairwise_merges": len(merge_rows),
        "pairwise_merges_with_counterexamples": pairs_with_counterexamples,
        "all_pairwise_merges_have_counterexample": pairs_with_counterexamples == len(merge_rows),
        "controlled_cases": len(case_rows),
        "controlled_instruction_tool_false_accepts": controlled_false_accepts,
        "full_checker_unsafe_accepts_on_controlled_cases": sum(
            1 for row in case_rows if row["full_checker_allowed"]
        ),
        "input_digests": input_digests,
        "project_head": _git_head(),
        "git_status": _git_status(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_benchmark": True,
        "global_taxonomy_claim": False,
        "notes": [
            "The result is coverage over tested merge families, not a natural prevalence estimate.",
            "R239 supplies aggregate saved-trace owner-collapse counts for four pair families.",
            "R224 supplies the local instruction+env placement substitution row.",
            "The controlled suite isolates instruction+tool in both directions without model calls or side effects.",
        ],
    }


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _git_status() -> str:
    return subprocess.check_output(["git", "status", "--short", "--branch"], text=True).strip()


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
