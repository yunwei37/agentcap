"""Audit local benchmark task-loop protocol failures.

This is a deterministic saved-artifact analysis. It reads a completed
``run_tau2_local_llm_task_gateway.py`` result directory and characterizes whether
the local model loop is failing because the checker denies calls, or because the
model protocol does not produce parseable bounded tool calls. It does not run a
model, execute tools, replay tasks, sync datasets, or mint leases.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_tau2_local_llm_task_gateway import (  # noqa: E402
    normalize_model_calls,
    parse_model_json,
)


DEFAULT_INPUT_DIR = Path("results/eval/R340RETAILCOMPILERFEEDBACK5")
RAW_ROW_FIELDS = [
    "kind",
    "domain",
    "task_id",
    "step",
    "path",
    "returncode",
    "stdout_chars",
    "empty_stdout",
    "contains_think",
    "contains_output_json_fence",
    "has_end_marker",
    "parsed_json",
    "parsed_calls",
    "mentions_actions",
    "mentions_tool",
    "likely_truncated",
    "nonzero_returncode",
    "prompt_too_long",
    "backend_crash",
]
TASK_ROW_FIELDS = [
    "domain",
    "task_id",
    "step_outputs",
    "feedback_outputs",
    "empty_step_outputs",
    "step_outputs_with_think",
    "step_outputs_with_parsed_calls",
    "likely_truncated_step_outputs",
    "gateway_allowed",
    "gateway_blocked",
    "feedback_attempted",
    "feedback_model_calls",
    "feedback_gateway_allowed",
    "action_reward",
    "tool_oracle_pass",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    summary = analyze(input_dir=args.input_dir, output_dir=args.output_dir, run_id=args.run_id)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def analyze(*, input_dir: Path, output_dir: Path, run_id: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = input_dir / "task_gateway_summary.json"
    task_path = input_dir / "task_results.csv"
    action_path = input_dir / "action_results.csv"
    source_summary = _read_json(summary_path)
    task_rows = _read_csv(task_path)
    action_rows = _read_csv(action_path)

    raw_rows = _raw_rows(input_dir / "step_raw_outputs", kind="step")
    raw_rows.extend(_raw_rows(input_dir / "feedback_raw_outputs", kind="feedback"))
    per_task = _task_rows(task_rows, action_rows, raw_rows)
    summary = _summary(
        run_id=run_id,
        input_dir=input_dir,
        source_summary=source_summary,
        raw_rows=raw_rows,
        task_rows=task_rows,
        action_rows=action_rows,
        per_task=per_task,
    )

    _write_csv(output_dir / "protocol_raw_outputs.csv", RAW_ROW_FIELDS, raw_rows)
    _write_csv(output_dir / "protocol_task_summary.csv", TASK_ROW_FIELDS, per_task)
    (output_dir / "benchmark_protocol_gap_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    _write_csv(
        output_dir / "input_digests.csv",
        ["path", "bytes", "sha256"],
        [
            _digest_row(summary_path),
            _digest_row(task_path),
            _digest_row(action_path),
        ],
    )
    return summary


def _raw_rows(raw_dir: Path, *, kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not raw_dir.exists():
        return rows
    for path in sorted(raw_dir.glob("*.txt")):
        payload = _raw_payload(path)
        stdout = _stdout(path)
        stderr = str(payload.get("stderr", "")) if isinstance(payload, dict) else ""
        returncode = payload.get("returncode", "") if isinstance(payload, dict) else ""
        parsed = parse_model_json(stdout)
        calls = normalize_model_calls(parsed)
        task_key = _task_key(path.stem)
        mentions_actions = '"actions"' in stdout or "'actions'" in stdout
        mentions_tool = '"tool"' in stdout or "'tool'" in stdout
        has_end_marker = "[end of text]" in stdout
        likely_truncated = bool(stdout) and not has_end_marker and (
            parsed is None or mentions_actions or mentions_tool
        )
        rows.append(
            {
                "kind": kind,
                "domain": task_key["domain"],
                "task_id": task_key["task_id"],
                "step": task_key["step"],
                "path": str(path),
                "returncode": returncode,
                "stdout_chars": len(stdout),
                "empty_stdout": not bool(stdout),
                "contains_think": "<think>" in stdout,
                "contains_output_json_fence": "```json" in stdout,
                "has_end_marker": has_end_marker,
                "parsed_json": parsed is not None,
                "parsed_calls": len(calls),
                "mentions_actions": mentions_actions,
                "mentions_tool": mentions_tool,
                "likely_truncated": likely_truncated,
                "nonzero_returncode": _returncode_nonzero(returncode),
                "prompt_too_long": "prompt is too long" in stderr,
                "backend_crash": _returncode_negative(returncode),
            }
        )
    return rows


def _task_rows(
    task_rows: list[dict[str, str]],
    action_rows: list[dict[str, str]],
    raw_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_by_task: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        raw_by_task[(str(row["domain"]), str(row["task_id"]))].append(row)
    feedback_allowed: dict[tuple[str, str], int] = defaultdict(int)
    for row in action_rows:
        key = (row["domain"], row["task_id"])
        if "_feedback_" in row.get("round", "") and _bool(row.get("gateway_allowed", "")):
            feedback_allowed[key] += 1

    out: list[dict[str, Any]] = []
    for task in task_rows:
        key = (task["domain"], task["task_id"])
        raws = raw_by_task.get(key, [])
        step = [row for row in raws if row["kind"] == "step"]
        feedback = [row for row in raws if row["kind"] == "feedback"]
        out.append(
            {
                "domain": key[0],
                "task_id": key[1],
                "step_outputs": len(step),
                "feedback_outputs": len(feedback),
                "empty_step_outputs": sum(1 for row in step if row["empty_stdout"]),
                "step_outputs_with_think": sum(1 for row in step if row["contains_think"]),
                "step_outputs_with_parsed_calls": sum(
                    1 for row in step if int(row["parsed_calls"]) > 0
                ),
                "likely_truncated_step_outputs": sum(
                    1 for row in step if row["likely_truncated"]
                ),
                "gateway_allowed": int(task["gateway_allowed"]),
                "gateway_blocked": int(task["gateway_blocked"]),
                "feedback_attempted": _bool(task["feedback_attempted"]),
                "feedback_model_calls": int(task["feedback_model_calls"]),
                "feedback_gateway_allowed": feedback_allowed.get(key, 0),
                "action_reward": float(task["action_reward"]),
                "tool_oracle_pass": _bool(task["tool_oracle_pass"]),
            }
        )
    return out


def _summary(
    *,
    run_id: str,
    input_dir: Path,
    source_summary: dict[str, Any],
    raw_rows: list[dict[str, Any]],
    task_rows: list[dict[str, str]],
    action_rows: list[dict[str, str]],
    per_task: list[dict[str, Any]],
) -> dict[str, Any]:
    step_rows = [row for row in raw_rows if row["kind"] == "step"]
    feedback_rows = [row for row in raw_rows if row["kind"] == "feedback"]
    action_step_rows = [
        row for row in action_rows if str(row.get("round", "")).startswith("step_")
    ]
    step_outputs_empty = sum(1 for row in step_rows if row["empty_stdout"])
    step_outputs_with_think = sum(1 for row in step_rows if row["contains_think"])
    step_outputs_with_parsed_calls = sum(
        1 for row in step_rows if int(row["parsed_calls"]) > 0
    )
    step_outputs_likely_truncated = sum(
        1 for row in step_rows if row["likely_truncated"]
    )
    step_outputs_nonzero_returncode = sum(
        1 for row in step_rows if row["nonzero_returncode"]
    )
    step_outputs_prompt_too_long = sum(1 for row in step_rows if row["prompt_too_long"])
    step_outputs_backend_crash = sum(1 for row in step_rows if row["backend_crash"])
    step_outputs_nonempty_clean_end = sum(
        1
        for row in step_rows
        if not row["empty_stdout"]
        and not row["contains_think"]
        and row["has_end_marker"]
        and not row["likely_truncated"]
    )
    schema_controls_enabled = bool(source_summary.get("llama_json_schema_actions")) and bool(
        source_summary.get("llama_reasoning_off")
    )
    step_protocol_clean = bool(step_rows) and (
        step_outputs_empty == 0
        and step_outputs_with_think == 0
        and step_outputs_likely_truncated == 0
        and step_outputs_nonzero_returncode == 0
        and step_outputs_with_parsed_calls == len(step_rows)
    )
    output_protocol_clean_for_completed_steps = schema_controls_enabled and bool(step_rows) and (
        step_outputs_with_think == 0
        and step_outputs_likely_truncated == 0
        and step_outputs_nonempty_clean_end == len(step_rows) - step_outputs_empty
    )
    protocol_controlled = schema_controls_enabled and step_protocol_clean
    if protocol_controlled:
        protocol_gap_status = "controlled_on_source_shard"
        claim_interpretation = (
            "The source shard no longer shows a local output-protocol failure: "
            "schema-constrained reasoning-off step outputs are parseable bounded "
            "tool calls. Remaining utility gaps are task-planning/compiler-recall "
            "issues, not observed checker bypasses."
        )
        missing_for_stronger_utility_claim = [
            "persistent or batch local model serving to avoid per-step cold starts",
            "larger non-oracle compiler/refinement task loop with task-level reward",
            "approval-burden and recovery measurements on benchmark-derived denials",
        ]
    elif output_protocol_clean_for_completed_steps and (
        step_outputs_prompt_too_long > 0 or step_outputs_backend_crash > 0
    ):
        protocol_gap_status = "context_capacity_or_backend_error_open"
        claim_interpretation = (
            "Schema-constrained reasoning-off outputs are clean for completed "
            "steps, but the source shard is now limited by context capacity or "
            "backend reliability rather than by observed thinking/truncation."
        )
        missing_for_stronger_utility_claim = [
            "context compaction or larger-context local serving for long tool-result histories",
            "persistent or batch local model serving to avoid per-step cold starts",
            "larger non-oracle compiler/refinement task loop with task-level reward",
            "approval-burden and recovery measurements on benchmark-derived denials",
        ]
    else:
        protocol_gap_status = "open"
        claim_interpretation = (
            "The saved benchmark-derived recovery shard is bottlenecked by local "
            "planner/output protocol and compiler recall, not by observed tool "
            "errors or unsafe checker bypasses."
        )
        missing_for_stronger_utility_claim = [
            "persistent or batch local model serving to avoid per-step cold starts",
            "reliable no-thinking JSON output protocol or constrained decoding",
            "larger non-oracle compiler/refinement task loop with task-level reward",
            "approval-burden and recovery measurements on benchmark-derived denials",
        ]
    return {
        "run_id": run_id,
        "analysis": "benchmark task-loop model-output protocol gap over saved artifacts",
        "source_run_id": source_summary.get("run_id", input_dir.name),
        "source_input_dir": str(input_dir),
        "tasks_evaluated": int(source_summary["tasks_evaluated"]),
        "source_model_calls": int(source_summary["model_calls"]),
        "source_gateway_allowed": int(source_summary["gateway_allowed"]),
        "source_gateway_blocked": int(source_summary["gateway_blocked"]),
        "source_feedback_attempted_tasks": int(
            source_summary["feedback_attempted_tasks"]
        ),
        "source_feedback_model_calls": int(source_summary["feedback_model_calls"]),
        "source_feedback_gateway_allowed": int(
            source_summary["feedback_gateway_allowed"]
        ),
        "source_bound_reference_calls": int(source_summary["bound_reference_calls"]),
        "source_action_reward_pass_tasks": int(
            source_summary["action_reward_pass_tasks"]
        ),
        "source_tool_oracle_pass_tasks": int(source_summary["tool_oracle_pass_tasks"]),
        "step_raw_outputs": len(step_rows),
        "feedback_raw_outputs": len(feedback_rows),
        "step_outputs_empty": step_outputs_empty,
        "step_outputs_with_think": step_outputs_with_think,
        "step_outputs_with_json_fence": sum(
            1 for row in step_rows if row["contains_output_json_fence"]
        ),
        "step_outputs_with_end_marker": sum(1 for row in step_rows if row["has_end_marker"]),
        "step_outputs_with_parsed_json": sum(1 for row in step_rows if row["parsed_json"]),
        "step_outputs_with_parsed_calls": step_outputs_with_parsed_calls,
        "step_outputs_likely_truncated": step_outputs_likely_truncated,
        "step_outputs_nonzero_returncode": step_outputs_nonzero_returncode,
        "step_outputs_prompt_too_long": step_outputs_prompt_too_long,
        "step_outputs_backend_crash": step_outputs_backend_crash,
        "step_outputs_nonempty_clean_end": step_outputs_nonempty_clean_end,
        "tasks_with_likely_truncated_step_outputs": sum(
            1 for row in per_task if int(row["likely_truncated_step_outputs"]) > 0
        ),
        "tasks_with_empty_step_outputs": sum(
            1 for row in per_task if int(row["empty_step_outputs"]) > 0
        ),
        "step_action_rows": len(action_step_rows),
        "step_action_rows_allowed": sum(
            1 for row in action_step_rows if _bool(row.get("gateway_allowed", ""))
        ),
        "step_action_rows_blocked": sum(
            1 for row in action_step_rows if not _bool(row.get("gateway_allowed", ""))
        ),
        "task_rows": len(task_rows),
        "source_llama_json_schema_actions": bool(
            source_summary.get("llama_json_schema_actions")
        ),
        "source_llama_reasoning_off": bool(source_summary.get("llama_reasoning_off")),
        "step_protocol_clean": step_protocol_clean,
        "protocol_gap_status": protocol_gap_status,
        "claim_interpretation": claim_interpretation,
        "missing_for_stronger_utility_claim": missing_for_stronger_utility_claim,
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_benchmark": True,
        "project_head": _git(["rev-parse", "HEAD"]),
        "git_status": _git(["status", "--short"]),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def _task_key(stem: str) -> dict[str, str]:
    if "_step_" not in stem:
        return {"domain": "", "task_id": stem, "step": ""}
    prefix, step = stem.split("_step_", 1)
    if "_" not in prefix:
        return {"domain": prefix, "task_id": "", "step": step}
    domain, task_id = prefix.split("_", 1)
    return {"domain": domain, "task_id": task_id, "step": step}


def _stdout(path: Path) -> str:
    payload = _raw_payload(path)
    if isinstance(payload, dict):
        return str(payload.get("stdout", ""))
    return path.read_text(errors="replace")


def _raw_payload(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _returncode_nonzero(value: Any) -> bool:
    try:
        return int(value) != 0
    except (TypeError, ValueError):
        return False


def _returncode_negative(value: Any) -> bool:
    try:
        return int(value) < 0
    except (TypeError, ValueError):
        return False


def _digest_row(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _git(args: list[str]) -> str:
    import subprocess

    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        return ""
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
