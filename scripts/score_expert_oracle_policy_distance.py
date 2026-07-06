"""Score policy rows against adjudicated expert-oracle lease rows.

This E2 utility runs after expert labels have been completed, adjudicated, and
exported with ``export_adjudicated_expert_oracle.py``. It compares each
sample/policy row against the adjudicated oracle row for that sample and writes
per-row and per-policy distance summaries. It does not create labels, run
models, execute tools, clone repositories, sync datasets, or download data.
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
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_ORACLE = Path("results/eval/R201/adjudicated_expert_oracle.csv")

DISTANCE_FIELDS = [
    "sample_id",
    "benchmark",
    "workload_family",
    "policy",
    "status",
    "extra_operations",
    "missing_operations",
    "extra_objects",
    "missing_objects",
    "extra_sinks",
    "missing_sinks",
    "extra_influence_modes",
    "missing_influence_modes",
    "extra_decision_classes",
    "missing_decision_classes",
    "budget_extra_invocations",
    "budget_missing_invocations",
    "argument_constraint_mismatch",
    "extra_authority_units",
    "coverage_gap_units",
    "oracle_distance_score",
    "notes",
]

POLICY_SUMMARY_FIELDS = [
    "policy",
    "rows",
    "ok_rows",
    "missing_oracle_rows",
    "total_extra_authority_units",
    "total_coverage_gap_units",
    "argument_constraint_mismatches",
    "total_oracle_distance_score",
    "mean_oracle_distance_score",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Score policies against expert oracle rows")
    parser.add_argument("--run-id", default="R202")
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--policies", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = score_policy_distance(
        run_id=args.run_id,
        oracle_path=args.oracle,
        policy_path=args.policies,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["score_status"] == "ok" else 1


def score_policy_distance(
    *,
    run_id: str,
    oracle_path: Path,
    policy_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    oracle_rows = _read_csv(oracle_path)
    policy_rows = _read_csv(policy_path)
    oracle_by_sample = {row["sample_id"]: row for row in oracle_rows}

    distance_rows = [
        _score_row(oracle_by_sample.get(row.get("sample_id", "")), row)
        for row in policy_rows
    ]
    policy_summary_rows = _policy_summary_rows(distance_rows)
    missing_oracle_rows = sum(1 for row in distance_rows if row["status"] != "ok")
    summary = {
        "run_id": run_id,
        "analysis": "expert-oracle policy distance scoring",
        "oracle_rows": len(oracle_rows),
        "policy_rows": len(policy_rows),
        "scored_rows": sum(1 for row in distance_rows if row["status"] == "ok"),
        "missing_oracle_rows": missing_oracle_rows,
        "policies": sorted({row.get("policy", "") for row in policy_rows}),
        "score_status": "ok" if missing_oracle_rows == 0 else "incomplete",
        "no_dataset_sync": True,
        "notes": [
            "This scorer compares policy rows to adjudicated expert-oracle rows.",
            "Distance is a decomposed proxy over exposed operations, objects, sinks, influence modes, decision classes, budgets, and argument constraints.",
            "It should be run only after independent expert labels are adjudicated and exported.",
        ],
        "input_digests": [_file_digest(oracle_path), _file_digest(policy_path)],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "expert_policy_oracle_distance.csv", distance_rows, DISTANCE_FIELDS)
    _write_rows(
        output_dir / "expert_policy_oracle_summary.csv",
        policy_summary_rows,
        POLICY_SUMMARY_FIELDS,
    )
    _write_rows(output_dir / "input_digests.csv", summary["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "expert_policy_distance_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())

    return {
        "summary": summary,
        "distance_rows": distance_rows,
        "policy_summary_rows": policy_summary_rows,
    }


def _score_row(oracle: dict[str, str] | None, policy: dict[str, str]) -> dict[str, Any]:
    sample_id = policy.get("sample_id", "")
    policy_name = policy.get("policy") or policy.get("baseline") or "unknown_policy"
    base = {
        "sample_id": sample_id,
        "benchmark": policy.get("benchmark", ""),
        "workload_family": policy.get("workload_family", ""),
        "policy": policy_name,
    }
    if oracle is None:
        return {
            **base,
            "status": "missing_oracle",
            "extra_operations": "",
            "missing_operations": "",
            "extra_objects": "",
            "missing_objects": "",
            "extra_sinks": "",
            "missing_sinks": "",
            "extra_influence_modes": "",
            "missing_influence_modes": "",
            "extra_decision_classes": "",
            "missing_decision_classes": "",
            "budget_extra_invocations": "",
            "budget_missing_invocations": "",
            "argument_constraint_mismatch": "",
            "extra_authority_units": "",
            "coverage_gap_units": "",
            "oracle_distance_score": "",
            "notes": f"no adjudicated oracle row for sample_id={sample_id}",
        }

    operations = _compare_set(policy, oracle, "lease_operations")
    objects = _compare_set(policy, oracle, "lease_objects")
    sinks = _compare_set(policy, oracle, "lease_allowed_sinks")
    modes = _compare_set(policy, oracle, "influence_modes")
    decisions = _compare_set(policy, oracle, "decision_classes")
    policy_budget = _parse_int(policy.get("budget_invocations_total", ""))
    oracle_budget = _parse_int(oracle.get("budget_invocations_total", ""))
    budget_extra = max(0, policy_budget - oracle_budget)
    budget_missing = max(0, oracle_budget - policy_budget)
    argument_mismatch = int(
        _canonical_jsonish(policy.get("lease_argument_constraints_json", ""))
        != _canonical_jsonish(oracle.get("lease_argument_constraints_json", ""))
    )

    extra_units = (
        len(operations["extra"])
        + len(objects["extra"])
        + len(sinks["extra"])
        + len(modes["extra"])
        + len(decisions["extra"])
        + budget_extra
    )
    gap_units = (
        len(operations["missing"])
        + len(objects["missing"])
        + len(sinks["missing"])
        + len(modes["missing"])
        + len(decisions["missing"])
        + budget_missing
    )
    distance = (10 * extra_units) + (10 * gap_units) + (5 * argument_mismatch)

    return {
        **base,
        "benchmark": policy.get("benchmark") or oracle.get("benchmark", ""),
        "workload_family": policy.get("workload_family") or oracle.get("workload_family", ""),
        "status": "ok",
        "extra_operations": _join(operations["extra"]),
        "missing_operations": _join(operations["missing"]),
        "extra_objects": _join(objects["extra"]),
        "missing_objects": _join(objects["missing"]),
        "extra_sinks": _join(sinks["extra"]),
        "missing_sinks": _join(sinks["missing"]),
        "extra_influence_modes": _join(modes["extra"]),
        "missing_influence_modes": _join(modes["missing"]),
        "extra_decision_classes": _join(decisions["extra"]),
        "missing_decision_classes": _join(decisions["missing"]),
        "budget_extra_invocations": budget_extra,
        "budget_missing_invocations": budget_missing,
        "argument_constraint_mismatch": argument_mismatch,
        "extra_authority_units": extra_units,
        "coverage_gap_units": gap_units,
        "oracle_distance_score": distance,
        "notes": "",
    }


def _policy_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["policy"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for policy, policy_rows in sorted(grouped.items()):
        ok_rows = [row for row in policy_rows if row["status"] == "ok"]
        total_distance = sum(int(row["oracle_distance_score"]) for row in ok_rows)
        total_extra = sum(int(row["extra_authority_units"]) for row in ok_rows)
        total_gap = sum(int(row["coverage_gap_units"]) for row in ok_rows)
        mismatches = sum(int(row["argument_constraint_mismatch"]) for row in ok_rows)
        summary_rows.append(
            {
                "policy": policy,
                "rows": len(policy_rows),
                "ok_rows": len(ok_rows),
                "missing_oracle_rows": len(policy_rows) - len(ok_rows),
                "total_extra_authority_units": total_extra,
                "total_coverage_gap_units": total_gap,
                "argument_constraint_mismatches": mismatches,
                "total_oracle_distance_score": total_distance,
                "mean_oracle_distance_score": (
                    round(total_distance / len(ok_rows), 6) if ok_rows else ""
                ),
            }
        )
    return summary_rows


def _compare_set(policy: dict[str, str], oracle: dict[str, str], field: str) -> dict[str, set[str]]:
    policy_values = _split(policy.get(field, ""))
    oracle_values = _split(oracle.get(field, ""))
    return {
        "extra": policy_values - oracle_values,
        "missing": oracle_values - policy_values,
    }


def _split(value: str) -> set[str]:
    return {item.strip() for item in str(value).split("|") if item.strip()}


def _join(values: set[str]) -> str:
    return "|".join(sorted(values))


def _parse_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _canonical_jsonish(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    try:
        return json.dumps(_normalize_constraints(json.loads(text)), sort_keys=True, separators=(",", ":"))
    except json.JSONDecodeError:
        return text


def _normalize_constraints(value: Any) -> Any:
    """Drop scorer/provenance metadata that is not part of lease authority."""
    if isinstance(value, list):
        return [_normalize_constraints(item) for item in value]
    if isinstance(value, dict):
        ignored_keys = {"source_baseline"}
        return {
            key: _normalize_constraints(item)
            for key, item in value.items()
            if key not in ignored_keys
        }
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
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


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _git_status() -> str:
    try:
        return subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv])


if __name__ == "__main__":
    raise SystemExit(main())
