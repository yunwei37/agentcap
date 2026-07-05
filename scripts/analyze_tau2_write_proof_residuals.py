"""Diagnose high-impact write proof residuals after repair-map execution.

This is a saved-artifact analysis over local tau2 task-loop runs. It does not
run a model, execute tools, sync datasets, or mint authority. Its purpose is to
separate three residual classes that R150 left entangled:

* high-impact repair-map writes whose arguments are visible but whose runtime
  value proof is incomplete;
* repeated/consumed-state references where the same tool+arguments already ran
  for a different reference event; and
* DB-feasible residuals that still require tool activation or upstream planning.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


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
INTENT_PROOF_STOPWORDS = {
    "able",
    "after",
    "agent",
    "also",
    "and",
    "any",
    "argument",
    "available",
    "before",
    "call",
    "current",
    "customer",
    "details",
    "from",
    "gather",
    "get",
    "identified",
    "identify",
    "into",
    "line",
    "must",
    "need",
    "needed",
    "needs",
    "prior",
    "prove",
    "reservation",
    "result",
    "retrieve",
    "satisfies",
    "task",
    "that",
    "the",
    "this",
    "tool",
    "user",
    "using",
    "value",
    "verify",
    "want",
    "wants",
    "with",
}
INTENT_TOKEN_ALIASES = {
    "disabled": ("disabled", "false", "off"),
    "enabled": ("enabled", "true", "on"),
    "laguardia": ("laguardia", "lga"),
    "philadelphia": ("philadelphia", "phl"),
}

WRITE_PROOF_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "action_round",
    "action_index",
    "gateway_reason",
    "runtime_binding_reason",
    "runtime_template_id",
    "compiler_run_id",
    "intent_evidence",
    "runtime_args",
    "intent_discriminator_tokens",
    "missing_proof_args",
    "arg_context_summary_json",
    "leaf_context_summary_json",
    "leaf_level_all_tokens_possible",
    "list_argument_context_gap",
    "alias_gap_tokens",
    "repair_map_candidate_ready",
    "next_mechanism_target",
]

REPEATED_STATE_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "actionability_class",
    "proof_status",
    "executed_same_call_event_ids",
    "executed_same_call_rounds",
    "executed_same_call_bound_reference_ids",
    "diagnosis",
    "next_mechanism_target",
]

BLOCKER_FIELDS = [
    "source_run_id",
    "domain",
    "task_id",
    "event_id",
    "tool",
    "args_json",
    "actionability_class",
    "next_experiment_target",
    "residual_blocker",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose tau2 write-proof residuals")
    parser.add_argument("--run-id", default="R151")
    parser.add_argument("--source-run-id", default="R148")
    parser.add_argument("--source-run-dir", type=Path, default=Path("results/eval/R148"))
    parser.add_argument(
        "--repair-execution-csv",
        type=Path,
        default=Path("results/eval/R149/repair_map_candidate_execution.csv"),
    )
    parser.add_argument(
        "--recovery-plan-csv",
        type=Path,
        default=Path("results/eval/R150/residual_recovery_candidate_map.csv"),
    )
    parser.add_argument(
        "--not-ready-csv",
        type=Path,
        default=Path("results/eval/R150/not_yet_candidate_ready_residuals.csv"),
    )
    parser.add_argument(
        "--compiler-run-dir",
        type=Path,
        action="append",
        default=None,
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R151"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_write_proof_residuals(
        run_id=args.run_id,
        source_run_id=args.source_run_id,
        source_run_dir=args.source_run_dir,
        repair_execution_csv=args.repair_execution_csv,
        recovery_plan_csv=args.recovery_plan_csv,
        not_ready_csv=args.not_ready_csv,
        compiler_run_dirs=args.compiler_run_dir
        or [Path("results/eval/R074"), Path("results/eval/R077")],
        output_dir=args.output_dir,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_write_proof_residuals(
    *,
    run_id: str,
    source_run_id: str,
    source_run_dir: Path,
    repair_execution_csv: Path,
    recovery_plan_csv: Path,
    not_ready_csv: Path,
    compiler_run_dirs: list[Path],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    action_rows = read_csv(source_run_dir / "action_results.csv")
    repair_rows = read_csv(repair_execution_csv)
    recovery_rows = read_csv(recovery_plan_csv)
    not_ready_rows = read_csv(not_ready_csv)
    compiler_rows = load_compiler_lease_rows(compiler_run_dirs)

    action_rows_by_task = group_rows_by_task(action_rows)
    repair_by_event = {str(row.get("event_id", "")): row for row in repair_rows}
    recovery_by_event = {str(row.get("event_id", "")): row for row in recovery_rows}

    write_rows = build_write_proof_rows(
        source_run_id=source_run_id,
        action_rows=action_rows,
        action_rows_by_task=action_rows_by_task,
        compiler_rows=compiler_rows,
        repair_by_event=repair_by_event,
        recovery_by_event=recovery_by_event,
    )
    repeated_rows = build_repeated_state_rows(
        source_run_id=source_run_id,
        recovery_rows=recovery_rows,
        action_rows_by_task=action_rows_by_task,
    )
    blocker_rows = [
        {
            "source_run_id": source_run_id,
            "domain": row.get("domain", ""),
            "task_id": row.get("task_id", ""),
            "event_id": row.get("event_id", ""),
            "tool": row.get("tool", ""),
            "args_json": row.get("args_json", ""),
            "actionability_class": row.get("actionability_class", ""),
            "next_experiment_target": row.get("next_experiment_target", ""),
            "residual_blocker": row.get("residual_blocker", ""),
        }
        for row in not_ready_rows
    ]
    summary = build_summary(
        run_id=run_id,
        source_run_id=source_run_id,
        source_run_dir=source_run_dir,
        repair_execution_csv=repair_execution_csv,
        recovery_plan_csv=recovery_plan_csv,
        not_ready_csv=not_ready_csv,
        compiler_run_dirs=compiler_run_dirs,
        write_rows=write_rows,
        repeated_rows=repeated_rows,
        blocker_rows=blocker_rows,
    )

    write_csv(output_dir / "write_proof_residuals.csv", write_rows, WRITE_PROOF_FIELDS)
    write_csv(output_dir / "repeated_consumed_residuals.csv", repeated_rows, REPEATED_STATE_FIELDS)
    write_csv(output_dir / "not_ready_residual_blockers.csv", blocker_rows, BLOCKER_FIELDS)
    write_json(output_dir / "write_proof_residual_summary.json", summary)
    write_csv(
        output_dir / "input_digests.csv",
        input_digest_rows(
            [
                source_run_dir / "action_results.csv",
                source_run_dir / "samples.jsonl",
                repair_execution_csv,
                recovery_plan_csv,
                not_ready_csv,
                *[path / "lease_results.csv" for path in compiler_run_dirs],
            ]
        ),
        ["path", "sha256", "bytes"],
    )
    (output_dir / "command.txt").write_text(command_text(), encoding="utf-8")
    return {
        "write_rows": write_rows,
        "repeated_rows": repeated_rows,
        "blocker_rows": blocker_rows,
        "summary": summary,
    }


def build_write_proof_rows(
    *,
    source_run_id: str,
    action_rows: list[dict[str, str]],
    action_rows_by_task: dict[tuple[str, str], list[dict[str, str]]],
    compiler_rows: list[dict[str, str]],
    repair_by_event: dict[str, dict[str, str]],
    recovery_by_event: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in action_rows:
        reason = str(row.get("runtime_binding_reason", ""))
        if not reason.startswith("missing runtime value proof"):
            continue
        tool = str(row.get("model_tool", ""))
        if not is_high_impact_tool(tool):
            continue
        args = parse_json_object(row.get("model_args_json", ""))
        event_id = str(row.get("event_id", ""))
        runtime_template_id = parse_runtime_template_id(reason)
        compiler_row = select_compiler_row(
            compiler_rows=compiler_rows,
            domain=str(row.get("domain", "")),
            task_id=str(row.get("task_id", "")),
            tool=tool,
            arg_keys=sorted(args),
        )
        runtime_args = parse_pipe_list(compiler_row.get("runtime_policy_args", "")) or sorted(args)
        intent_evidence = compiler_row.get("intent_evidence", "")
        tokens = intent_discriminator_tokens(
            intent_evidence,
            tool=tool,
            runtime_args=runtime_args,
        )
        prior_rows = rows_before_event(
            action_rows_by_task[(str(row.get("domain", "")), str(row.get("task_id", "")))],
            row,
        )
        arg_summary, missing_args = summarize_arg_contexts(args, runtime_args, prior_rows, tokens)
        leaf_summary = summarize_leaf_contexts(args, prior_rows, tokens)
        alias_gap_tokens = infer_alias_gap_tokens(tokens, arg_summary, leaf_summary)
        rows.append(
            {
                "source_run_id": source_run_id,
                "domain": row.get("domain", ""),
                "task_id": row.get("task_id", ""),
                "event_id": event_id,
                "tool": tool,
                "args_json": json.dumps(args, sort_keys=True),
                "action_round": row.get("round", ""),
                "action_index": row.get("index", ""),
                "gateway_reason": row.get("gateway_reason", ""),
                "runtime_binding_reason": reason,
                "runtime_template_id": runtime_template_id,
                "compiler_run_id": compiler_row.get("run_id", ""),
                "intent_evidence": intent_evidence,
                "runtime_args": "|".join(runtime_args),
                "intent_discriminator_tokens": "|".join(tokens),
                "missing_proof_args": "|".join(missing_args),
                "arg_context_summary_json": json.dumps(arg_summary, sort_keys=True),
                "leaf_context_summary_json": json.dumps(leaf_summary, sort_keys=True),
                "leaf_level_all_tokens_possible": all(
                    entry.get("passes_token_threshold") for entry in leaf_summary.values()
                ),
                "list_argument_context_gap": any(
                    isinstance(args.get(arg_name), list)
                    and arg_summary.get(arg_name, {}).get("context_count") == 0
                    and all(
                        leaf_summary.get(str(value), {}).get("context_count", 0) > 0
                        for value in args.get(arg_name, [])
                    )
                    for arg_name in runtime_args
                ),
                "alias_gap_tokens": "|".join(alias_gap_tokens),
                "repair_map_candidate_ready": truthy(
                    (recovery_by_event.get(event_id) or repair_by_event.get(event_id) or {}).get(
                        "eligible", ""
                    )
                )
                or str((recovery_by_event.get(event_id) or {}).get("proof_status", ""))
                == "repair_candidate_ready",
                "next_mechanism_target": write_next_target(arg_summary, leaf_summary, alias_gap_tokens),
            }
        )
    return sorted(rows, key=lambda item: (item["domain"], item["task_id"], item["event_id"]))


def build_repeated_state_rows(
    *,
    source_run_id: str,
    recovery_rows: list[dict[str, str]],
    action_rows_by_task: dict[tuple[str, str], list[dict[str, str]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in recovery_rows:
        if str(row.get("actionability_class", "")) != "candidate_selection_or_planning_gap":
            continue
        args = parse_json_object(row.get("args_json", ""))
        same_calls = [
            action
            for action in action_rows_by_task.get((str(row.get("domain", "")), str(row.get("task_id", ""))), [])
            if truthy(action.get("executed", ""))
            and str(action.get("model_tool", "")) == str(row.get("tool", ""))
            and parse_json_object(action.get("model_args_json", "")) == args
        ]
        rows.append(
            {
                "source_run_id": source_run_id,
                "domain": row.get("domain", ""),
                "task_id": row.get("task_id", ""),
                "event_id": row.get("event_id", ""),
                "tool": row.get("tool", ""),
                "args_json": json.dumps(args, sort_keys=True),
                "actionability_class": row.get("actionability_class", ""),
                "proof_status": row.get("proof_status", ""),
                "executed_same_call_event_ids": "|".join(
                    str(action.get("event_id", "")) for action in same_calls
                ),
                "executed_same_call_rounds": "|".join(
                    str(action.get("round", "")) for action in same_calls
                ),
                "executed_same_call_bound_reference_ids": "|".join(
                    str(action.get("bound_reference_event_id", "")) for action in same_calls
                ),
                "diagnosis": (
                    "same_tool_args_already_executed_for_different_reference"
                    if same_calls
                    else "existing_exact_candidate_not_selected"
                ),
                "next_mechanism_target": (
                    "repeated_event_selection_or_reference_accounting"
                    if same_calls
                    else "planner_confirm_existing_exact_candidate"
                ),
            }
        )
    return rows


def summarize_arg_contexts(
    args: dict[str, Any],
    runtime_args: list[str],
    prior_rows: list[dict[str, str]],
    tokens: list[str],
) -> tuple[dict[str, Any], list[str]]:
    summary: dict[str, Any] = {}
    missing: list[str] = []
    for arg_name in runtime_args:
        value = args.get(arg_name)
        contexts = executed_tool_result_contexts_for_value(value, prior_rows)
        matched = sorted({token for context in contexts for token in matched_intent_tokens(context, tokens)})
        passes = any(context_has_intent_tokens(context, tokens) for context in contexts)
        if not passes:
            missing.append(arg_name)
        summary[arg_name] = {
            "value": value,
            "context_count": len(contexts),
            "matched_tokens": matched,
            "missing_tokens": [token for token in tokens if token not in matched],
            "passes_token_threshold": passes,
            "context_tools": sorted(context_tools_for_value(value, prior_rows)),
        }
    return summary, missing


def summarize_leaf_contexts(
    args: dict[str, Any],
    prior_rows: list[dict[str, str]],
    tokens: list[str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for value in sorted({leaf for value in args.values() for leaf in leaf_values(value)}):
        contexts = executed_tool_result_contexts_for_value(value, prior_rows)
        matched = sorted({token for context in contexts for token in matched_intent_tokens(context, tokens)})
        summary[str(value)] = {
            "context_count": len(contexts),
            "matched_tokens": matched,
            "missing_tokens": [token for token in tokens if token not in matched],
            "passes_token_threshold": any(context_has_intent_tokens(context, tokens) for context in contexts),
            "context_tools": sorted(context_tools_for_value(value, prior_rows)),
        }
    return summary


def write_next_target(
    arg_summary: dict[str, Any],
    leaf_summary: dict[str, Any],
    alias_gap_tokens: list[str],
) -> str:
    if alias_gap_tokens:
        return "add_intent_discriminator_aliases_or_structured_value_proof"
    if any(entry.get("context_count", 0) == 0 for entry in arg_summary.values()):
        if any(entry.get("context_count", 0) > 0 for entry in leaf_summary.values()):
            return "make_list_write_args_leaf_provable"
        return "derive_read_probe_before_write"
    return "strengthen_write_value_proof_or_user_confirmation"


def infer_alias_gap_tokens(
    tokens: list[str],
    arg_summary: dict[str, Any],
    leaf_summary: dict[str, Any],
) -> list[str]:
    matched = {
        token
        for entry in [*arg_summary.values(), *leaf_summary.values()]
        for token in entry.get("matched_tokens", [])
    }
    gaps: list[str] = []
    for token in tokens:
        if token in matched:
            continue
        if token in {"small", "tshirt", "shirts", "shirt"}:
            gaps.append(token)
    return gaps


def build_summary(
    *,
    run_id: str,
    source_run_id: str,
    source_run_dir: Path,
    repair_execution_csv: Path,
    recovery_plan_csv: Path,
    not_ready_csv: Path,
    compiler_run_dirs: list[Path],
    write_rows: list[dict[str, Any]],
    repeated_rows: list[dict[str, Any]],
    blocker_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    blocker_counts = Counter(str(row.get("residual_blocker", "")) for row in blocker_rows)
    target_counts = Counter(str(row.get("next_mechanism_target", "")) for row in write_rows)
    return {
        "run_id": run_id,
        "source_run_id": source_run_id,
        "source_run_dir": str(source_run_dir),
        "repair_execution_csv": str(repair_execution_csv),
        "recovery_plan_csv": str(recovery_plan_csv),
        "not_ready_csv": str(not_ready_csv),
        "compiler_run_dirs": [str(path) for path in compiler_run_dirs],
        "project_git_commit": git_output(["git", "rev-parse", "HEAD"]),
        "machine": platform.platform(),
        "model_or_tool_execution": False,
        "dataset_sync": False,
        "high_impact_write_value_proof_blocks": len(write_rows),
        "blocked_write_events": [row["event_id"] for row in write_rows],
        "write_next_target_counts": dict(sorted(target_counts.items())),
        "write_rows_with_list_argument_context_gap": sum(
            1 for row in write_rows if truthy(row.get("list_argument_context_gap", ""))
        ),
        "write_rows_with_alias_gap_tokens": sum(
            1 for row in write_rows if str(row.get("alias_gap_tokens", ""))
        ),
        "repeated_or_consumed_state_residuals": len(repeated_rows),
        "repeated_state_events": [row["event_id"] for row in repeated_rows],
        "not_ready_db_feasible_residuals": len(blocker_rows),
        "not_ready_blocker_counts": dict(sorted(blocker_counts.items())),
    }


def load_compiler_lease_rows(compiler_run_dirs: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for run_dir in compiler_run_dirs:
        path = run_dir / "lease_results.csv"
        if not path.exists():
            continue
        for row in read_csv(path):
            rows.append({**row, "_compiler_run_dir": str(run_dir)})
    return rows


def select_compiler_row(
    *,
    compiler_rows: list[dict[str, str]],
    domain: str,
    task_id: str,
    tool: str,
    arg_keys: list[str],
) -> dict[str, str]:
    candidates = [
        row
        for row in compiler_rows
        if str(row.get("domain", "")) == domain
        and str(row.get("task_id", "")) == task_id
        and str(row.get("tool", "")) == tool
        and truthy(row.get("valid_tool", ""))
    ]
    arg_key_set = set(arg_keys)
    exact = [
        row
        for row in candidates
        if set(parse_pipe_list(row.get("equals_any_policy_args", "")))
        | set(parse_pipe_list(row.get("runtime_policy_args", "")))
        == arg_key_set
    ]
    if exact:
        return exact[-1]
    return candidates[-1] if candidates else {}


def group_rows_by_task(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("domain", "")), str(row.get("task_id", "")))].append(row)
    return dict(grouped)


def rows_before_event(task_rows: list[dict[str, str]], target: dict[str, str]) -> list[dict[str, str]]:
    prior: list[dict[str, str]] = []
    for row in task_rows:
        if row is target:
            break
        if (
            str(row.get("round", "")) == str(target.get("round", ""))
            and str(row.get("index", "")) == str(target.get("index", ""))
            and str(row.get("event_id", "")) == str(target.get("event_id", ""))
        ):
            break
        prior.append(row)
    return prior


def parse_runtime_template_id(reason: str) -> str:
    match = re.search(r"missing runtime value proof for (.+?): runtime value context", reason)
    return match.group(1) if match else ""


def intent_discriminator_tokens(intent: str, *, tool: str, runtime_args: list[str]) -> list[str]:
    ignored = set(INTENT_PROOF_STOPWORDS)
    ignored.update(split_identifier(tool))
    for arg_name in runtime_args:
        ignored.update(split_identifier(arg_name))

    tokens: list[str] = []
    for token in re.findall(r"[a-z][a-z0-9]+", intent.lower()):
        if len(token) < 3 or token in ignored:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens[:8]


def split_identifier(value: str) -> set[str]:
    return {part for part in re.split(r"[^a-zA-Z0-9]+|_", value.lower()) if part}


def executed_tool_result_contexts_for_value(
    value: Any,
    action_rows: list[dict[str, str]],
) -> list[str]:
    contexts: list[str] = []
    for row in action_rows:
        if not truthy(row.get("executed", "")):
            continue
        for decoded in decode_nested_json_values(str(row.get("tool_result_preview", ""))):
            for context in json_contexts_containing_value(decoded, value):
                text = json.dumps(context, sort_keys=True, default=str)
                if text not in contexts:
                    contexts.append(text)
    return contexts


def context_tools_for_value(value: Any, action_rows: list[dict[str, str]]) -> set[str]:
    tools: set[str] = set()
    for row in action_rows:
        if not truthy(row.get("executed", "")):
            continue
        for decoded in decode_nested_json_values(str(row.get("tool_result_preview", ""))):
            if json_contains_value(decoded, value):
                tools.add(str(row.get("model_tool", "")))
                break
    return tools


def decode_nested_json_values(text: str) -> list[Any]:
    try:
        root = json.loads(text)
    except json.JSONDecodeError:
        return []
    decoded = [root]
    queue = [root]
    while queue:
        value = queue.pop(0)
        children: list[Any] = []
        if isinstance(value, dict):
            children.extend(value.values())
        elif isinstance(value, list):
            children.extend(value)
        for child in children:
            if not isinstance(child, str):
                continue
            stripped = child.strip()
            if not stripped or stripped[0] not in "[{":
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            decoded.append(parsed)
            queue.append(parsed)
    return decoded


def json_contexts_containing_value(node: Any, target: Any) -> list[Any]:
    contexts: list[Any] = []
    if json_contains_value(node, target):
        contexts.append(node)
    if isinstance(node, dict):
        for child in node.values():
            contexts.extend(json_contexts_containing_value(child, target))
    elif isinstance(node, list):
        for child in node:
            contexts.extend(json_contexts_containing_value(child, target))
    return contexts


def json_contains_value(node: Any, target: Any) -> bool:
    if node == target:
        return True
    if isinstance(node, dict):
        return any(json_contains_value(child, target) for child in node.values())
    if isinstance(node, list):
        return any(json_contains_value(child, target) for child in node)
    return False


def context_has_intent_tokens(context: str, tokens: list[str]) -> bool:
    lower_context = context.lower()
    if not tokens:
        return True
    matches = 0
    for token in tokens:
        aliases = INTENT_TOKEN_ALIASES.get(token, (token,))
        if any(alias.lower() in lower_context for alias in aliases):
            matches += 1
    required = len(tokens) if any(token in INTENT_TOKEN_ALIASES for token in tokens) else min(2, len(tokens))
    return matches >= required


def matched_intent_tokens(context: str, tokens: list[str]) -> list[str]:
    lower_context = context.lower()
    matched: list[str] = []
    for token in tokens:
        aliases = INTENT_TOKEN_ALIASES.get(token, (token,))
        if any(alias.lower() in lower_context for alias in aliases):
            matched.append(token)
    return matched


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


def parse_pipe_list(raw: Any) -> list[str]:
    return [part for part in str(raw or "").split("|") if part]


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
