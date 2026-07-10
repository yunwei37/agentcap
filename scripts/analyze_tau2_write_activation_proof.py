"""Audit write/high-impact tool activation proof readiness from saved tau2 artifacts.

This is a saved-artifact analysis. It does not run a model, execute tools,
sync datasets, or mint authority. It checks whether a write/high-impact
activation blocker has the same structured value proof required by the runtime
binder before a one-shot write lease could be considered.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import scripts.analyze_tau2_candidate_generation_repair as repair_analyzer  # noqa: E402
import scripts.run_tau2_local_llm_task_gateway as task_runner  # noqa: E402


PROOF_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "tool_type",
    "intent_evidence",
    "semantic_tokens",
    "value_context_complete",
    "collective_intent_tokens_covered",
    "value_proof_complete",
    "proof_gap_class",
    "proof_reason",
    "missing_args_json",
    "global_missing_tokens",
    "write_activation_candidate_ready",
    "next_experiment_target",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze tau2 write activation proof readiness")
    parser.add_argument("--run-id", default="R195")
    parser.add_argument(
        "--activation-csv",
        type=Path,
        default=Path("results/eval/R192/tool_activation_candidates.csv"),
    )
    parser.add_argument(
        "--action-results-csv",
        type=Path,
        default=Path("results/eval/R187/action_results.csv"),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("results/eval/R187"),
        help="Saved task-loop run directory containing samples.jsonl and step prompts.",
    )
    parser.add_argument("--prior-adjusted-missing", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R195"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_write_activation_proof(
        run_id=args.run_id,
        activation_csv=args.activation_csv,
        action_results_csv=args.action_results_csv,
        run_dir=args.run_dir,
        prior_adjusted_missing=args.prior_adjusted_missing,
        output_dir=args.output_dir,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "write_activation_proof.csv",
        result["proof_rows"],
        PROOF_FIELDS,
    )
    write_json(args.output_dir / "write_activation_proof_summary.json", result["summary"])
    write_csv(
        args.output_dir / "input_digests.csv",
        input_digest_rows(
            [
                args.activation_csv,
                args.action_results_csv,
                args.run_dir / "samples.jsonl",
                Path(__file__),
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (args.output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_write_activation_proof(
    *,
    run_id: str,
    activation_csv: Path,
    action_results_csv: Path,
    run_dir: Path,
    prior_adjusted_missing: int,
    output_dir: Path,
) -> dict[str, Any]:
    activation_rows = [
        row
        for row in read_csv(activation_csv)
        if str(row.get("activation_kind", ""))
        == "write_or_high_impact_tool_activation_requires_value_proof"
    ]
    action_rows = read_csv(action_results_csv)
    records_by_task = repair_analyzer.load_records_by_task(run_dir)
    proof_rows = [
        build_proof_row(
            activation_row=row,
            action_rows=action_rows,
            record=records_by_task.get(repair_analyzer.task_key(row), {}),
        )
        for row in activation_rows
    ]
    summary = build_summary(
        run_id=run_id,
        activation_csv=activation_csv,
        action_results_csv=action_results_csv,
        run_dir=run_dir,
        output_dir=output_dir,
        prior_adjusted_missing=prior_adjusted_missing,
        activation_rows=activation_rows,
        action_rows=action_rows,
        proof_rows=proof_rows,
    )
    return {"proof_rows": proof_rows, "summary": summary}


def build_proof_row(
    *,
    activation_row: dict[str, str],
    action_rows: list[dict[str, Any]],
    record: dict[str, Any],
) -> dict[str, Any]:
    args = parse_json_object(activation_row.get("args_json", "{}"))
    intent_evidence = write_intent_evidence(
        tool=str(activation_row.get("tool", "")),
        task_text=task_text_from_record(record),
    )
    template = {
        "id": (
            "write-activation-proof:"
            f"{activation_row.get('domain')}:{activation_row.get('task_id')}:"
            f"{activation_row.get('event_id')}"
        ),
        "tool": str(activation_row.get("tool", "")),
        "object": (
            f"tau2.{activation_row.get('domain')}.assistant."
            f"{activation_row.get('tool')}"
        ),
        "static_args": {},
        "runtime_args": list(args),
        "allowed_arg_keys": list(args),
        "intent_evidence": intent_evidence,
        "tool_type": str(activation_row.get("tool_type", "write") or "write"),
        "proof_required": True,
    }
    proof = task_runner.runtime_value_proof_status(
        template=template,
        args=args,
        action_rows=action_rows,
        require_value_proof=True,
    )
    tokens = [str(token) for token in proof.get("tokens", [])]
    missing_args = proof.get("missing_args", {})
    if not isinstance(missing_args, dict):
        missing_args = {}
    global_missing = [str(token) for token in proof.get("global_missing_tokens", [])]
    value_context_complete = not missing_context_values(missing_args)
    collective_covered = not global_missing
    proof_complete = bool(proof.get("complete", False))
    gap_class = proof_gap_class(
        proof_complete=proof_complete,
        value_context_complete=value_context_complete,
        collective_covered=collective_covered,
    )
    return {
        "source_run_id": str(activation_row.get("source_run_id", "")),
        "domain": str(activation_row.get("domain", "")),
        "task_id": str(activation_row.get("task_id", "")),
        "event_id": str(activation_row.get("event_id", "")),
        "tool": str(activation_row.get("tool", "")),
        "args_json": json.dumps(args, sort_keys=True),
        "tool_type": str(activation_row.get("tool_type", "")),
        "intent_evidence": intent_evidence,
        "semantic_tokens": "|".join(tokens),
        "value_context_complete": value_context_complete,
        "collective_intent_tokens_covered": collective_covered,
        "value_proof_complete": proof_complete,
        "proof_gap_class": gap_class,
        "proof_reason": str(proof.get("reason", "")),
        "missing_args_json": json.dumps(missing_args, sort_keys=True),
        "global_missing_tokens": "|".join(global_missing),
        "write_activation_candidate_ready": proof_complete,
        "next_experiment_target": next_experiment_target(gap_class),
    }


def task_text_from_record(record: dict[str, Any]) -> str:
    contexts = repair_analyzer.prompt_contexts_from_record(record)
    if not contexts:
        return ""
    task_text = str(contexts[0].get("task_text", ""))
    try:
        parsed = json.loads(task_text)
    except json.JSONDecodeError:
        return task_text
    instructions = (
        ((parsed.get("user_scenario") or {}).get("instructions") or {})
        if isinstance(parsed, dict)
        else {}
    )
    if isinstance(instructions, dict):
        fields = [
            str(instructions.get("reason_for_call", "")),
            str(instructions.get("task_instructions", "")),
            str(instructions.get("known_info", "")),
        ]
        return " ".join(field for field in fields if field and field != ".")
    return task_text


def write_intent_evidence(*, tool: str, task_text: str) -> str:
    text = " ".join(str(task_text or "").split())
    if tool.startswith("return_"):
        match = re.search(r"\breturn\b(?P<clause>[^.]+)", text, flags=re.IGNORECASE)
        if match:
            return f"return{match.group('clause')}".strip()
    return text


def proof_gap_class(
    *,
    proof_complete: bool,
    value_context_complete: bool,
    collective_covered: bool,
) -> str:
    if proof_complete:
        return "write_activation_value_proof_complete"
    if not value_context_complete:
        return "missing_structured_value_context"
    if collective_covered:
        return "collective_tokens_present_but_leaf_threshold_missing"
    return "missing_global_intent_tokens"


def missing_context_values(missing_args: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for values in missing_args.values():
        if not isinstance(values, list):
            continue
        for value in values:
            text = str(value)
            if text.startswith("missing context for "):
                missing.append(text.removeprefix("missing context for "))
    return missing


def next_experiment_target(gap_class: str) -> str:
    if gap_class == "write_activation_value_proof_complete":
        return "lower_write_activation_candidate_to_one_shot_runtime_lease"
    if gap_class == "collective_tokens_present_but_leaf_threshold_missing":
        return "design_grouped_list_value_proof_for_multi_item_write"
    if gap_class == "missing_structured_value_context":
        return "gather_or_preserve_structured_item_context_before_write_activation"
    return "derive_narrower_write_intent_or_collect_missing_intent_evidence"


def build_summary(
    *,
    run_id: str,
    activation_csv: Path,
    action_results_csv: Path,
    run_dir: Path,
    output_dir: Path,
    prior_adjusted_missing: int,
    activation_rows: list[dict[str, str]],
    action_rows: list[dict[str, Any]],
    proof_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    gap_counts = Counter(str(row.get("proof_gap_class", "")) for row in proof_rows)
    complete_rows = [
        row for row in proof_rows if truthy(row.get("value_proof_complete", ""))
    ]
    return {
        "run_id": run_id,
        "analysis": "saved tau2 write activation proof-readiness audit",
        "activation_csv": str(activation_csv),
        "action_results_csv": str(action_results_csv),
        "run_dir": str(run_dir),
        "output_dir": str(output_dir),
        "project_git_commit": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "machine": platform.platform(),
        "model_or_tool_execution": False,
        "dataset_sync": False,
        "official_tau2_score_changed": False,
        "prior_adjusted_missing": prior_adjusted_missing,
        "input_write_activation_blockers": len(activation_rows),
        "action_log_rows_scanned": len(action_rows),
        "proof_complete_write_activation_candidates": len(complete_rows),
        "proof_gap_class_counts": dict(sorted(gap_counts.items())),
        "potential_adjusted_missing_after_complete_write_activation": (
            prior_adjusted_missing - len(complete_rows)
        ),
        "ready_event_ids": [str(row.get("event_id", "")) for row in complete_rows],
        "notes": [
            "This audit reuses the runtime structured value-proof predicate.",
            "It does not expose hidden reference actions to an online planner and does not mint authority.",
            (
                "A complete proof row is a candidate for a future bounded activation run, "
                "not an official score change."
            ),
        ],
    }


def parse_json_object(raw: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
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
        rows.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
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
