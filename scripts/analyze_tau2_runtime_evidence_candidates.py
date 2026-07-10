"""Classify tau2 runtime-evidence candidate correctness from saved task loops.

This analysis is intentionally offline. It reads saved local task-loop artifacts
only; it does not run models, execute tools, sync datasets, or expose reference
actions to a model. Its purpose is to separate runtime-evidence candidates that
are merely relevant from candidates that are the correct next reference action.
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


DEFAULT_RUN_DIR = Path("results/eval/R125")

CANDIDATE_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "step",
    "rank_position",
    "tool",
    "args_json",
    "rank_score",
    "rank_margin_to_next",
    "candidate_correctness",
    "exact_reference_event_id",
    "exact_reference_index",
    "selected_by_model",
    "selected_by_ranked_fallback",
    "executed",
    "bound_reference_event_id",
    "complete_arguments",
    "value_proof_required",
    "value_proof_complete",
    "proof_status",
    "proof_complete",
    "proof_probe",
    "rank_reasons",
    "lease_template_id",
    "runtime_args",
]

STEP_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "step",
    "candidates",
    "proof_complete_candidates",
    "has_exact_next_reference_candidate",
    "has_any_exact_reference_candidate",
    "top_tool",
    "top_args_json",
    "top_rank_score",
    "top_rank_margin",
    "top_candidate_correctness",
    "selected_tool",
    "selected_args_json",
    "selected_candidate_correctness",
    "selected_by_ranked_fallback",
    "selected_executed",
    "selected_bound_reference_event_id",
    "fallback_missed_exact_next_reference",
]

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "steps_with_candidates",
    "runtime_candidates",
    "proof_complete_candidates",
    "exact_next_reference_candidates",
    "any_exact_reference_candidates",
    "top_exact_next_reference_steps",
    "top_any_exact_reference_steps",
    "steps_with_correct_candidate_but_top_wrong",
    "selected_candidates",
    "selected_exact_next_reference",
    "selected_any_exact_reference",
    "ranked_fallback_steps",
    "ranked_fallback_selected_exact_next_reference",
    "ranked_fallback_selected_any_exact_reference",
    "ranked_fallback_missed_exact_next_reference",
    "proof_complete_non_reference_or_wrong_arg_candidates",
    "tool_oracle_pass",
    "all_reference_actions_executed",
    "action_reward",
    "env_reward",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze tau2 runtime-evidence candidate correctness from saved artifacts"
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Analysis run id to record in the summary; defaults to the output directory name.",
    )
    parser.add_argument(
        "--mismatch-dir",
        type=Path,
        default=None,
        help="Optional mismatch-analysis directory to include in input digests only.",
    )
    parser.add_argument(
        "--recall-gap-dir",
        type=Path,
        default=None,
        help="Optional recall-gap-analysis directory to include in input digests only.",
    )
    args = parser.parse_args()

    run_id = args.run_id or args.output_dir.name
    result = analyze_run(args.run_dir, run_id=run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        args.output_dir / "runtime_evidence_candidate_correctness.csv",
        result["candidate_rows"],
        CANDIDATE_FIELDS,
    )
    _write_rows(
        args.output_dir / "step_runtime_evidence_candidate_correctness.csv",
        result["step_rows"],
        STEP_FIELDS,
    )
    _write_rows(
        args.output_dir / "task_runtime_evidence_candidate_correctness.csv",
        result["task_rows"],
        TASK_FIELDS,
    )
    (args.output_dir / "tau2_runtime_evidence_candidate_correctness_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    digest_paths = [args.run_dir]
    if args.mismatch_dir is not None:
        digest_paths.append(args.mismatch_dir)
    if args.recall_gap_dir is not None:
        digest_paths.append(args.recall_gap_dir)
    (args.output_dir / "input_digests.csv").write_text(_input_digest_csv(digest_paths))
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_run(run_dir: Path, *, run_id: str = "R131") -> dict[str, Any]:
    records = _load_jsonl(run_dir / "samples.jsonl")
    saved_summary = _saved_summary(run_dir)
    source_run_id = str(saved_summary.get("run_id") or run_dir.name)
    candidate_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []

    for record in records:
        task_result = analyze_task_record(source_run_id, record)
        candidate_rows.extend(task_result["candidate_rows"])
        step_rows.extend(task_result["step_rows"])
        task_rows.append(task_result["task_row"])

    summary = _summary(
        run_id=run_id,
        run_dir=run_dir,
        source_run_id=source_run_id,
        saved_summary=saved_summary,
        candidate_rows=candidate_rows,
        step_rows=step_rows,
        task_rows=task_rows,
    )
    return {
        "summary": summary,
        "candidate_rows": candidate_rows,
        "step_rows": step_rows,
        "task_rows": task_rows,
    }


def analyze_task_record(source_run_id: str, record: dict[str, Any]) -> dict[str, Any]:
    references = list(record.get("reference_actions") or [])
    executed_ids: set[str] = {
        str(row.get("bound_reference_event_id", ""))
        for row in record.get("action_rows") or []
        if str(row.get("round", "")) == "initial"
        and row.get("executed")
        and row.get("bound_reference_event_id")
    }
    candidate_rows: list[dict[str, Any]] = []
    step_rows: list[dict[str, Any]] = []

    for step in (record.get("stepwise") or {}).get("steps") or []:
        step_result = analyze_step(
            source_run_id,
            record,
            step,
            references=references,
            executed_ids_before=set(executed_ids),
        )
        candidate_rows.extend(step_result["candidate_rows"])
        if step_result["step_row"] is not None:
            step_rows.append(step_result["step_row"])
        for row in step.get("new_action_rows") or []:
            if row.get("executed") and row.get("bound_reference_event_id"):
                executed_ids.add(str(row.get("bound_reference_event_id")))

    task_row = _task_row(source_run_id, record, candidate_rows, step_rows)
    return {
        "candidate_rows": candidate_rows,
        "step_rows": step_rows,
        "task_row": task_row,
    }


def analyze_step(
    source_run_id: str,
    record: dict[str, Any],
    step: dict[str, Any],
    *,
    references: list[dict[str, Any]],
    executed_ids_before: set[str],
) -> dict[str, Any]:
    hints = [
        hint for hint in step.get("runtime_evidence_lease_hints") or [] if isinstance(hint, dict)
    ]
    if not hints:
        return {"candidate_rows": [], "step_row": None}

    sorted_hints = sorted(
        hints,
        key=lambda hint: (
            -_int_value(hint.get("rank_score")),
            str(hint.get("tool", "")),
            json.dumps(_clean_args(dict(hint.get("arguments") or {})), sort_keys=True),
        ),
    )
    selected_keys = {
        _call_key(str(call.get("tool", "")), _clean_args(dict(call.get("arguments") or {})))
        for call in step.get("model_calls") or []
        if isinstance(call, dict)
    }
    ranked_fallback_keys = {
        _call_key(str(call.get("tool", "")), _clean_args(dict(call.get("arguments") or {})))
        for call in step.get("model_calls") or []
        if isinstance(call, dict)
        and isinstance(call.get("arguments"), dict)
        and call["arguments"].get("_intentcap_synthesized_from_ranked_runtime_evidence_hint")
    }
    action_rows_by_key = {
        _call_key(str(row.get("model_tool", "")), _json_dict(row.get("model_args_json", "{}"))): row
        for row in step.get("new_action_rows") or []
        if isinstance(row, dict)
    }

    rows: list[dict[str, Any]] = []
    for index, hint in enumerate(sorted_hints, start=1):
        tool = str(hint.get("tool", ""))
        args = _clean_args(dict(hint.get("arguments") or {}))
        key = _call_key(tool, args)
        next_score = (
            _int_value(sorted_hints[index].get("rank_score"))
            if index < len(sorted_hints)
            else None
        )
        score = _int_value(hint.get("rank_score"))
        selected = key in selected_keys
        action_row = action_rows_by_key.get(key, {})
        correctness = _candidate_correctness(tool, args, references, executed_ids_before)
        value_proof = hint.get("value_proof") if isinstance(hint.get("value_proof"), dict) else {}
        value_proof_required = bool(value_proof.get("required", False))
        value_proof_complete = bool(value_proof.get("complete", not value_proof_required))
        complete_arguments = bool(hint.get("complete_arguments"))
        proof_status = _proof_status(
            complete_arguments=complete_arguments,
            value_proof_required=value_proof_required,
            value_proof_complete=value_proof_complete,
            proof_probe=bool(hint.get("proof_probe", False)),
        )
        rows.append(
            {
                "source_run_id": source_run_id,
                "domain": str(record.get("domain", "")),
                "task_id": str(record.get("task_id", "")),
                "step": int(step.get("step", 0)),
                "rank_position": index,
                "tool": tool,
                "args_json": json.dumps(args, sort_keys=True),
                "rank_score": score,
                "rank_margin_to_next": "" if next_score is None else score - next_score,
                "candidate_correctness": correctness["class"],
                "exact_reference_event_id": correctness["event_id"],
                "exact_reference_index": correctness["index"],
                "selected_by_model": selected,
                "selected_by_ranked_fallback": key in ranked_fallback_keys,
                "executed": bool(action_row.get("executed", False)),
                "bound_reference_event_id": str(action_row.get("bound_reference_event_id", "")),
                "complete_arguments": complete_arguments,
                "value_proof_required": value_proof_required,
                "value_proof_complete": value_proof_complete,
                "proof_status": proof_status,
                "proof_complete": complete_arguments
                and (not value_proof_required or value_proof_complete),
                "proof_probe": bool(hint.get("proof_probe", False)),
                "rank_reasons": "|".join(str(reason) for reason in hint.get("rank_reasons") or []),
                "lease_template_id": str(hint.get("lease_template_id", "")),
                "runtime_args": "|".join(str(arg) for arg in hint.get("runtime_args") or []),
            }
        )

    return {"candidate_rows": rows, "step_row": _step_row(source_run_id, record, step, rows)}


def _candidate_correctness(
    tool: str,
    args: dict[str, Any],
    references: list[dict[str, Any]],
    executed_ids_before: set[str],
) -> dict[str, Any]:
    next_index = _next_unexecuted_reference_index(references, executed_ids_before)
    exact_index = ""
    exact_event_id = ""
    for index, reference in enumerate(references):
        if str(reference.get("tool", "")) == tool and dict(reference.get("arguments") or {}) == args:
            exact_index = str(index)
            exact_event_id = str(reference.get("event_id", ""))
            if exact_event_id in executed_ids_before:
                correctness = "exact_already_executed_reference"
            elif next_index is not None and index == next_index:
                correctness = "exact_next_reference"
            else:
                correctness = "exact_future_reference"
            return {"class": correctness, "event_id": exact_event_id, "index": exact_index}
    if any(str(reference.get("tool", "")) == tool for reference in references):
        return {"class": "same_tool_wrong_args", "event_id": "", "index": ""}
    if references:
        return {"class": "non_reference_tool", "event_id": "", "index": ""}
    return {"class": "no_reference_oracle", "event_id": "", "index": ""}


def _next_unexecuted_reference_index(
    references: list[dict[str, Any]],
    executed_ids_before: set[str],
) -> int | None:
    for index, reference in enumerate(references):
        if str(reference.get("event_id", "")) not in executed_ids_before:
            return index
    return None


def _step_row(
    source_run_id: str,
    record: dict[str, Any],
    step: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    top = rows[0]
    selected = next((row for row in rows if row["selected_by_model"]), None)
    has_next = any(row["candidate_correctness"] == "exact_next_reference" for row in rows)
    has_any_reference = any(_is_exact_reference(row["candidate_correctness"]) for row in rows)
    selected_correctness = str((selected or {}).get("candidate_correctness", ""))
    selected_by_ranked_fallback = bool((selected or {}).get("selected_by_ranked_fallback", False))
    return {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "step": int(step.get("step", 0)),
        "candidates": len(rows),
        "proof_complete_candidates": sum(1 for row in rows if row["proof_complete"]),
        "has_exact_next_reference_candidate": has_next,
        "has_any_exact_reference_candidate": has_any_reference,
        "top_tool": top["tool"],
        "top_args_json": top["args_json"],
        "top_rank_score": top["rank_score"],
        "top_rank_margin": top["rank_margin_to_next"],
        "top_candidate_correctness": top["candidate_correctness"],
        "selected_tool": str((selected or {}).get("tool", "")),
        "selected_args_json": str((selected or {}).get("args_json", "")),
        "selected_candidate_correctness": selected_correctness,
        "selected_by_ranked_fallback": selected_by_ranked_fallback,
        "selected_executed": bool((selected or {}).get("executed", False)),
        "selected_bound_reference_event_id": str(
            (selected or {}).get("bound_reference_event_id", "")
        ),
        "fallback_missed_exact_next_reference": selected_by_ranked_fallback
        and has_next
        and selected_correctness != "exact_next_reference",
    }


def _task_row(
    source_run_id: str,
    record: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
    step_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    task_row = dict(record.get("task_row") or {})
    fallback_steps = [row for row in step_rows if row["selected_by_ranked_fallback"]]
    selected_rows = [row for row in candidate_rows if row["selected_by_model"]]
    return {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "steps_with_candidates": len(step_rows),
        "runtime_candidates": len(candidate_rows),
        "proof_complete_candidates": sum(1 for row in candidate_rows if row["proof_complete"]),
        "exact_next_reference_candidates": sum(
            1 for row in candidate_rows if row["candidate_correctness"] == "exact_next_reference"
        ),
        "any_exact_reference_candidates": sum(
            1 for row in candidate_rows if _is_exact_reference(row["candidate_correctness"])
        ),
        "top_exact_next_reference_steps": sum(
            1 for row in step_rows if row["top_candidate_correctness"] == "exact_next_reference"
        ),
        "top_any_exact_reference_steps": sum(
            1 for row in step_rows if _is_exact_reference(row["top_candidate_correctness"])
        ),
        "steps_with_correct_candidate_but_top_wrong": sum(
            1
            for row in step_rows
            if row["has_exact_next_reference_candidate"]
            and row["top_candidate_correctness"] != "exact_next_reference"
        ),
        "selected_candidates": len(selected_rows),
        "selected_exact_next_reference": sum(
            1 for row in selected_rows if row["candidate_correctness"] == "exact_next_reference"
        ),
        "selected_any_exact_reference": sum(
            1 for row in selected_rows if _is_exact_reference(row["candidate_correctness"])
        ),
        "ranked_fallback_steps": len(fallback_steps),
        "ranked_fallback_selected_exact_next_reference": sum(
            1 for row in fallback_steps if row["selected_candidate_correctness"] == "exact_next_reference"
        ),
        "ranked_fallback_selected_any_exact_reference": sum(
            1
            for row in fallback_steps
            if _is_exact_reference(row["selected_candidate_correctness"])
        ),
        "ranked_fallback_missed_exact_next_reference": sum(
            1 for row in fallback_steps if row["fallback_missed_exact_next_reference"]
        ),
        "proof_complete_non_reference_or_wrong_arg_candidates": sum(
            1
            for row in candidate_rows
            if row["proof_complete"] and not _is_exact_reference(row["candidate_correctness"])
        ),
        "tool_oracle_pass": bool(task_row.get("tool_oracle_pass")),
        "all_reference_actions_executed": bool(task_row.get("all_reference_actions_executed")),
        "action_reward": float(task_row.get("action_reward", 0.0)),
        "env_reward": float(task_row.get("env_reward", 0.0)),
    }


def _summary(
    *,
    run_id: str,
    run_dir: Path,
    source_run_id: str,
    saved_summary: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
    step_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_counts = Counter(str(row["candidate_correctness"]) for row in candidate_rows)
    top_counts = Counter(str(row["top_candidate_correctness"]) for row in step_rows)
    selected_counts = Counter(
        str(row["candidate_correctness"]) for row in candidate_rows if row["selected_by_model"]
    )
    fallback_counts = Counter(
        str(row["selected_candidate_correctness"])
        for row in step_rows
        if row["selected_by_ranked_fallback"]
    )
    fallback_steps = [row for row in step_rows if row["selected_by_ranked_fallback"]]
    return {
        "run_id": run_id,
        "analysis": "saved local-Qwen tau2 runtime-evidence candidate correctness classification",
        "source_run": source_run_id,
        "run_dir": str(run_dir),
        "no_dataset_sync": True,
        "tasks": len(task_rows),
        "steps_with_candidates": len(step_rows),
        "runtime_candidates": len(candidate_rows),
        "proof_complete_candidates": sum(1 for row in candidate_rows if row["proof_complete"]),
        "candidate_correctness_counts": dict(sorted(candidate_counts.items())),
        "top_candidate_correctness_counts": dict(sorted(top_counts.items())),
        "selected_candidate_correctness_counts": dict(sorted(selected_counts.items())),
        "ranked_fallback_selected_correctness_counts": dict(sorted(fallback_counts.items())),
        "steps_with_exact_next_reference_candidate": sum(
            1 for row in step_rows if row["has_exact_next_reference_candidate"]
        ),
        "steps_top_exact_next_reference": sum(
            1 for row in step_rows if row["top_candidate_correctness"] == "exact_next_reference"
        ),
        "steps_top_any_exact_reference": sum(
            1 for row in step_rows if _is_exact_reference(row["top_candidate_correctness"])
        ),
        "steps_with_correct_candidate_but_top_wrong": sum(
            1
            for row in step_rows
            if row["has_exact_next_reference_candidate"]
            and row["top_candidate_correctness"] != "exact_next_reference"
        ),
        "ranked_fallback_steps": len(fallback_steps),
        "ranked_fallback_selected_exact_next_reference": sum(
            1
            for row in fallback_steps
            if row["selected_candidate_correctness"] == "exact_next_reference"
        ),
        "ranked_fallback_selected_any_exact_reference": sum(
            1
            for row in fallback_steps
            if _is_exact_reference(row["selected_candidate_correctness"])
        ),
        "ranked_fallback_missed_exact_next_reference": sum(
            1 for row in fallback_steps if row["fallback_missed_exact_next_reference"]
        ),
        "top1_exact_next_reference_precision": _ratio(
            sum(1 for row in step_rows if row["top_candidate_correctness"] == "exact_next_reference"),
            len(step_rows),
        ),
        "top1_any_exact_reference_precision": _ratio(
            sum(1 for row in step_rows if _is_exact_reference(row["top_candidate_correctness"])),
            len(step_rows),
        ),
        "selected_exact_next_reference_precision": _ratio(
            selected_counts["exact_next_reference"],
            sum(selected_counts.values()),
        ),
        "selected_any_exact_reference_precision": _ratio(
            sum(count for label, count in selected_counts.items() if _is_exact_reference(label)),
            sum(selected_counts.values()),
        ),
        "ranked_fallback_exact_next_reference_precision": _ratio(
            fallback_counts["exact_next_reference"],
            len(fallback_steps),
        ),
        "ranked_fallback_any_exact_reference_precision": _ratio(
            sum(count for label, count in fallback_counts.items() if _is_exact_reference(label)),
            len(fallback_steps),
        ),
        "proof_complete_false_positive_rate": _ratio(
            sum(
                1
                for row in candidate_rows
                if row["proof_complete"] and not _is_exact_reference(row["candidate_correctness"])
            ),
            sum(1 for row in candidate_rows if row["proof_complete"]),
        ),
        "top_rank_tie_or_zero_margin_steps": sum(
            1
            for row in step_rows
            if str(row["top_rank_margin"]) != "" and int(row["top_rank_margin"]) == 0
        ),
        "proof_complete_non_reference_or_wrong_arg_candidates": sum(
            1
            for row in candidate_rows
            if row["proof_complete"] and not _is_exact_reference(row["candidate_correctness"])
        ),
        "tool_oracle_pass_tasks": sum(1 for row in task_rows if row["tool_oracle_pass"]),
        "source_tool_oracle_pass_tasks": int(saved_summary.get("tool_oracle_pass_tasks", 0)),
        "source_bound_reference_calls": int(saved_summary.get("bound_reference_calls", 0)),
        "source_stepwise_runtime_evidence_ranked_fallbacks": int(
            saved_summary.get("stepwise_runtime_evidence_ranked_fallbacks", 0)
        ),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            f"This analysis reads existing {source_run_id} local tau2 task-gateway artifacts only.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or reveal hidden reference actions to a model.",
            "Candidate correctness uses saved reference actions only as a post-hoc oracle.",
            "exact_next_reference means the candidate matches the first reference action not yet executed before that step.",
            "exact_future_reference means the candidate matches a later reference action but would not be the next oracle step.",
            "same_tool_wrong_args means the candidate tool appears in the reference trajectory but the arguments do not exactly match any reference action.",
            "A proof-complete candidate has complete arguments and any required value proof marked complete; this is not sufficient to prove next-action correctness.",
        ],
    }


def _is_exact_reference(correctness: Any) -> bool:
    return str(correctness).startswith("exact_")


def _proof_status(
    *,
    complete_arguments: bool,
    value_proof_required: bool,
    value_proof_complete: bool,
    proof_probe: bool,
) -> str:
    if not complete_arguments:
        return "incomplete_arguments"
    if value_proof_required and not value_proof_complete:
        return "underproven_value"
    if proof_probe:
        return "proof_probe_complete"
    return "proof_complete"


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _clean_args(args: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in args.items() if not str(key).startswith("_intentcap_")}


def _call_key(tool: str, args: dict[str, Any]) -> tuple[str, str]:
    return (tool, json.dumps(args, sort_keys=True))


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _saved_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "task_gateway_summary.json"
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(paths: list[Path]) -> str:
    rows = ["path,sha256,size_bytes"]
    seen: set[Path] = set()
    for root in paths:
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in files:
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            rows.append(f"{path},{_sha256(path.read_bytes())},{path.stat().st_size}")
    return "\n".join(rows) + "\n"


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    ) or "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
