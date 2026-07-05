"""Build a tau2 candidate-generation repair map from saved diagnostics.

R134 showed that broad utility failure is not caused by selecting the wrong
existing exact runtime candidate: all 38 DB-feasible missing actions lacked an
exact candidate in the saved R131 pool.  This script takes the next conservative
step.  It reads saved R134 actionability rows and saved R125 task-loop prompts
to identify immediate exact-candidate repair opportunities:

* visible-tool/visible-argument misses where a compiler/planner should have
  synthesized a runtime candidate; and
* complete compiler hints that were already present but not called.

This is still offline diagnostic evidence.  For visible-tool/argument misses,
the exact reference arguments are used only post-hoc as the target to verify
that all required values were visible in the prompt; they are not sent to a
model, executed, or used to mint authority in a task loop.
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


REPAIR_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "actionability_class",
    "repair_class",
    "eligible",
    "earliest_synthesis_step",
    "synthesis_steps",
    "tool_visible_steps",
    "all_arg_evidence_steps",
    "complete_compiler_hint_steps",
    "candidate_json",
    "candidate_source",
    "candidate_exact_reference_match",
    "tool_schema_available",
    "required_args",
    "schema_required_args_satisfied",
    "all_arg_values_visible_in_step",
    "arg_value_sources_json",
    "proof_status",
    "next_experiment_target",
]

TASK_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "eligible_repairs",
    "visible_tool_argument_repairs",
    "complete_hint_repairs",
    "high_impact_repairs",
    "repair_event_ids",
    "primary_repair_class",
]

HIGH_IMPACT_TOOL_PREFIXES = (
    "book_",
    "cancel_",
    "create_",
    "delete_",
    "enable_",
    "exchange_",
    "modify_",
    "refuel_",
    "resume_",
    "return_",
    "send_",
    "suspend_",
    "transfer_",
    "update_",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build candidate-generation repair map from saved R134/R125 artifacts"
    )
    parser.add_argument("--run-id", default="R135")
    parser.add_argument(
        "--actionability-csv",
        type=Path,
        default=Path("results/eval/R134/missing_reference_actionability.csv"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("results/eval/R125"),
        help="Saved task-loop run directory containing samples.jsonl and step prompts.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R135"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_repair_map(
        actionability_csv=args.actionability_csv,
        run_dir=args.run_dir,
        run_id=args.run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "candidate_generation_repair_map.csv",
        result["repair_rows"],
        REPAIR_FIELDS,
    )
    write_csv(
        args.output_dir / "task_candidate_generation_repair_map.csv",
        result["task_rows"],
        TASK_FIELDS,
    )
    (args.output_dir / "candidate_generation_repair_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(
        args.output_dir / "input_digests.csv",
        input_digest_rows([args.actionability_csv, args.run_dir / "samples.jsonl"]),
        ["path", "sha256", "bytes"],
    )
    (args.output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_repair_map(
    *,
    actionability_csv: Path,
    run_dir: Path,
    run_id: str = "R135",
) -> dict[str, Any]:
    actionability_rows = read_csv(actionability_csv)
    records_by_task = load_records_by_task(run_dir)
    repair_rows = [
        classify_repair_row(row, records_by_task, run_dir=run_dir)
        for row in actionability_rows
        if str(row.get("actionability_class", ""))
        in {"runtime_candidate_generation_gap", "complete_compiler_hint_not_called"}
    ]
    task_rows = build_task_rows(repair_rows)
    summary = build_summary(
        run_id=run_id,
        actionability_csv=actionability_csv,
        run_dir=run_dir,
        actionability_rows=actionability_rows,
        repair_rows=repair_rows,
        task_rows=task_rows,
    )
    return {"repair_rows": repair_rows, "task_rows": task_rows, "summary": summary}


def classify_repair_row(
    row: dict[str, str],
    records_by_task: dict[tuple[str, str], dict[str, Any]],
    *,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    actionability_class = str(row.get("actionability_class", ""))
    args = parse_json_object(row.get("args_json", "{}"))
    tool = str(row.get("tool", ""))
    record = records_by_task.get(task_key(row), {})
    contexts = prompt_contexts_from_record(record, run_dir=run_dir) if record else []
    context_by_step = {str(context["step"]): context for context in contexts}

    repair_class = ""
    synthesis_steps: list[str] = []
    candidate_source = ""
    candidate_args = args

    if actionability_class == "runtime_candidate_generation_gap":
        repair_class = "visible_tool_argument_candidate_generation"
        synthesis_steps = sorted_step_intersection(
            row.get("tool_visible_steps", ""),
            row.get("all_arg_evidence_steps", ""),
        )
        candidate_source = "posthoc_reference_args_verified_visible_in_prompt"
    elif actionability_class == "complete_compiler_hint_not_called":
        repair_class = "existing_complete_compiler_hint_replay"
        synthesis_steps = parse_steps(row.get("complete_compiler_hint_steps", ""))
        candidate_source = "saved_complete_compiler_hint"
        hint = first_complete_hint(context_by_step, synthesis_steps, tool, args)
        if hint:
            candidate_args = dict(hint.get("arguments") or {})

    earliest_step = synthesis_steps[0] if synthesis_steps else ""
    selected_context = context_by_step.get(earliest_step, {})
    tool_schema = find_tool_schema(selected_context, tool)
    required_args = list(((tool_schema.get("parameters") or {}).get("required") or []))
    required_satisfied = all(arg in candidate_args for arg in required_args)
    arg_value_sources = value_sources(candidate_args, selected_context)
    all_values_visible = all(
        source.get("sources") for source in arg_value_sources.values()
    )
    candidate = {"tool": tool, "arguments": candidate_args}
    exact_match = candidate_args == args
    eligible = bool(synthesis_steps) and bool(tool_schema) and required_satisfied
    if actionability_class == "runtime_candidate_generation_gap":
        eligible = eligible and all_values_visible
    if actionability_class == "complete_compiler_hint_not_called":
        eligible = eligible and exact_match

    proof_status = proof_status_for(
        actionability_class=actionability_class,
        eligible=eligible,
        exact_match=exact_match,
        tool_schema=bool(tool_schema),
        required_satisfied=required_satisfied,
        all_values_visible=all_values_visible,
    )

    return {
        "source_run_id": str(row.get("source_run_id", "")),
        "domain": str(row.get("domain", "")),
        "task_id": str(row.get("task_id", "")),
        "event_id": str(row.get("event_id", "")),
        "tool": tool,
        "args_json": json.dumps(args, sort_keys=True),
        "actionability_class": actionability_class,
        "repair_class": repair_class,
        "eligible": eligible,
        "earliest_synthesis_step": earliest_step,
        "synthesis_steps": "|".join(synthesis_steps),
        "tool_visible_steps": str(row.get("tool_visible_steps", "")),
        "all_arg_evidence_steps": str(row.get("all_arg_evidence_steps", "")),
        "complete_compiler_hint_steps": str(row.get("complete_compiler_hint_steps", "")),
        "candidate_json": json.dumps(candidate, sort_keys=True),
        "candidate_source": candidate_source,
        "candidate_exact_reference_match": exact_match,
        "tool_schema_available": bool(tool_schema),
        "required_args": "|".join(str(arg) for arg in required_args),
        "schema_required_args_satisfied": required_satisfied,
        "all_arg_values_visible_in_step": all_values_visible,
        "arg_value_sources_json": json.dumps(arg_value_sources, sort_keys=True),
        "proof_status": proof_status,
        "next_experiment_target": next_target(repair_class),
    }


def first_complete_hint(
    context_by_step: dict[str, dict[str, Any]],
    steps: list[str],
    tool: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    for step in steps:
        context = context_by_step.get(step) or {}
        for hint in context.get("compiler_hints") or []:
            if (
                str(hint.get("tool", "")) == tool
                and hint.get("complete_arguments") is True
                and dict(hint.get("arguments") or {}) == args
            ):
                return hint
    return {}


def find_tool_schema(context: dict[str, Any], tool: str) -> dict[str, Any]:
    for schema in context.get("available_tools") or []:
        if isinstance(schema, dict) and str(schema.get("name", "")) == tool:
            return schema
    return {}


def value_sources(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    task_text = str(context.get("task_text", ""))
    gateway_text = str(context.get("previous_gateway_results_text", ""))
    sources: dict[str, Any] = {}
    for value in leaf_values(args):
        value_sources_for_leaf: list[str] = []
        if value in task_text:
            value_sources_for_leaf.append("trusted_task_text")
        if value in gateway_text:
            value_sources_for_leaf.append("prior_gateway_result")
        sources[value] = {"sources": value_sources_for_leaf}
    return sources


def proof_status_for(
    *,
    actionability_class: str,
    eligible: bool,
    exact_match: bool,
    tool_schema: bool,
    required_satisfied: bool,
    all_values_visible: bool,
) -> str:
    if not tool_schema:
        return "missing_tool_schema_at_synthesis_step"
    if not required_satisfied:
        return "missing_required_argument"
    if actionability_class == "runtime_candidate_generation_gap" and not all_values_visible:
        return "missing_visible_argument_value"
    if actionability_class == "complete_compiler_hint_not_called" and not exact_match:
        return "complete_hint_does_not_match_reference"
    if eligible:
        return "repair_candidate_ready"
    return "not_repairable_by_this_stage"


def next_target(repair_class: str) -> str:
    if repair_class == "visible_tool_argument_candidate_generation":
        return "add_visible_value_candidate_generator_and_gateway_replay"
    if repair_class == "existing_complete_compiler_hint_replay":
        return "execute_complete_compiler_hint_before_runtime_evidence_search"
    return "unclassified"


def build_task_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["domain"]), str(row["task_id"]))].append(row)

    task_rows: list[dict[str, Any]] = []
    for (domain, task_id), task_rows_for_key in sorted(grouped.items()):
        eligible = [row for row in task_rows_for_key if row["eligible"]]
        repair_counts = Counter(str(row["repair_class"]) for row in eligible)
        task_rows.append(
            {
                "source_run_id": str(task_rows_for_key[0].get("source_run_id", "")),
                "domain": domain,
                "task_id": task_id,
                "eligible_repairs": len(eligible),
                "visible_tool_argument_repairs": repair_counts[
                    "visible_tool_argument_candidate_generation"
                ],
                "complete_hint_repairs": repair_counts[
                    "existing_complete_compiler_hint_replay"
                ],
                "high_impact_repairs": sum(
                    1 for row in eligible if is_high_impact_tool(str(row["tool"]))
                ),
                "repair_event_ids": "|".join(str(row["event_id"]) for row in eligible),
                "primary_repair_class": primary_repair_class(repair_counts),
            }
        )
    return task_rows


def primary_repair_class(counts: Counter[str]) -> str:
    for repair_class in (
        "existing_complete_compiler_hint_replay",
        "visible_tool_argument_candidate_generation",
    ):
        if counts[repair_class]:
            return repair_class
    return "none"


def build_summary(
    *,
    run_id: str,
    actionability_csv: Path,
    run_dir: Path,
    actionability_rows: list[dict[str, str]],
    repair_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [row for row in repair_rows if row["eligible"]]
    all_db_feasible_missing = [
        row for row in actionability_rows if truthy(row.get("db_feasible", ""))
    ]
    repair_counts = Counter(str(row["repair_class"]) for row in eligible)
    source_counts = Counter(str(row.get("candidate_source", "")) for row in eligible)
    return {
        "run_id": run_id,
        "analysis": "saved tau2 R134 candidate-generation repair map",
        "actionability_csv": str(actionability_csv),
        "run_dir": str(run_dir),
        "no_dataset_sync": True,
        "no_model_run": True,
        "no_tool_execution": True,
        "db_feasible_missing_actions_before_repair_map": len(all_db_feasible_missing),
        "repair_rows": len(repair_rows),
        "eligible_exact_candidate_repairs": len(eligible),
        "eligible_visible_tool_argument_repairs": repair_counts[
            "visible_tool_argument_candidate_generation"
        ],
        "eligible_complete_hint_repairs": repair_counts[
            "existing_complete_compiler_hint_replay"
        ],
        "eligible_high_impact_repairs": sum(
            1 for row in eligible if is_high_impact_tool(str(row["tool"]))
        ),
        "potential_db_feasible_missing_after_immediate_repairs": max(
            0, len(all_db_feasible_missing) - len(eligible)
        ),
        "tasks_with_repair_opportunities": len(
            {(str(row["domain"]), str(row["task_id"])) for row in eligible}
        ),
        "repair_class_counts": dict(sorted(repair_counts.items())),
        "candidate_source_counts": dict(sorted(source_counts.items())),
        "task_primary_repair_class_counts": dict(
            sorted(Counter(str(row["primary_repair_class"]) for row in task_rows).items())
        ),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256(Path(__file__).read_bytes()),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This is an offline repair-map analysis over saved R134/R125 artifacts.",
            "Visible-tool/argument candidates use reference arguments only as post-hoc exactness targets; this is not a real compiler utility result.",
            "Complete-hint candidates are recovered from saved prompt compiler hints.",
            "The next execution experiment should feed these repair classes into the task loop and measure whether bound-reference calls improve without broadening authority.",
        ],
    }


def load_records_by_task(run_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    records = []
    samples_path = run_dir / "samples.jsonl"
    if samples_path.exists():
        records = load_jsonl(samples_path)
    return {(str(record.get("domain", "")), str(record.get("task_id", ""))): record for record in records}


def prompt_contexts_from_record(
    record: dict[str, Any],
    *,
    run_dir: Path | None = None,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    steps = (record.get("stepwise") or {}).get("steps") or []
    for step in steps:
        payload = step.get("prompt_payload")
        if payload is None:
            prompt_path = resolve_prompt_path(step.get("prompt_path", ""), run_dir)
            payload = read_prompt_payload(prompt_path) if prompt_path.exists() else {}
        if not isinstance(payload, dict):
            payload = {}
        compiler_hints = payload.get("active_compiler_lease_hints")
        if compiler_hints is None:
            compiler_hints = step.get("compiler_lease_hints") or []
        contexts.append(
            {
                "step": str(step.get("step") or payload.get("step_index") or ""),
                "available_tools": [
                    tool for tool in payload.get("available_tools") or [] if isinstance(tool, dict)
                ],
                "compiler_hints": [
                    hint for hint in compiler_hints if isinstance(hint, dict)
                ],
                "previous_gateway_results_text": json.dumps(
                    payload.get("previous_gateway_results") or [],
                    sort_keys=True,
                    default=str,
                ),
                "task_text": json.dumps(
                    payload.get("task") or {},
                    sort_keys=True,
                    default=str,
                ),
            }
        )
    return contexts


def resolve_prompt_path(raw_path: Any, run_dir: Path | None) -> Path:
    prompt_path = Path(str(raw_path or ""))
    if not str(raw_path or "") or prompt_path.is_absolute():
        return prompt_path
    candidates = [prompt_path]
    if run_dir is not None:
        candidates.append(run_dir / prompt_path)
        candidates.append(Path.cwd() / prompt_path)
        if len(run_dir.parents) >= 3:
            candidates.append(run_dir.parents[2] / prompt_path)
        if prompt_path.parts[:3] == ("results", "eval", run_dir.name):
            candidates.append(run_dir / Path(*prompt_path.parts[3:]))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return prompt_path


def read_prompt_payload(prompt_path: Path) -> dict[str, Any]:
    try:
        text = prompt_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    marker = "Input JSON:\n"
    if marker not in text:
        return {}
    payload_text = text.split(marker, 1)[1]
    for end_marker in ("\nOutput JSON only:", "\nOutput JSON:"):
        if end_marker in payload_text:
            payload_text = payload_text.split(end_marker, 1)[0]
            break
    try:
        payload = json.loads(payload_text.strip())
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def task_key(row: dict[str, str]) -> tuple[str, str]:
    return (str(row.get("domain", "")), str(row.get("task_id", "")))


def sorted_step_intersection(left: str, right: str) -> list[str]:
    return sorted_steps(set(parse_steps(left)) & set(parse_steps(right)))


def parse_steps(raw_steps: str) -> list[str]:
    return sorted_steps(step for step in str(raw_steps or "").split("|") if step)


def sorted_steps(steps: Any) -> list[str]:
    return sorted([str(step) for step in steps], key=lambda step: (int(step) if step.isdigit() else 10**9, step))


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


def is_high_impact_tool(tool: str) -> bool:
    return any(tool.startswith(prefix) for prefix in HIGH_IMPACT_TOOL_PREFIXES)


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def parse_json_object(raw: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def input_digest_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        data = path.read_bytes()
        rows.append({"path": str(path), "sha256": sha256(data), "bytes": len(data)})
    return rows


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
