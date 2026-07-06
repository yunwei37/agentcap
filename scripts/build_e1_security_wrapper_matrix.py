"""Build the E1 same-event security wrapper comparison matrix.

This script consolidates saved InjecAgent and MCPTox authority-minimization
summaries into one paper-facing security table. It compares IntentCap against
exact-tool, toolkit/server, and global/static wrappers on the same protected
events. It does not run a model, execute tools, clone repositories, sync
datasets, or download data.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_INJECAGENT_SUMMARY = Path("results/injecagent/R019/authority_summary.json")
DEFAULT_MCPTOX_SUMMARY = Path("results/mcptox/R020/authority_summary.json")

MATRIX_FIELDS = [
    "benchmark",
    "workload_family",
    "policy",
    "policy_family",
    "source_run",
    "matched_event_count",
    "dangerous_accepted",
    "dangerous_blocked",
    "dangerous_accept_rate",
    "dangerous_block_rate",
    "control_provenance_checked",
    "argument_event_id_checked",
    "broad_arguments",
    "mean_exposed_tools",
    "median_exposed_tools",
    "p95_exposed_tools",
    "max_exposed_tools",
    "exposed_tool_slots_total",
    "exposure_over_intentcap",
    "admitted_by_mode_json",
    "admitted_by_risk_json",
    "notes",
]

FAMILY_FIELDS = [
    "policy_family",
    "rows",
    "benchmarks",
    "matched_event_count",
    "dangerous_accepted",
    "dangerous_blocked",
    "dangerous_accept_rate",
    "mean_exposed_tools_weighted",
    "max_exposed_tools",
    "all_rows_check_control_provenance",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 security wrapper matrix")
    parser.add_argument("--run-id", default="R202E1")
    parser.add_argument("--injecagent-summary", type=Path, default=DEFAULT_INJECAGENT_SUMMARY)
    parser.add_argument("--mcptox-summary", type=Path, default=DEFAULT_MCPTOX_SUMMARY)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build_matrix(
        run_id=args.run_id,
        injecagent_summary=args.injecagent_summary,
        mcptox_summary=args.mcptox_summary,
    )
    write_outputs(args.output_dir, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def build_matrix(
    *,
    run_id: str,
    injecagent_summary: Path = DEFAULT_INJECAGENT_SUMMARY,
    mcptox_summary: Path = DEFAULT_MCPTOX_SUMMARY,
) -> dict[str, Any]:
    inputs = [injecagent_summary, mcptox_summary]
    summaries = [
        ("InjecAgent", "tool_response_injection", "R019", json.loads(injecagent_summary.read_text())),
        ("MCPTox", "mcp_tool_poisoning", "R020", json.loads(mcptox_summary.read_text())),
    ]
    matrix_rows: list[dict[str, Any]] = []
    for benchmark, family, source_run, summary in summaries:
        matrix_rows.extend(_rows_from_summary(benchmark, family, source_run, summary))

    family_rows = _family_summary_rows(matrix_rows)
    summary = _summary(run_id, matrix_rows, family_rows, inputs)
    return {
        "summary": summary,
        "matrix_rows": matrix_rows,
        "family_rows": family_rows,
        "input_digests": [_file_digest(path) for path in inputs],
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "e1_security_wrapper_matrix.csv", result["matrix_rows"], MATRIX_FIELDS)
    _write_rows(output_dir / "e1_security_policy_family_summary.csv", result["family_rows"], FAMILY_FIELDS)
    _write_rows(output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "e1_security_wrapper_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())


def _rows_from_summary(
    benchmark: str,
    workload_family: str,
    source_run: str,
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy in summary.get("baseline_order", []):
        baseline = summary.get("baselines", {}).get(policy, {})
        matched = _event_count(benchmark, baseline)
        accepted = _accepted_count(benchmark, baseline)
        blocked = max(0, matched - accepted)
        mean_exposed = _float(
            baseline.get("mean_exposed_tools_per_case")
            or baseline.get("mean_exposed_tools_per_event")
        )
        median_exposed = _float(
            baseline.get("median_exposed_tools_per_case")
            or baseline.get("median_exposed_tools_per_event")
        )
        p95_exposed = _float(
            baseline.get("p95_exposed_tools_per_case")
            or baseline.get("p95_exposed_tools_per_event")
        )
        max_exposed = _float(
            baseline.get("max_exposed_tools_per_case")
            or baseline.get("max_exposed_tools_per_event")
        )
        exposure_over_intentcap = _float(
            baseline.get("tool_slot_over_intentcap_ratio")
            or baseline.get("mean_tool_exposure_over_intentcap")
        )
        row = {
            "benchmark": benchmark,
            "workload_family": workload_family,
            "policy": policy,
            "policy_family": _policy_family(policy),
            "source_run": source_run,
            "matched_event_count": matched,
            "dangerous_accepted": accepted,
            "dangerous_blocked": blocked,
            "dangerous_accept_rate": _rate(accepted, matched),
            "dangerous_block_rate": _rate(blocked, matched),
            "control_provenance_checked": bool(baseline.get("control_provenance_checked")),
            "argument_event_id_checked": bool(baseline.get("argument_event_id_checked", False)),
            "broad_arguments": bool(baseline.get("broad_arguments", False)),
            "mean_exposed_tools": mean_exposed,
            "median_exposed_tools": median_exposed,
            "p95_exposed_tools": p95_exposed,
            "max_exposed_tools": max_exposed,
            "exposed_tool_slots_total": _int(baseline.get("exposed_tool_slots_total", "")),
            "exposure_over_intentcap": exposure_over_intentcap,
            "admitted_by_mode_json": _stable_json(baseline.get("admitted_by_mode", {})),
            "admitted_by_risk_json": _stable_json(
                baseline.get("admitted_by_attack_family")
                or baseline.get("admitted_by_security_risk")
                or {}
            ),
            "notes": _row_note(benchmark, policy),
        }
        rows.append(row)
    return rows


def _event_count(benchmark: str, baseline: dict[str, Any]) -> int:
    if benchmark == "InjecAgent":
        return _int(baseline.get("protected_attack_events"))
    return _int(baseline.get("protected_events"))


def _accepted_count(benchmark: str, baseline: dict[str, Any]) -> int:
    if benchmark == "InjecAgent":
        return _int(baseline.get("admitted_attack_events"))
    return _int(baseline.get("admitted_events"))


def _policy_family(policy: str) -> str:
    mapping = {
        "intentcap_one_shot": "intentcap",
        "intentcap_provenance": "intentcap",
        "task_tool_allowlist": "exact_or_task_tool_acl",
        "exact_tool_acl": "exact_or_task_tool_acl",
        "toolkit_allowlist": "toolkit_or_server_allowlist",
        "authentic_server_allowlist": "toolkit_or_server_allowlist",
        "observed_server_allowlist": "toolkit_or_server_allowlist",
        "benchmark_user_tools": "benchmark_or_observed_static_acl",
        "observed_trace_tools": "benchmark_or_observed_static_acl",
        "global_authentic_tools": "benchmark_or_observed_static_acl",
        "global_observed_tools": "benchmark_or_observed_static_acl",
        "catalog_all_tools": "global_catalog_acl",
    }
    return mapping.get(policy, "other")


def _row_note(benchmark: str, policy: str) -> str:
    if policy in {"intentcap_one_shot", "intentcap_provenance"}:
        return "IntentCap row checks trusted control provenance for protected decisions."
    if policy in {"task_tool_allowlist", "exact_tool_acl"}:
        return "Exact object/tool ACL row keeps object scope narrow but ignores context-to-decision provenance."
    if policy in {"toolkit_allowlist", "authentic_server_allowlist", "observed_server_allowlist"}:
        return "Toolkit/server row widens object scope and ignores protected-decision provenance."
    return f"{benchmark} broad static row ignores protected-decision provenance."


def _family_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["policy_family"])].append(row)

    family_rows: list[dict[str, Any]] = []
    for family, family_rows_raw in sorted(grouped.items()):
        matched = sum(_int(row["matched_event_count"]) for row in family_rows_raw)
        accepted = sum(_int(row["dangerous_accepted"]) for row in family_rows_raw)
        blocked = sum(_int(row["dangerous_blocked"]) for row in family_rows_raw)
        weighted_exposure = (
            sum(_float(row["mean_exposed_tools"]) * _int(row["matched_event_count"]) for row in family_rows_raw)
            / matched
            if matched
            else 0.0
        )
        family_rows.append(
            {
                "policy_family": family,
                "rows": len(family_rows_raw),
                "benchmarks": "|".join(sorted({str(row["benchmark"]) for row in family_rows_raw})),
                "matched_event_count": matched,
                "dangerous_accepted": accepted,
                "dangerous_blocked": blocked,
                "dangerous_accept_rate": _rate(accepted, matched),
                "mean_exposed_tools_weighted": round(weighted_exposure, 6),
                "max_exposed_tools": max(_float(row["max_exposed_tools"]) for row in family_rows_raw),
                "all_rows_check_control_provenance": all(
                    bool(row["control_provenance_checked"]) for row in family_rows_raw
                ),
            }
        )
    return family_rows


def _summary(
    run_id: str,
    matrix_rows: list[dict[str, Any]],
    family_rows: list[dict[str, Any]],
    input_paths: list[Path],
) -> dict[str, Any]:
    intentcap = [
        row for row in matrix_rows
        if row["policy_family"] == "intentcap"
    ]
    exact_acl = [
        row for row in matrix_rows
        if row["policy_family"] == "exact_or_task_tool_acl"
    ]
    total_events = sum(_int(row["matched_event_count"]) for row in intentcap)
    total_intentcap_accepts = sum(_int(row["dangerous_accepted"]) for row in intentcap)
    total_exact_acl_accepts = sum(_int(row["dangerous_accepted"]) for row in exact_acl)
    by_benchmark = Counter(str(row["benchmark"]) for row in matrix_rows)
    return {
        "run_id": run_id,
        "analysis": "E1 same-event security wrapper comparison",
        "matrix_rows": len(matrix_rows),
        "family_rows": len(family_rows),
        "rows_by_benchmark": dict(sorted(by_benchmark.items())),
        "intentcap_dangerous_accepted": total_intentcap_accepts,
        "exact_or_task_tool_acl_dangerous_accepted": total_exact_acl_accepts,
        "intentcap_matched_events": total_events,
        "intentcap_accept_rate": _rate(total_intentcap_accepts, total_events),
        "exact_or_task_tool_acl_accept_rate": _rate(total_exact_acl_accepts, total_events),
        "same_event_security_delta": total_exact_acl_accepts - total_intentcap_accepts,
        "no_dataset_sync": True,
        "not_a_fresh_online_run": True,
        "notes": [
            "This is an E1 security-side matrix over saved protected events, not a utility result.",
            "Rows compare policy wrappers on the same event sets exported by R019 and R020.",
            "The exact/tool ACL family is intentionally narrow on object exposure but lacks control-provenance checks.",
        ],
        "input_digests": [_file_digest(path) for path in input_paths],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }


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


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 8) if denominator else 0.0


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
