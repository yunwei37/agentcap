"""Analyze tau2 missing-tool activation gaps from saved task-loop artifacts.

This is a saved-artifact analysis. It does not run a model, execute tools,
sync datasets, or mint authority. The goal is to split tool-activation gaps
into conservative next-step candidates:

* read-only tools whose concrete argument values are already visible in saved
  task/tool-result context and whose schema exists in the local tool catalog;
* write or high-impact tools, which remain blocked until a stronger value-proof
  and policy activation path exists.
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


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import scripts.analyze_tau2_candidate_generation_repair as repair_analyzer  # noqa: E402
from analyze_tau2_visible_lease_compiler import _parse_assistant_tools  # noqa: E402


ACTIVATION_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "actionability_class",
    "tool_type",
    "tool_catalog_available",
    "active_prompt_tool_visible",
    "required_args",
    "required_args_satisfied",
    "earliest_arg_visible_step",
    "arg_visible_steps",
    "all_arg_values_visible",
    "arg_value_sources_json",
    "activation_eligible",
    "activation_kind",
    "proof_status",
    "candidate_json",
    "next_experiment_target",
]

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "tool_activation_gaps",
    "eligible_read_activation_candidates",
    "write_or_high_impact_activation_blockers",
    "missing_visibility_blockers",
    "activation_event_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze tau2 tool-activation gaps")
    parser.add_argument("--run-id", default="R174")
    parser.add_argument(
        "--actionability-csv",
        type=Path,
        default=Path("results/eval/R170/remaining_missing_actionability.csv"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("results/eval/R169"),
        help="Saved task-loop run directory containing samples.jsonl and step prompts.",
    )
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument(
        "--prior-adjusted-missing",
        type=int,
        default=17,
        help="Adjusted missing count after R173 idempotent-read accounting.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R174"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_tool_activation_gaps(
        run_id=args.run_id,
        actionability_csv=args.actionability_csv,
        run_dir=args.run_dir,
        benchmark_dir=args.benchmark_dir,
        prior_adjusted_missing=args.prior_adjusted_missing,
        output_dir=args.output_dir,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "tool_activation_candidates.csv", result["activation_rows"], ACTIVATION_FIELDS)
    write_csv(args.output_dir / "task_tool_activation_summary.csv", result["task_rows"], TASK_FIELDS)
    write_json(args.output_dir / "tool_activation_summary.json", result["summary"])
    write_csv(
        args.output_dir / "input_digests.csv",
        input_digest_rows(
            [
                args.actionability_csv,
                args.run_dir / "samples.jsonl",
                *tool_source_paths(args.benchmark_dir),
                Path(__file__),
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (args.output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_tool_activation_gaps(
    *,
    run_id: str,
    actionability_csv: Path,
    run_dir: Path,
    benchmark_dir: Path,
    prior_adjusted_missing: int,
    output_dir: Path,
) -> dict[str, Any]:
    actionability_rows = read_csv(actionability_csv)
    records_by_task = repair_analyzer.load_records_by_task(run_dir)
    tool_catalog = load_tool_catalog(benchmark_dir)
    activation_rows = [
        build_activation_row(
            row=row,
            record=records_by_task.get(repair_analyzer.task_key(row), {}),
            run_dir=run_dir,
            tool_catalog=tool_catalog,
        )
        for row in actionability_rows
        if str(row.get("actionability_class", "")) == "tool_activation_gap"
        and truthy(row.get("db_feasible", ""))
    ]
    task_rows = build_task_rows(activation_rows)
    summary = build_summary(
        run_id=run_id,
        actionability_csv=actionability_csv,
        run_dir=run_dir,
        benchmark_dir=benchmark_dir,
        output_dir=output_dir,
        prior_adjusted_missing=prior_adjusted_missing,
        actionability_rows=actionability_rows,
        activation_rows=activation_rows,
        task_rows=task_rows,
    )
    return {"activation_rows": activation_rows, "task_rows": task_rows, "summary": summary}


def build_activation_row(
    *,
    row: dict[str, str],
    record: dict[str, Any],
    run_dir: Path,
    tool_catalog: dict[tuple[str, str], Any],
) -> dict[str, Any]:
    domain = str(row.get("domain", ""))
    tool = str(row.get("tool", ""))
    args = repair_analyzer.parse_json_object(row.get("args_json", "{}"))
    tool_spec = tool_catalog.get((domain, tool))
    contexts = repair_analyzer.prompt_contexts_from_record(record, run_dir=run_dir) if record else []
    required_args = list(getattr(tool_spec, "arguments", ()) or []) if tool_spec else []
    required_satisfied = all(arg in args for arg in required_args)
    active_prompt_tool_visible = any(repair_analyzer.find_tool_schema(context, tool) for context in contexts)
    visible_steps: list[str] = []
    source_by_step: dict[str, Any] = {}
    for context in contexts:
        step = str(context.get("step", ""))
        sources = repair_analyzer.value_sources(args, context)
        if all(source.get("sources") for source in sources.values()):
            visible_steps.append(step)
            source_by_step[step] = sources
    earliest_step = repair_analyzer.sorted_steps(visible_steps)[0] if visible_steps else ""
    arg_sources = source_by_step.get(earliest_step, {})
    all_values_visible = bool(earliest_step)
    tool_type = str(getattr(tool_spec, "tool_type", "")) if tool_spec else ""
    activation_kind, eligible = activation_decision(
        tool_catalog_available=tool_spec is not None,
        tool_type=tool_type,
        required_satisfied=required_satisfied,
        all_values_visible=all_values_visible,
    )
    proof_status = proof_status_for_activation(
        tool_catalog_available=tool_spec is not None,
        tool_type=tool_type,
        required_satisfied=required_satisfied,
        all_values_visible=all_values_visible,
        eligible=eligible,
    )

    return {
        "source_run_id": str(row.get("source_run_id", "")),
        "domain": domain,
        "task_id": str(row.get("task_id", "")),
        "event_id": str(row.get("event_id", "")),
        "tool": tool,
        "args_json": json.dumps(args, sort_keys=True),
        "actionability_class": str(row.get("actionability_class", "")),
        "tool_type": tool_type,
        "tool_catalog_available": tool_spec is not None,
        "active_prompt_tool_visible": active_prompt_tool_visible,
        "required_args": "|".join(required_args),
        "required_args_satisfied": required_satisfied,
        "earliest_arg_visible_step": earliest_step,
        "arg_visible_steps": "|".join(repair_analyzer.sorted_steps(visible_steps)),
        "all_arg_values_visible": all_values_visible,
        "arg_value_sources_json": json.dumps(arg_sources, sort_keys=True),
        "activation_eligible": eligible,
        "activation_kind": activation_kind,
        "proof_status": proof_status,
        "candidate_json": json.dumps({"tool": tool, "arguments": args}, sort_keys=True),
        "next_experiment_target": next_experiment_target(activation_kind),
    }


def activation_decision(
    *,
    tool_catalog_available: bool,
    tool_type: str,
    required_satisfied: bool,
    all_values_visible: bool,
) -> tuple[str, bool]:
    if not tool_catalog_available:
        return "missing_tool_catalog_schema", False
    if not required_satisfied:
        return "missing_required_argument", False
    if not all_values_visible:
        return "missing_visible_argument_evidence", False
    if tool_type == "read":
        return "read_only_tool_activation_from_visible_argument", True
    return "write_or_high_impact_tool_activation_requires_value_proof", False


def proof_status_for_activation(
    *,
    tool_catalog_available: bool,
    tool_type: str,
    required_satisfied: bool,
    all_values_visible: bool,
    eligible: bool,
) -> str:
    if not tool_catalog_available:
        return "missing_tool_catalog_schema"
    if not required_satisfied:
        return "missing_required_argument"
    if not all_values_visible:
        return "missing_visible_argument_value"
    if eligible:
        return "activation_candidate_ready"
    if tool_type != "read":
        return "write_activation_requires_structured_value_proof"
    return "not_activation_ready"


def next_experiment_target(activation_kind: str) -> str:
    if activation_kind == "read_only_tool_activation_from_visible_argument":
        return "lower_visible_read_tool_activation_to_one_shot_runtime_lease"
    if activation_kind == "write_or_high_impact_tool_activation_requires_value_proof":
        return "require_write_value_proof_before_tool_activation"
    if activation_kind == "missing_visible_argument_evidence":
        return "gather_argument_evidence_before_tool_activation"
    return "repair_tool_catalog_or_compiler_tool_selection"


def build_task_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("domain", "")), str(row.get("task_id", "")))].append(row)
    task_rows: list[dict[str, Any]] = []
    for (domain, task_id), task_rows_for_key in sorted(grouped.items()):
        eligible = [row for row in task_rows_for_key if truthy(row.get("activation_eligible", ""))]
        blockers = [
            row
            for row in task_rows_for_key
            if str(row.get("activation_kind", "")) == "write_or_high_impact_tool_activation_requires_value_proof"
        ]
        missing_visibility = [
            row
            for row in task_rows_for_key
            if str(row.get("activation_kind", "")) == "missing_visible_argument_evidence"
        ]
        task_rows.append(
            {
                "source_run_id": str(task_rows_for_key[0].get("source_run_id", "")),
                "domain": domain,
                "task_id": task_id,
                "tool_activation_gaps": len(task_rows_for_key),
                "eligible_read_activation_candidates": len(eligible),
                "write_or_high_impact_activation_blockers": len(blockers),
                "missing_visibility_blockers": len(missing_visibility),
                "activation_event_ids": "|".join(str(row.get("event_id", "")) for row in eligible),
            }
        )
    return task_rows


def build_summary(
    *,
    run_id: str,
    actionability_csv: Path,
    run_dir: Path,
    benchmark_dir: Path,
    output_dir: Path,
    prior_adjusted_missing: int,
    actionability_rows: list[dict[str, str]],
    activation_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    class_counts = Counter(str(row.get("actionability_class", "")) for row in actionability_rows)
    kind_counts = Counter(str(row.get("activation_kind", "")) for row in activation_rows)
    proof_counts = Counter(str(row.get("proof_status", "")) for row in activation_rows)
    eligible_rows = [row for row in activation_rows if truthy(row.get("activation_eligible", ""))]
    write_blockers = [
        row
        for row in activation_rows
        if str(row.get("activation_kind", "")) == "write_or_high_impact_tool_activation_requires_value_proof"
    ]
    return {
        "run_id": run_id,
        "analysis": "saved tau2 tool-activation gap audit",
        "actionability_csv": str(actionability_csv),
        "run_dir": str(run_dir),
        "benchmark_dir": str(benchmark_dir),
        "output_dir": str(output_dir),
        "no_dataset_sync": True,
        "no_model_run": True,
        "no_tool_execution": True,
        "official_tau2_score_changed": False,
        "input_actionability_class_counts": dict(sorted(class_counts.items())),
        "input_tool_activation_gaps": len(activation_rows),
        "eligible_read_only_activation_candidates": len(eligible_rows),
        "write_or_high_impact_activation_blockers": len(write_blockers),
        "activation_kind_counts": dict(sorted(kind_counts.items())),
        "proof_status_counts": dict(sorted(proof_counts.items())),
        "prior_adjusted_db_feasible_missing": prior_adjusted_missing,
        "potential_adjusted_missing_after_read_activation_candidates": max(
            0, prior_adjusted_missing - len(eligible_rows)
        ),
        "eligible_event_ids": [str(row.get("event_id", "")) for row in eligible_rows],
        "blocked_write_event_ids": [str(row.get("event_id", "")) for row in write_blockers],
        "tasks_with_activation_candidates": len(
            {(str(row.get("domain", "")), str(row.get("task_id", ""))) for row in eligible_rows}
        ),
        "task_rows": len(task_rows),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256_path(Path(__file__)),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "Read-only activation candidates are not executed here; they identify where a future runner can mint one-shot runtime leases from visible argument evidence.",
            "Write/high-impact missing-tool rows are not activation-ready without the structured value-proof path.",
            "Reference arguments are used only as post-hoc exactness targets for saved-artifact diagnosis.",
        ],
    }


def load_tool_catalog(benchmark_dir: Path) -> dict[tuple[str, str], Any]:
    src_root = benchmark_dir / "src" / "tau2" / "domains"
    catalog: dict[tuple[str, str], Any] = {}
    for tools_path in sorted(src_root.glob("*/tools.py")):
        domain = tools_path.parent.name
        for tool in _parse_assistant_tools(tools_path, domain=domain):
            catalog[(domain, tool.name)] = tool
    return catalog


def tool_source_paths(benchmark_dir: Path) -> list[Path]:
    return sorted((benchmark_dir / "src" / "tau2" / "domains").glob("*/tools.py"))


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
        rows.append({"path": str(path), "sha256": sha256_path(path), "bytes": path.stat().st_size})
    return rows


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    return digest.hexdigest()


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
