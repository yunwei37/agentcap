"""Build a top-conference claim evidence matrix from saved IntentCap results.

This is a saved-result analysis. It does not run models, execute tools, clone
benchmarks, or download datasets. The goal is to connect two existing evidence
families into paper-facing tables:

* R025 checker ablation: how many protected decisions resource/object-only
  policies would accept when IntentCap denies them for provenance reasons.
* R027 authority distance: how far static ACL/server/tool policies are from the
  current IntentCap oracle profiles and how many unsafe events they admit.

The output is intentionally conservative: it records what the saved artifacts
support and what they still do not support.
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


DEFAULT_CHECKER_SUMMARY = Path("results/checker/R025/checker_ablation_summary.json")
DEFAULT_ORACLE_DISTANCE = Path("results/eval/R027/baseline_oracle_distance.csv")

SECURITY_FIELDS = [
    "evidence_id",
    "source",
    "benchmark",
    "baseline",
    "comparison",
    "protected_events",
    "unsafe_or_false_accepts",
    "unsafe_or_false_accept_rate",
    "authorize_violations",
    "sink_select_violations",
    "tool_select_violations",
    "extra_authority_slots_vs_oracle",
    "oracle_distance_score",
    "interpretation",
]

CLAIM_FIELDS = [
    "claim_id",
    "claim",
    "support_level",
    "primary_evidence",
    "strongest_counterpoint",
    "paper_safe_wording",
    "missing_for_stronger_claim",
]

RANKING_FIELDS = [
    "benchmark",
    "baseline",
    "oracle_baseline",
    "unsafe_events_total",
    "unsafe_events_admitted",
    "unsafe_admit_rate",
    "extra_authority_slots_vs_oracle",
    "oracle_distance_score",
    "distance_over_oracle_slots",
    "description",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze top-conference IntentCap claim evidence")
    parser.add_argument("--run-id", default="R081")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checker-summary", type=Path, default=DEFAULT_CHECKER_SUMMARY)
    parser.add_argument("--oracle-distance", type=Path, default=DEFAULT_ORACLE_DISTANCE)
    args = parser.parse_args()

    checker_summary = json.loads(args.checker_summary.read_text())
    distance_rows = _read_csv(args.oracle_distance)
    result = analyze(
        run_id=args.run_id,
        checker_summary=checker_summary,
        distance_rows=distance_rows,
        input_paths=(args.checker_summary, args.oracle_distance),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "topconf_claim_evidence_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "security_evidence_matrix.csv", result["security_rows"], SECURITY_FIELDS)
    _write_rows(args.output_dir / "claim_evidence_matrix.csv", result["claim_rows"], CLAIM_FIELDS)
    _write_rows(args.output_dir / "baseline_risk_ranking.csv", result["ranking_rows"], RANKING_FIELDS)
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(
    *,
    run_id: str,
    checker_summary: dict[str, Any],
    distance_rows: list[dict[str, str]],
    input_paths: tuple[Path, ...] = (DEFAULT_CHECKER_SUMMARY, DEFAULT_ORACLE_DISTANCE),
) -> dict[str, Any]:
    security_rows = _checker_security_rows(checker_summary)
    security_rows.extend(_distance_security_rows(distance_rows))
    ranking_rows = _ranking_rows(distance_rows)
    claim_rows = _claim_rows(checker_summary, distance_rows)
    input_digests = [_file_digest(path) for path in input_paths]
    summary = _summary(
        run_id=run_id,
        checker_summary=checker_summary,
        distance_rows=distance_rows,
        security_rows=security_rows,
        claim_rows=claim_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "security_rows": security_rows,
        "claim_rows": claim_rows,
        "ranking_rows": ranking_rows,
        "input_digests": input_digests,
    }


def _checker_security_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    denied = int(summary.get("checker_denied", 0))
    rows = []
    configs = [
        (
            "checker_ablation.object_only",
            "object_only",
            "op/object-only policy ignores args and provenance",
            "Object/resource matching would accept every saved protected decision denied by IntentCap.",
        ),
        (
            "checker_ablation.lease_constraints_no_provenance",
            "lease_constraints_no_provenance",
            "saved lease op/object/args, no provenance",
            "Even argument-constrained leases are unsafe when context labels and control provenance are ignored.",
        ),
        (
            "checker_ablation.full_event_args_no_provenance",
            "full_event_args_no_provenance",
            "LLM-like full event args, no provenance",
            "A complete-looking event-specific lease is still unsafe without deterministic provenance checks.",
        ),
    ]
    for evidence_id, prefix, comparison, interpretation in configs:
        false_accepts = int(summary.get(f"{prefix}_false_accept", 0))
        by_mode = summary.get(f"{prefix}_false_accept_by_mode", {})
        if prefix == "object_only" and false_accepts == denied:
            by_mode = summary.get("checker_denied_by_mode", by_mode)
        rows.append(
            {
                "evidence_id": evidence_id,
                "source": "R025 checker ablation",
                "benchmark": "saved mixed traces",
                "baseline": prefix,
                "comparison": comparison,
                "protected_events": denied,
                "unsafe_or_false_accepts": false_accepts,
                "unsafe_or_false_accept_rate": false_accepts / denied if denied else 0.0,
                "authorize_violations": int(by_mode.get("authorize", 0)),
                "sink_select_violations": int(by_mode.get("sink_select", 0)),
                "tool_select_violations": int(by_mode.get("tool_select", 0)),
                "extra_authority_slots_vs_oracle": "",
                "oracle_distance_score": "",
                "interpretation": interpretation,
            }
        )
    return rows


def _distance_security_rows(distance_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in distance_rows:
        if _bool(row.get("is_oracle", "")):
            continue
        unsafe_total = _int(row.get("unsafe_events_total"))
        unsafe_admitted = _int(row.get("unsafe_events_admitted"))
        extra_slots = _float(row.get("extra_authority_slots_vs_oracle"))
        if unsafe_admitted <= 0 and extra_slots <= 0:
            continue
        comparison = "static policy vs IntentCap oracle profile"
        if unsafe_admitted > 0 and extra_slots == 0:
            comparison = "same exposed object count, missing provenance/argument authority"
        elif unsafe_admitted > 0:
            comparison = "broader static authority and missing provenance/argument authority"
        elif extra_slots > 0:
            comparison = "broader static authority without observed unsafe events in this corpus"
        rows.append(
            {
                "evidence_id": f"oracle_distance.{row['benchmark']}.{row['baseline']}",
                "source": "R027 oracle-distance scoring",
                "benchmark": row["benchmark"],
                "baseline": row["baseline"],
                "comparison": comparison,
                "protected_events": unsafe_total,
                "unsafe_or_false_accepts": unsafe_admitted,
                "unsafe_or_false_accept_rate": _float(row.get("unsafe_admit_rate")),
                "authorize_violations": "",
                "sink_select_violations": "",
                "tool_select_violations": "",
                "extra_authority_slots_vs_oracle": extra_slots,
                "oracle_distance_score": _int(row.get("oracle_distance_score")),
                "interpretation": row.get("description", ""),
            }
        )
    return rows


def _claim_rows(checker_summary: dict[str, Any], distance_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    denied = int(checker_summary.get("checker_denied", 0))
    object_false = int(checker_summary.get("object_only_false_accept", 0))
    same_exposure_unsafe = [
        row for row in distance_rows
        if not _bool(row.get("is_oracle", ""))
        and _int(row.get("unsafe_events_admitted")) > 0
        and _float(row.get("extra_authority_slots_vs_oracle")) == 0.0
    ]
    same_exposure_unsafe_admissions = sum(
        _int(row.get("unsafe_events_admitted")) for row in same_exposure_unsafe
    )
    non_oracle_rows = [row for row in distance_rows if not _bool(row.get("is_oracle", ""))]
    max_extra = max((_float(row.get("extra_authority_slots_vs_oracle")) for row in non_oracle_rows), default=0.0)
    non_oracle_unsafe_admissions = sum(
        _int(row.get("unsafe_events_admitted")) for row in non_oracle_rows
    )
    unique_unsafe_total = _unique_unsafe_events_total(non_oracle_rows)

    return [
        {
            "claim_id": "TC1",
            "claim": "Context influence is a security boundary distinct from tool/resource access.",
            "support_level": "strong saved-trace evidence, not yet fresh online baseline evidence",
            "primary_evidence": (
                f"R025: object-only accepts {object_false}/{denied} checker-denied protected decisions; "
                "R027: same-exposure non-oracle baseline profiles produce "
                f"{same_exposure_unsafe_admissions} unsafe event admissions."
            ),
            "strongest_counterpoint": (
                "Artifacts are saved traces/post-hoc policy analyses; fresh online wrappers for the strongest baselines are still missing."
            ),
            "paper_safe_wording": (
                "Across saved traces, policies that match tools/resources but ignore context provenance admit protected decisions that IntentCap denies."
            ),
            "missing_for_stronger_claim": (
                "Run fresh online agents with vanilla/tool-ACL/MCP-allowlist/Task-Shield-or-CaMeL-style baselines on the same tasks."
            ),
        },
        {
            "claim_id": "TC2",
            "claim": "Intent-carrying leases reduce authority surface relative to static tool/server policies.",
            "support_level": "strong saved-result evidence, expert-blind oracle still missing",
            "primary_evidence": (
                "R027: non-oracle baseline profiles produce "
                f"{non_oracle_unsafe_admissions} unsafe event admissions over "
                f"{unique_unsafe_total} unique unsafe events in the saved security corpora; "
                f"max extra authority is {max_extra:g} slots over the current IntentCap oracle profiles."
            ),
            "strongest_counterpoint": (
                "The current oracle profiles are project-generated, not a blinded expert-written oracle corpus."
            ),
            "paper_safe_wording": (
                "IntentCap profiles are closer to the current per-event/provenance oracle and expose less static authority than broad ACL/server policies."
            ),
            "missing_for_stronger_claim": (
                "Create a blinded expert-oracle lease set and report distance before inspecting IntentCap output."
            ),
        },
        {
            "claim_id": "TC3",
            "claim": "LLM-generated leases must be checker-validated outside the TCB.",
            "support_level": "strong checker-ablation evidence, compiler validity labels still partial",
            "primary_evidence": (
                "R025: full-event-args/no-provenance proposals false-accept "
                f"{int(checker_summary.get('full_event_args_no_provenance_false_accept', 0))} protected decisions."
            ),
            "strongest_counterpoint": (
                "This row uses ablated synthetic proposals plus saved compiler probes; it is not a fully independent lease-validity annotation study."
            ),
            "paper_safe_wording": (
                "Deterministic provenance checking rejects unsafe candidate leases that a complete-looking event policy would accept."
            ),
            "missing_for_stronger_claim": (
                "Hand-label a compiler proposal corpus and compare LLM-only, checker-only, and checker+repair variants."
            ),
        },
        {
            "claim_id": "TC4",
            "claim": "Narrow leases preserve practical utility with structured recovery.",
            "support_level": "weak/partial",
            "primary_evidence": (
                "R062/R065 show exact-oracle tau2 utility with constrained active-lease UI; R079 shows strict compiler-corpus lower-bound task-loop safety but poor utility."
            ),
            "strongest_counterpoint": (
                "The best utility evidence still depends on exact reference leases; the non-oracle compiler task loop is not utility-ready."
            ),
            "paper_safe_wording": (
                "Current utility results are mechanism probes and upper/lower bounds, not final task-success evidence."
            ),
            "missing_for_stronger_claim": (
                "Improve non-oracle exact argument synthesis and run compiler+refinement task loops against broad/static baselines."
            ),
        },
    ]


def _ranking_rows(distance_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in distance_rows:
        if _bool(row.get("is_oracle", "")):
            continue
        rows.append(
            {
                "benchmark": row["benchmark"],
                "baseline": row["baseline"],
                "oracle_baseline": row["oracle_baseline"],
                "unsafe_events_total": _int(row.get("unsafe_events_total")),
                "unsafe_events_admitted": _int(row.get("unsafe_events_admitted")),
                "unsafe_admit_rate": _float(row.get("unsafe_admit_rate")),
                "extra_authority_slots_vs_oracle": _float(row.get("extra_authority_slots_vs_oracle")),
                "oracle_distance_score": _int(row.get("oracle_distance_score")),
                "distance_over_oracle_slots": _float(row.get("distance_over_oracle_slots")),
                "description": row.get("description", ""),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -int(row["unsafe_events_admitted"]),
            -float(row["extra_authority_slots_vs_oracle"]),
            -int(row["oracle_distance_score"]),
        ),
    )


def _summary(
    *,
    run_id: str,
    checker_summary: dict[str, Any],
    distance_rows: list[dict[str, str]],
    security_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    non_oracle = [row for row in distance_rows if not _bool(row.get("is_oracle", ""))]
    same_exposure_unsafe = [
        row for row in non_oracle
        if _int(row.get("unsafe_events_admitted")) > 0
        and _float(row.get("extra_authority_slots_vs_oracle")) == 0.0
    ]
    return {
        "run_id": run_id,
        "analysis": "top-conference claim evidence matrix over saved IntentCap results",
        "project_head": _git(["rev-parse", "HEAD"]),
        "git_status": _git(["status", "--short"]),
        "machine": platform.platform(),
        "input_digests": input_digests,
        "checker_events": int(checker_summary.get("events", 0)),
        "checker_denied_protected_decisions": int(checker_summary.get("checker_denied", 0)),
        "object_only_false_accepts": int(checker_summary.get("object_only_false_accept", 0)),
        "lease_no_provenance_false_accepts": int(
            checker_summary.get("lease_constraints_no_provenance_false_accept", 0)
        ),
        "full_event_args_no_provenance_false_accepts": int(
            checker_summary.get("full_event_args_no_provenance_false_accept", 0)
        ),
        "checker_denied_by_mode": checker_summary.get("checker_denied_by_mode", {}),
        "non_oracle_baseline_rows": len(non_oracle),
        "non_oracle_unsafe_event_admissions": sum(
            _int(row.get("unsafe_events_admitted")) for row in non_oracle
        ),
        "unique_unsafe_events_total": _unique_unsafe_events_total(non_oracle),
        "same_exposure_unsafe_event_admissions": sum(
            _int(row.get("unsafe_events_admitted")) for row in same_exposure_unsafe
        ),
        "max_extra_authority_slots_vs_oracle": max(
            (_float(row.get("extra_authority_slots_vs_oracle")) for row in non_oracle),
            default=0.0,
        ),
        "security_evidence_rows": len(security_rows),
        "claim_rows": len(claim_rows),
        "claim_verdict": {
            "TC1": "partial but strong saved-trace security evidence",
            "TC2": "partial but strong saved-result authority evidence",
            "TC3": "partial checker-ablation evidence",
            "TC4": "weak/partial utility evidence",
        },
        "notes": [
            "R081 does not run models, execute tools, clone benchmarks, sync datasets, or download data.",
            "Same-exposure unsafe event admissions are important because they show a tool/object ACL can expose no more objects than IntentCap and still admit unsafe protected decisions when provenance is ignored.",
            "The result supports conservative saved-trace wording, not final benchmark-scale online utility or approval-burden claims.",
        ],
    }


def _unique_unsafe_events_total(rows: list[dict[str, str]]) -> int:
    by_benchmark: dict[str, int] = {}
    for row in rows:
        benchmark = row.get("benchmark", "")
        total = _int(row.get("unsafe_events_total"))
        if total:
            by_benchmark[benchmark] = max(by_benchmark.get(benchmark, 0), total)
    return sum(by_benchmark.values())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _int(value: Any) -> int:
    if value in {"", None}:
        return 0
    return int(float(str(value)))


def _float(value: Any) -> float:
    if value in {"", None}:
        return 0.0
    return float(str(value))


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return ""


def _command_text() -> str:
    return " ".join([sys.executable, *sys.argv]) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
