"""Account for repeated read-only tau2 residuals after repair-map execution.

This is a saved-artifact analysis. It does not run a model, execute tools,
sync datasets, or change official tau2 scores. The narrow purpose is to
separate two cases that both look like candidate-selection residuals:

* a read-only idempotent tool call with identical arguments already executed
  for another reference event; and
* an exact candidate that exists but still was not selected by the planner.
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
from collections import Counter
from pathlib import Path
from typing import Any


ADJUSTMENT_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "proof_status",
    "diagnosis",
    "executed_same_call_event_ids",
    "executed_same_call_bound_reference_ids",
    "read_only_idempotent_tool",
    "accounting_class",
    "db_feasible_missing_delta",
    "adjusted_status",
    "rationale",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze tau2 repeated-state accounting")
    parser.add_argument("--run-id", default="R173")
    parser.add_argument("--source-run-id", default="R169")
    parser.add_argument(
        "--repeated-residual-csv",
        type=Path,
        default=Path("results/eval/R172/repeated_consumed_residuals.csv"),
    )
    parser.add_argument(
        "--missing-actionability-csv",
        type=Path,
        default=Path("results/eval/R170/remaining_missing_actionability.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R173"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_repeated_state_accounting(
        run_id=args.run_id,
        source_run_id=args.source_run_id,
        repeated_residual_csv=args.repeated_residual_csv,
        missing_actionability_csv=args.missing_actionability_csv,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_repeated_state_accounting(
    *,
    run_id: str,
    source_run_id: str,
    repeated_residual_csv: Path,
    missing_actionability_csv: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    repeated_rows = read_csv(repeated_residual_csv)
    actionability_rows = read_csv(missing_actionability_csv)

    adjustment_rows = [
        build_adjustment_row(source_run_id=source_run_id, row=row) for row in repeated_rows
    ]
    summary = build_summary(
        run_id=run_id,
        source_run_id=source_run_id,
        repeated_residual_csv=repeated_residual_csv,
        missing_actionability_csv=missing_actionability_csv,
        adjustment_rows=adjustment_rows,
        actionability_rows=actionability_rows,
    )

    write_csv(output_dir / "repeated_state_adjustments.csv", adjustment_rows, ADJUSTMENT_FIELDS)
    write_json(output_dir / "repeated_state_accounting_summary.json", summary)
    write_csv(
        output_dir / "input_digests.csv",
        input_digest_rows([repeated_residual_csv, missing_actionability_csv, Path(__file__)]),
        ["path", "sha256", "bytes"],
    )
    (output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    return {"adjustment_rows": adjustment_rows, "summary": summary}


def build_adjustment_row(*, source_run_id: str, row: dict[str, str]) -> dict[str, Any]:
    tool = str(row.get("tool", ""))
    diagnosis = str(row.get("diagnosis", ""))
    same_call_ids = str(row.get("executed_same_call_event_ids", ""))
    read_only = is_read_only_idempotent_tool(tool)
    same_call_executed = bool(same_call_ids.strip())

    if diagnosis == "same_tool_args_already_executed_for_different_reference" and same_call_executed:
        if read_only:
            accounting_class = "idempotent_read_already_observed"
            delta = -1
            adjusted_status = "credit_as_observed_for_adjusted_missing_accounting"
            rationale = (
                "An identical read-only get_* call already executed in the same task; "
                "crediting it changes adjusted residual accounting only, not official tau2 score."
            )
        else:
            accounting_class = "same_call_requires_state_semantics"
            delta = 0
            adjusted_status = "no_credit"
            rationale = (
                "An identical call exists, but the tool is not classified as read-only idempotent."
            )
    elif diagnosis == "existing_exact_candidate_not_selected":
        accounting_class = "planner_exact_candidate_not_selected"
        delta = 0
        adjusted_status = "still_missing"
        rationale = "No identical executed call was found; this remains a planner selection residual."
    else:
        accounting_class = "unclassified_repeated_state_residual"
        delta = 0
        adjusted_status = "still_missing"
        rationale = "Residual diagnosis is not covered by the conservative accounting rule."

    return {
        "source_run_id": source_run_id,
        "domain": row.get("domain", ""),
        "task_id": row.get("task_id", ""),
        "event_id": row.get("event_id", ""),
        "tool": tool,
        "args_json": canonical_json(row.get("args_json", "")),
        "proof_status": row.get("proof_status", ""),
        "diagnosis": diagnosis,
        "executed_same_call_event_ids": same_call_ids,
        "executed_same_call_bound_reference_ids": row.get(
            "executed_same_call_bound_reference_ids", ""
        ),
        "read_only_idempotent_tool": read_only,
        "accounting_class": accounting_class,
        "db_feasible_missing_delta": delta,
        "adjusted_status": adjusted_status,
        "rationale": rationale,
    }


def build_summary(
    *,
    run_id: str,
    source_run_id: str,
    repeated_residual_csv: Path,
    missing_actionability_csv: Path,
    adjustment_rows: list[dict[str, Any]],
    actionability_rows: list[dict[str, str]],
) -> dict[str, Any]:
    class_counts = Counter(str(row.get("accounting_class", "")) for row in adjustment_rows)
    before = sum(1 for row in actionability_rows if truthy(row.get("db_feasible", "")))
    creditable = [
        row
        for row in adjustment_rows
        if row.get("accounting_class") == "idempotent_read_already_observed"
    ]
    planner_residuals = [
        row
        for row in adjustment_rows
        if row.get("accounting_class") == "planner_exact_candidate_not_selected"
    ]
    credit_delta = sum(int(row.get("db_feasible_missing_delta", 0)) for row in adjustment_rows)
    return {
        "run_id": run_id,
        "source_run_id": source_run_id,
        "analysis": "saved tau2 repeated-state accounting audit",
        "repeated_residual_csv": str(repeated_residual_csv),
        "missing_actionability_csv": str(missing_actionability_csv),
        "project_git_commit": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "machine": platform.platform(),
        "model_or_tool_execution": False,
        "dataset_sync": False,
        "official_tau2_score_changed": False,
        "input_repeated_state_residuals": len(adjustment_rows),
        "accounting_class_counts": dict(sorted(class_counts.items())),
        "current_db_feasible_missing_before_accounting": before,
        "idempotent_same_call_creditable": len(creditable),
        "planner_selection_residuals": len(planner_residuals),
        "non_idempotent_same_call_creditable": 0,
        "adjusted_db_feasible_missing_after_idempotent_read_credit": before + credit_delta,
        "creditable_event_ids": [row["event_id"] for row in creditable],
        "planner_residual_event_ids": [row["event_id"] for row in planner_residuals],
        "notes": [
            "Only read-only get_* tools are credited when the same tool arguments already executed in the same task.",
            "This is adjusted residual accounting, not a change to official tau2 tool-oracle scoring.",
            "Write operations and exact candidates that were not executed receive no accounting credit.",
        ],
    }


def is_read_only_idempotent_tool(tool: str) -> bool:
    return tool.startswith("get_")


def canonical_json(raw: Any) -> str:
    try:
        parsed = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return str(raw or "")
    return json.dumps(parsed, sort_keys=True) if isinstance(parsed, dict) else str(raw or "")


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def input_digest_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        data = path.read_bytes()
        rows.append({"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return rows


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
