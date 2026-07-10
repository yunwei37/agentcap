"""Analyze runtime-evidence exact-next candidate generation gaps.

This is an offline diagnostic over saved R125/R131 artifacts. It asks why a
hint-bearing step lacks an exact-next runtime-evidence candidate: was the exact
tool and argument evidence visible but not converted into a candidate, was the
tool hidden, or was the argument evidence unavailable? It does not run models,
execute tools, clone benchmarks, sync datasets, or use reference labels to mint
runtime authority.
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


STEP_KEY_FIELDS = ["source_run_id", "domain", "task_id", "step"]

STEP_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "step",
    "exact_next_reference_event_id",
    "exact_next_reference_index",
    "exact_next_feasibility",
    "exact_next_invalid_reference",
    "exact_next_tool",
    "exact_next_args_json",
    "exact_next_arg_values",
    "current_candidates",
    "has_exact_next_candidate",
    "top_candidate_correctness",
    "same_tool_candidates",
    "same_tool_wrong_arg_candidates",
    "exact_future_candidates",
    "tool_visible",
    "all_arg_evidence_prior_results",
    "all_arg_evidence_task_text",
    "all_arg_evidence_any_prompt",
    "any_arg_evidence_prior_results",
    "any_arg_evidence_task_text",
    "exact_compiler_hint_visible",
    "complete_runtime_hint_same_tool",
    "available_tools",
    "missing_arg_values_from_prior_results",
    "missing_arg_values_from_task_text",
    "generation_gap_class",
    "generator_upper_bound_exact_next_possible",
    "runtime_evidence_upper_bound_exact_next_possible",
    "db_feasible_generator_upper_bound_exact_next_possible",
    "db_feasible_runtime_evidence_upper_bound_exact_next_possible",
]

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "steps",
    "steps_with_existing_exact_next_candidate",
    "steps_without_exact_next_candidate",
    "visible_evidence_generation_gap",
    "runtime_evidence_generation_gap",
    "tool_exposure_gap",
    "argument_evidence_gap",
    "tool_and_argument_gap",
    "invalid_exact_next_reference",
    "generator_upper_bound_exact_next_steps",
    "runtime_evidence_upper_bound_exact_next_steps",
    "db_feasible_generator_upper_bound_exact_next_steps",
    "db_feasible_runtime_evidence_upper_bound_exact_next_steps",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify exact-next runtime-evidence candidate generation gaps"
    )
    parser.add_argument("--run-id", default="R133")
    parser.add_argument("--run-dir", type=Path, default=Path("results/eval/R125"))
    parser.add_argument(
        "--candidate-csv",
        type=Path,
        default=Path("results/eval/R131/runtime_evidence_candidate_correctness.csv"),
    )
    parser.add_argument(
        "--feasibility-csv",
        type=Path,
        default=Path("results/eval/R067/reference_feasibility.csv"),
        help="Optional saved reference-feasibility audit used only to tag invalid reference artifacts.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R133"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_generation_gaps(
        args.run_dir,
        args.candidate_csv,
        feasibility_csv=args.feasibility_csv,
        run_id=args.run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "runtime_evidence_generation_gap_steps.csv",
        result["step_rows"],
        STEP_FIELDS,
    )
    write_csv(
        args.output_dir / "runtime_evidence_generation_gap_tasks.csv",
        result["task_rows"],
        TASK_FIELDS,
    )
    (args.output_dir / "runtime_evidence_generation_gap_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest_rows = [
        {
            "path": str(args.run_dir),
            "sha256": sha256_path(args.run_dir),
            "bytes": path_size(args.run_dir),
        },
        {
            "path": str(args.candidate_csv),
            "sha256": sha256_path(args.candidate_csv),
            "bytes": path_size(args.candidate_csv),
        },
    ]
    if args.feasibility_csv.exists():
        digest_rows.append(
            {
                "path": str(args.feasibility_csv),
                "sha256": sha256_path(args.feasibility_csv),
                "bytes": path_size(args.feasibility_csv),
            }
        )
    write_csv(args.output_dir / "input_digests.csv", digest_rows, ["path", "sha256", "bytes"])
    (args.output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_generation_gaps(
    run_dir: Path,
    candidate_csv: Path,
    *,
    feasibility_csv: Path | None = None,
    run_id: str = "R133",
) -> dict[str, Any]:
    candidate_rows = read_csv(candidate_csv)
    candidates_by_step = group_candidates(candidate_rows)
    feasibility_by_event = read_feasibility(feasibility_csv)
    records = load_jsonl(run_dir / "samples.jsonl")
    source_run_id = source_run(run_dir)
    step_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []

    for record in records:
        task_result = analyze_task(
            source_run_id,
            record,
            candidates_by_step,
            feasibility_by_event,
            run_dir=run_dir,
        )
        step_rows.extend(task_result["step_rows"])
        if task_result["task_row"] is not None:
            task_rows.append(task_result["task_row"])

    summary = build_summary(
        run_id=run_id,
        run_dir=run_dir,
        candidate_csv=candidate_csv,
        feasibility_csv=feasibility_csv,
        source_run_id=source_run_id,
        step_rows=step_rows,
        task_rows=task_rows,
    )
    return {"summary": summary, "step_rows": step_rows, "task_rows": task_rows}


def analyze_task(
    source_run_id: str,
    record: dict[str, Any],
    candidates_by_step: dict[tuple[str, str, str, str], list[dict[str, str]]],
    feasibility_by_event: dict[str, str],
    *,
    run_dir: Path,
) -> dict[str, Any]:
    references = list(record.get("reference_actions") or [])
    executed_ids: set[str] = {
        str(row.get("bound_reference_event_id", ""))
        for row in record.get("action_rows") or []
        if str(row.get("round", "")) == "initial"
        and row.get("executed")
        and row.get("bound_reference_event_id")
    }
    rows: list[dict[str, Any]] = []
    for step in (record.get("stepwise") or {}).get("steps") or []:
        step_key_value = (
            source_run_id,
            str(record.get("domain", "")),
            str(record.get("task_id", "")),
            str(step.get("step", "")),
        )
        if step_key_value in candidates_by_step:
            rows.append(
                analyze_step(
                    source_run_id,
                    record,
                    step,
                    candidates_by_step[step_key_value],
                    references=references,
                    executed_ids_before=set(executed_ids),
                    feasibility_by_event=feasibility_by_event,
                    run_dir=run_dir,
                )
            )
        for action_row in step.get("new_action_rows") or []:
            if action_row.get("executed") and action_row.get("bound_reference_event_id"):
                executed_ids.add(str(action_row.get("bound_reference_event_id")))

    return {"step_rows": rows, "task_row": task_row(source_run_id, record, rows)}


def analyze_step(
    source_run_id: str,
    record: dict[str, Any],
    step: dict[str, Any],
    candidates: list[dict[str, str]],
    *,
    references: list[dict[str, Any]],
    executed_ids_before: set[str],
    feasibility_by_event: dict[str, str],
    run_dir: Path,
) -> dict[str, Any]:
    next_index = next_unexecuted_reference_index(references, executed_ids_before)
    reference = references[next_index] if next_index is not None else {}
    event_id = str(reference.get("event_id", ""))
    feasibility = feasibility_by_event.get(event_id, "")
    invalid_reference = feasibility.startswith("invalid_")
    tool = str(reference.get("tool", ""))
    args = dict(reference.get("arguments") or {})
    arg_values = leaf_values(args)
    payload = prompt_payload(step, run_dir=run_dir)
    available_tools = [
        str(tool_row.get("name", ""))
        for tool_row in payload.get("available_tools") or []
        if isinstance(tool_row, dict)
    ]
    previous_text = json.dumps(payload.get("previous_gateway_results") or [], sort_keys=True)
    task_text = json.dumps(payload.get("task") or {}, sort_keys=True)
    compiler_hints = payload.get("active_compiler_lease_hints")
    if not isinstance(compiler_hints, list):
        compiler_hints = step.get("compiler_lease_hints") or []
    runtime_hints = [
        hint for hint in step.get("runtime_evidence_lease_hints") or [] if isinstance(hint, dict)
    ]

    has_exact = any(row["candidate_correctness"] == "exact_next_reference" for row in candidates)
    top_correctness = str(
        sorted(candidates, key=lambda row: int(row.get("rank_position") or 10**9))[0][
            "candidate_correctness"
        ]
    )
    tool_visible = tool in set(available_tools)
    all_prior = all_values_present(arg_values, previous_text)
    all_task = all_values_present(arg_values, task_text)
    any_prior = any_values_present(arg_values, previous_text)
    any_task = any_values_present(arg_values, task_text)
    exact_compiler_hint = exact_hint_visible(tool, args, compiler_hints)
    runtime_same_tool_complete = any(
        str(hint.get("tool", "")) == tool and bool(hint.get("complete_arguments"))
        for hint in runtime_hints
    )
    same_tool_candidates = [
        row for row in candidates if str(row.get("tool", "")) == tool
    ]
    row = {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "step": str(step.get("step", "")),
        "exact_next_reference_event_id": event_id,
        "exact_next_reference_index": "" if next_index is None else str(next_index),
        "exact_next_feasibility": feasibility,
        "exact_next_invalid_reference": invalid_reference,
        "exact_next_tool": tool,
        "exact_next_args_json": json.dumps(args, sort_keys=True),
        "exact_next_arg_values": "|".join(arg_values),
        "current_candidates": len(candidates),
        "has_exact_next_candidate": has_exact,
        "top_candidate_correctness": top_correctness,
        "same_tool_candidates": len(same_tool_candidates),
        "same_tool_wrong_arg_candidates": sum(
            1 for candidate in same_tool_candidates if candidate["candidate_correctness"] == "same_tool_wrong_args"
        ),
        "exact_future_candidates": sum(
            1 for candidate in candidates if candidate["candidate_correctness"] == "exact_future_reference"
        ),
        "tool_visible": tool_visible,
        "all_arg_evidence_prior_results": all_prior,
        "all_arg_evidence_task_text": all_task,
        "all_arg_evidence_any_prompt": all_prior or all_task,
        "any_arg_evidence_prior_results": any_prior,
        "any_arg_evidence_task_text": any_task,
        "exact_compiler_hint_visible": exact_compiler_hint,
        "complete_runtime_hint_same_tool": runtime_same_tool_complete,
        "available_tools": "|".join(available_tools),
        "missing_arg_values_from_prior_results": "|".join(
            value for value in arg_values if value not in previous_text
        ),
        "missing_arg_values_from_task_text": "|".join(
            value for value in arg_values if value not in task_text
        ),
    }
    row["generation_gap_class"] = generation_gap_class(row)
    row["generator_upper_bound_exact_next_possible"] = bool(
        has_exact or (tool_visible and (all_prior or all_task))
    )
    row["runtime_evidence_upper_bound_exact_next_possible"] = bool(
        has_exact or (tool_visible and all_prior)
    )
    row["db_feasible_generator_upper_bound_exact_next_possible"] = bool(
        (not invalid_reference) and row["generator_upper_bound_exact_next_possible"]
    )
    row["db_feasible_runtime_evidence_upper_bound_exact_next_possible"] = bool(
        (not invalid_reference) and row["runtime_evidence_upper_bound_exact_next_possible"]
    )
    return row


def generation_gap_class(row: dict[str, Any]) -> str:
    if not row["exact_next_tool"]:
        return "no_next_reference"
    if row["exact_next_invalid_reference"]:
        return "invalid_exact_next_reference"
    if row["has_exact_next_candidate"]:
        return "existing_exact_next_candidate"
    if row["tool_visible"] and row["all_arg_evidence_prior_results"]:
        return "runtime_evidence_generation_gap"
    if row["tool_visible"] and row["all_arg_evidence_any_prompt"]:
        return "task_text_candidate_generation_gap"
    if (not row["tool_visible"]) and row["all_arg_evidence_any_prompt"]:
        return "tool_exposure_gap"
    if row["tool_visible"]:
        return "argument_evidence_gap"
    return "tool_and_argument_gap"


def task_row(
    source_run_id: str,
    record: dict[str, Any],
    step_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not step_rows:
        return None
    counts = Counter(str(row["generation_gap_class"]) for row in step_rows)
    return {
        "source_run_id": source_run_id,
        "domain": str(record.get("domain", "")),
        "task_id": str(record.get("task_id", "")),
        "steps": len(step_rows),
        "steps_with_existing_exact_next_candidate": counts["existing_exact_next_candidate"],
        "steps_without_exact_next_candidate": len(step_rows)
        - counts["existing_exact_next_candidate"],
        "visible_evidence_generation_gap": counts["runtime_evidence_generation_gap"]
        + counts["task_text_candidate_generation_gap"],
        "runtime_evidence_generation_gap": counts["runtime_evidence_generation_gap"],
        "tool_exposure_gap": counts["tool_exposure_gap"],
        "argument_evidence_gap": counts["argument_evidence_gap"],
        "tool_and_argument_gap": counts["tool_and_argument_gap"],
        "invalid_exact_next_reference": counts["invalid_exact_next_reference"],
        "generator_upper_bound_exact_next_steps": sum(
            1 for row in step_rows if row["generator_upper_bound_exact_next_possible"]
        ),
        "runtime_evidence_upper_bound_exact_next_steps": sum(
            1 for row in step_rows if row["runtime_evidence_upper_bound_exact_next_possible"]
        ),
        "db_feasible_generator_upper_bound_exact_next_steps": sum(
            1
            for row in step_rows
            if row["db_feasible_generator_upper_bound_exact_next_possible"]
        ),
        "db_feasible_runtime_evidence_upper_bound_exact_next_steps": sum(
            1
            for row in step_rows
            if row["db_feasible_runtime_evidence_upper_bound_exact_next_possible"]
        ),
    }


def build_summary(
    *,
    run_id: str,
    run_dir: Path,
    candidate_csv: Path,
    feasibility_csv: Path | None,
    source_run_id: str,
    step_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = Counter(str(row["generation_gap_class"]) for row in step_rows)
    steps = len(step_rows)
    existing = counts["existing_exact_next_candidate"]
    generator_bound = sum(
        1 for row in step_rows if row["generator_upper_bound_exact_next_possible"]
    )
    runtime_bound = sum(
        1 for row in step_rows if row["runtime_evidence_upper_bound_exact_next_possible"]
    )
    db_generator_bound = sum(
        1
        for row in step_rows
        if row["db_feasible_generator_upper_bound_exact_next_possible"]
    )
    db_runtime_bound = sum(
        1
        for row in step_rows
        if row["db_feasible_runtime_evidence_upper_bound_exact_next_possible"]
    )
    invalid_steps = counts["invalid_exact_next_reference"]
    return {
        "run_id": run_id,
        "analysis": "saved local-Qwen tau2 exact-next runtime-evidence candidate generation gap",
        "source_run": source_run_id,
        "run_dir": str(run_dir),
        "candidate_csv": str(candidate_csv),
        "feasibility_csv": str(feasibility_csv or ""),
        "no_dataset_sync": True,
        "tasks": len(task_rows),
        "steps": steps,
        "steps_with_existing_exact_next_candidate": existing,
        "steps_without_exact_next_candidate": steps - existing,
        "generation_gap_class_counts": dict(sorted(counts.items())),
        "generator_upper_bound_exact_next_steps": generator_bound,
        "runtime_evidence_upper_bound_exact_next_steps": runtime_bound,
        "db_feasible_generator_upper_bound_exact_next_steps": db_generator_bound,
        "db_feasible_runtime_evidence_upper_bound_exact_next_steps": db_runtime_bound,
        "generator_upper_bound_gain_over_current": generator_bound - existing,
        "runtime_evidence_upper_bound_gain_over_current": runtime_bound - existing,
        "db_feasible_generator_upper_bound_gain_over_current": db_generator_bound - existing,
        "db_feasible_runtime_evidence_upper_bound_gain_over_current": db_runtime_bound - existing,
        "generator_upper_bound_step_coverage": ratio(generator_bound, steps),
        "runtime_evidence_upper_bound_step_coverage": ratio(runtime_bound, steps),
        "db_feasible_generator_upper_bound_step_coverage": ratio(db_generator_bound, steps),
        "db_feasible_runtime_evidence_upper_bound_step_coverage": ratio(db_runtime_bound, steps),
        "steps_with_invalid_exact_next_reference": invalid_steps,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256_path(Path(__file__)),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This analysis reads saved R125/R131 local tau2 artifacts only.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or reveal hidden reference actions to a model.",
            "Reference actions are used only as a post-hoc oracle to classify why exact-next candidates were absent.",
            "generator_upper_bound_exact_next_possible counts steps where the exact-next tool is visible and all exact-next argument leaf values appear in saved task text or prior gateway-result previews.",
            "runtime_evidence_upper_bound_exact_next_possible is stricter: argument leaf values must appear in prior gateway-result previews.",
            "If a saved feasibility audit marks the exact-next reference as invalid_schema_example_reference, the step is excluded from DB-feasible upper-bound counts.",
        ],
    }


def group_candidates(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[step_key(row)].append(row)
    return dict(groups)


def step_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return tuple(str(row.get(field, "")) for field in STEP_KEY_FIELDS)  # type: ignore[return-value]


def next_unexecuted_reference_index(
    references: list[dict[str, Any]],
    executed_ids_before: set[str],
) -> int | None:
    for index, reference in enumerate(references):
        if str(reference.get("event_id", "")) not in executed_ids_before:
            return index
    return None


def prompt_payload(step: dict[str, Any], *, run_dir: Path) -> dict[str, Any]:
    payload = step.get("prompt_payload")
    if isinstance(payload, dict):
        return payload
    path = resolve_prompt_path(step.get("prompt_path", ""), run_dir)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    marker = "Input JSON:\n"
    if marker not in text:
        return {}
    payload_text = text.split(marker, 1)[1]
    for end_marker in ("\nOutput JSON only:", "\nOutput JSON:"):
        if end_marker in payload_text:
            payload_text = payload_text.split(end_marker, 1)[0]
            break
    try:
        parsed = json.loads(payload_text.strip())
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def resolve_prompt_path(raw_path: Any, run_dir: Path) -> Path:
    path = Path(str(raw_path or ""))
    if not str(raw_path or "") or path.is_absolute():
        return path
    candidates = [
        path,
        run_dir / path,
        Path.cwd() / path,
    ]
    if path.parts[:3] == ("results", "eval", run_dir.name):
        candidates.append(run_dir / Path(*path.parts[3:]))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def exact_hint_visible(tool: str, args: dict[str, Any], hints: list[Any]) -> bool:
    for hint in hints:
        if not isinstance(hint, dict):
            continue
        if str(hint.get("tool", "")) != tool:
            continue
        if hint.get("complete_arguments") is True and dict(hint.get("arguments") or {}) == args:
            return True
    return False


def leaf_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            values.extend(leaf_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(leaf_values(child))
    elif isinstance(value, bool) or value is None:
        return []
    else:
        text = str(value)
        if text:
            values.append(text)
    return values


def all_values_present(values: list[str], text: str) -> bool:
    if not values:
        return True
    return all(value in text for value in values)


def any_values_present(values: list[str], text: str) -> bool:
    if not values:
        return True
    return any(value in text for value in values)


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def source_run(run_dir: Path) -> str:
    summary = run_dir / "task_gateway_summary.json"
    if summary.exists():
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict) and data.get("run_id"):
            return str(data["run_id"])
    return run_dir.name


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_feasibility(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    rows = read_csv(path)
    return {
        str(row.get("event_id", "")): str(row.get("feasibility", ""))
        for row in rows
        if row.get("event_id")
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    for child in sorted(path.rglob("*")):
        if child.is_file():
            digest.update(str(child.relative_to(path)).encode("utf-8"))
            digest.update(child.read_bytes())
    return digest.hexdigest()


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
