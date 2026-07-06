"""Compare reference executions before and after bounded activation runs.

This is a saved-artifact audit. It reads completed tau2 task-loop outputs only;
it does not run a model, execute tools, sync datasets, or mint authority. The
goal is to explain whether a new activation mechanism improves exact reference
coverage or merely shifts the planner trajectory.
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


DELTA_FIELDS = [
    "baseline_run",
    "current_run",
    "domain",
    "task_id",
    "event_id",
    "delta_class",
    "tool",
    "args_json",
    "baseline_round",
    "baseline_index",
    "baseline_binding_source",
    "baseline_binding_reason",
    "current_round",
    "current_index",
    "current_binding_source",
    "current_binding_reason",
]

TASK_FIELDS = [
    "baseline_run",
    "current_run",
    "domain",
    "task_id",
    "baseline_executed_references",
    "current_executed_references",
    "net_delta",
    "gained_event_ids",
    "lost_event_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit post-activation reference deltas")
    parser.add_argument("--run-id", default="R198_delta")
    parser.add_argument("--current-run-dir", type=Path, default=Path("results/eval/R197"))
    parser.add_argument(
        "--baseline-run-dir",
        action="append",
        type=Path,
        default=None,
        help="Baseline task-loop run directory. May be passed multiple times.",
    )
    parser.add_argument(
        "--residual-summary-json",
        type=Path,
        default=Path("results/eval/R198/repair_map_residual_summary.json"),
    )
    parser.add_argument(
        "--repeated-summary-json",
        type=Path,
        default=Path("results/eval/R198/repeated_state_accounting/repeated_state_accounting_summary.json"),
    )
    parser.add_argument(
        "--activation-summary-json",
        type=Path,
        default=Path("results/eval/R198/tool_activation_gaps/tool_activation_summary.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R198/post_activation_delta"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_post_activation_delta(
        run_id=args.run_id,
        current_run_dir=args.current_run_dir,
        baseline_run_dirs=args.baseline_run_dir
        or [Path("results/eval/R187"), Path("results/eval/R180")],
        residual_summary_json=args.residual_summary_json,
        repeated_summary_json=args.repeated_summary_json,
        activation_summary_json=args.activation_summary_json,
        output_dir=args.output_dir,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_post_activation_delta(
    *,
    run_id: str,
    current_run_dir: Path,
    baseline_run_dirs: list[Path],
    residual_summary_json: Path | None,
    repeated_summary_json: Path | None,
    activation_summary_json: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    current = load_run(current_run_dir)
    all_delta_rows: list[dict[str, Any]] = []
    all_task_rows: list[dict[str, Any]] = []
    baseline_summaries: dict[str, Any] = {}
    for baseline_dir in baseline_run_dirs:
        baseline = load_run(baseline_dir)
        baseline_summaries[baseline["run_id"]] = baseline["summary"]
        delta_rows = compare_runs(baseline=baseline, current=current)
        task_rows = build_task_rows(baseline=baseline, current=current, delta_rows=delta_rows)
        all_delta_rows.extend(delta_rows)
        all_task_rows.extend(task_rows)

    residual_summary = read_json_if_exists(residual_summary_json)
    repeated_summary = read_json_if_exists(repeated_summary_json)
    activation_summary = read_json_if_exists(activation_summary_json)
    summary = build_summary(
        run_id=run_id,
        current=current,
        baseline_summaries=baseline_summaries,
        delta_rows=all_delta_rows,
        task_rows=all_task_rows,
        residual_summary=residual_summary,
        repeated_summary=repeated_summary,
        activation_summary=activation_summary,
        output_dir=output_dir,
    )

    write_csv(output_dir / "post_activation_reference_delta.csv", all_delta_rows, DELTA_FIELDS)
    write_csv(output_dir / "task_post_activation_reference_delta.csv", all_task_rows, TASK_FIELDS)
    write_json(output_dir / "post_activation_delta_summary.json", summary)
    write_csv(
        output_dir / "input_digests.csv",
        input_digest_rows(
            [
                current_run_dir / "action_results.csv",
                current_run_dir / "task_gateway_summary.json",
                *[
                    path
                    for baseline_dir in baseline_run_dirs
                    for path in [
                        baseline_dir / "action_results.csv",
                        baseline_dir / "task_gateway_summary.json",
                    ]
                ],
                *[
                    path
                    for path in [
                        residual_summary_json,
                        repeated_summary_json,
                        activation_summary_json,
                        Path(__file__),
                    ]
                    if path is not None
                ],
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    return {"summary": summary, "delta_rows": all_delta_rows, "task_rows": all_task_rows}


def load_run(run_dir: Path) -> dict[str, Any]:
    summary = read_json_if_exists(run_dir / "task_gateway_summary.json")
    run_id = str(summary.get("run_id") or run_dir.name)
    action_rows = read_csv(run_dir / "action_results.csv")
    executed_by_event = {
        str(row.get("bound_reference_event_id", "")): row
        for row in action_rows
        if executed_without_error(row) and str(row.get("bound_reference_event_id", ""))
    }
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "summary": summary,
        "action_rows": action_rows,
        "executed_by_event": executed_by_event,
    }


def compare_runs(*, baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    baseline_events = baseline["executed_by_event"]
    current_events = current["executed_by_event"]
    delta_rows: list[dict[str, Any]] = []
    for event_id in sorted(set(baseline_events) ^ set(current_events)):
        baseline_row = baseline_events.get(event_id, {})
        current_row = current_events.get(event_id, {})
        row = current_row or baseline_row
        delta_class = "gained_reference_execution" if current_row else "lost_reference_execution"
        delta_rows.append(
            {
                "baseline_run": baseline["run_id"],
                "current_run": current["run_id"],
                "domain": row.get("domain", ""),
                "task_id": row.get("task_id", ""),
                "event_id": event_id,
                "delta_class": delta_class,
                "tool": row.get("model_tool", ""),
                "args_json": canonical_json(row.get("model_args_json", "{}")),
                "baseline_round": baseline_row.get("round", ""),
                "baseline_index": baseline_row.get("index", ""),
                "baseline_binding_source": binding_source(baseline_row),
                "baseline_binding_reason": binding_reason(baseline_row),
                "current_round": current_row.get("round", ""),
                "current_index": current_row.get("index", ""),
                "current_binding_source": binding_source(current_row),
                "current_binding_reason": binding_reason(current_row),
            }
        )
    return delta_rows


def build_task_rows(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    delta_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_counts = task_counts(baseline["executed_by_event"].values())
    current_counts = task_counts(current["executed_by_event"].values())
    gained: dict[tuple[str, str], list[str]] = defaultdict(list)
    lost: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in delta_rows:
        key = (str(row.get("domain", "")), str(row.get("task_id", "")))
        if row.get("delta_class") == "gained_reference_execution":
            gained[key].append(str(row.get("event_id", "")))
        else:
            lost[key].append(str(row.get("event_id", "")))
    task_rows = []
    for key in sorted(set(baseline_counts) | set(current_counts) | set(gained) | set(lost)):
        baseline_count = baseline_counts.get(key, 0)
        current_count = current_counts.get(key, 0)
        task_rows.append(
            {
                "baseline_run": baseline["run_id"],
                "current_run": current["run_id"],
                "domain": key[0],
                "task_id": key[1],
                "baseline_executed_references": baseline_count,
                "current_executed_references": current_count,
                "net_delta": current_count - baseline_count,
                "gained_event_ids": "|".join(sorted(gained.get(key, []))),
                "lost_event_ids": "|".join(sorted(lost.get(key, []))),
            }
        )
    return task_rows


def build_summary(
    *,
    run_id: str,
    current: dict[str, Any],
    baseline_summaries: dict[str, Any],
    delta_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    residual_summary: dict[str, Any],
    repeated_summary: dict[str, Any],
    activation_summary: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    delta_counts = Counter(str(row.get("delta_class", "")) for row in delta_rows)
    per_baseline_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in delta_rows:
        per_baseline_counts[str(row.get("baseline_run", ""))][str(row.get("delta_class", ""))] += 1
    gained_write_rows = [
        row
        for row in delta_rows
        if row.get("delta_class") == "gained_reference_execution"
        and row.get("current_binding_source") == "tool_activation"
        and str(row.get("tool", "")).startswith(("return_", "modify_", "create_", "delete_", "send_"))
    ]
    return {
        "analysis": "saved tau2 post-activation reference-delta audit",
        "run_id": run_id,
        "current_run": current["run_id"],
        "current_run_dir": current["run_dir"],
        "baseline_runs": sorted(baseline_summaries),
        "baseline_summaries": baseline_summaries,
        "delta_class_counts": dict(delta_counts),
        "delta_class_counts_by_baseline": {
            key: dict(value) for key, value in sorted(per_baseline_counts.items())
        },
        "unique_gained_event_ids": sorted(
            {
                str(row.get("event_id", ""))
                for row in delta_rows
                if row.get("delta_class") == "gained_reference_execution"
            }
        ),
        "unique_lost_event_ids": sorted(
            {
                str(row.get("event_id", ""))
                for row in delta_rows
                if row.get("delta_class") == "lost_reference_execution"
            }
        ),
        "unique_gained_write_activation_event_ids": sorted(
            {str(row.get("event_id", "")) for row in gained_write_rows}
        ),
        "tasks_with_negative_delta": sum(1 for row in task_rows if int(row["net_delta"]) < 0),
        "tasks_with_positive_delta": sum(1 for row in task_rows if int(row["net_delta"]) > 0),
        "current_db_feasible_missing_reference_actions": residual_summary.get(
            "current_db_feasible_missing_reference_actions"
        ),
        "current_db_feasible_actionability_class_counts": residual_summary.get(
            "current_db_feasible_actionability_class_counts", {}
        ),
        "adjusted_db_feasible_missing_after_idempotent_read_credit": repeated_summary.get(
            "adjusted_db_feasible_missing_after_idempotent_read_credit"
        ),
        "tool_activation_gaps_after_current_run": activation_summary.get(
            "input_tool_activation_gaps"
        ),
        "write_or_high_impact_activation_blockers_after_current_run": activation_summary.get(
            "write_or_high_impact_activation_blockers"
        ),
        "interpretation": interpretation(
            delta_rows=delta_rows,
            residual_summary=residual_summary,
            repeated_summary=repeated_summary,
            activation_summary=activation_summary,
        ),
        "no_dataset_sync": True,
        "no_model_execution": True,
        "no_tool_execution": True,
        "official_tau2_score_changed": False,
        "output_dir": str(output_dir),
        "project_head": git_commit(),
        "git_status": git_status(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "script_sha256": sha256_file(Path(__file__)),
    }


def interpretation(
    *,
    delta_rows: list[dict[str, Any]],
    residual_summary: dict[str, Any],
    repeated_summary: dict[str, Any],
    activation_summary: dict[str, Any],
) -> str:
    gained_write = [
        row
        for row in delta_rows
        if row.get("delta_class") == "gained_reference_execution"
        and row.get("current_binding_source") == "tool_activation"
    ]
    lost = [
        row for row in delta_rows if row.get("delta_class") == "lost_reference_execution"
    ]
    activation_gaps = int(activation_summary.get("input_tool_activation_gaps") or 0)
    adjusted_missing = repeated_summary.get(
        "adjusted_db_feasible_missing_after_idempotent_read_credit"
    )
    db_missing = residual_summary.get("current_db_feasible_missing_reference_actions")
    if gained_write and lost:
        return (
            "bounded write activation executed safely, but exact reference coverage did "
            "not improve because the current run lost other planner-selected read "
            f"references; residuals are now planning/candidate-generation dominated "
            f"({db_missing} DB-feasible missing, {adjusted_missing} after read credit, "
            f"{activation_gaps} tool-activation gaps)."
        )
    if gained_write:
        return "bounded write activation added reference coverage without observed lost references."
    return "no bounded write activation coverage gain was observed in the current run."


def task_counts(rows: Any) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        counts[(str(row.get("domain", "")), str(row.get("task_id", "")))] += 1
    return counts


def binding_source(row: dict[str, str]) -> str:
    if not row:
        return ""
    if truthy(row.get("tool_activation_binding_attempted", "")):
        return "tool_activation"
    if truthy(row.get("runtime_binding_attempted", "")):
        return "runtime_binding"
    markers = parse_json_object(row.get("intentcap_markers_json", "{}"))
    if markers.get("_intentcap_synthesized_from_repair_map"):
        return "repair_map"
    if markers.get("_intentcap_synthesized_from_compiler_lease_hint"):
        return "compiler_lease_hint"
    return "direct_or_static_lease"


def binding_reason(row: dict[str, str]) -> str:
    if not row:
        return ""
    if truthy(row.get("tool_activation_binding_attempted", "")):
        return str(row.get("tool_activation_binding_reason", ""))
    if truthy(row.get("runtime_binding_attempted", "")):
        return str(row.get("runtime_binding_reason", ""))
    return str(row.get("gateway_reason", ""))


def executed_without_error(row: dict[str, str]) -> bool:
    return truthy(row.get("executed", "")) and not truthy(row.get("tool_error", ""))


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def canonical_json(value: str) -> str:
    parsed = parse_json_object(value)
    return json.dumps(parsed, sort_keys=True)


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def input_digest_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        rows.append(
            {
                "path": str(path),
                "sha256": sha256_file(path) if path.exists() else "missing",
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    return run_command(["git", "rev-parse", "HEAD"])


def git_status() -> str:
    return run_command(["git", "status", "--short", "--branch"])


def run_command(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return "unknown"


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv])


if __name__ == "__main__":
    raise SystemExit(main())
