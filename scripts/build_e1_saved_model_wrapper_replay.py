"""Replay saved local-model proposals under wrapper-policy families.

This E1 analysis reads existing tau2 task-gateway mismatch annotations and
asks a counterfactual action-level question: which saved model-proposed calls
would each wrapper family accept? It does not run a model, execute tools,
clone repositories, sync datasets, or inspect benchmark hidden state.
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


DEFAULT_MISMATCH_CSVS = (
    Path("results/eval/R035/model_call_mismatches.csv"),
    Path("results/eval/R038/model_call_mismatches.csv"),
)

CATEGORY_EXACT = "exact_executed"
CATEGORY_SAME_TOOL_WRONG_ARGS = "off_lease_same_tool_wrong_args"
CATEGORY_WRONG_OR_HALLUCINATED_TOOL = "off_lease_wrong_or_hallucinated_tool"
CATEGORY_REPEATED_OR_CONSUMED_EXACT = "off_lease_repeated_or_consumed_exact_args"

POLICY_INTENTCAP_SAVED_GATEWAY = "intentcap_saved_gateway"
POLICY_INTENTCAP_EXACT_LEASE = "intentcap_exact_lease"
POLICY_TASK_REFERENCE_TOOL_ACL = "task_reference_tool_acl"
POLICY_BROAD_PROPOSED_TOOL_ACL = "broad_proposed_tool_acl"

POLICIES = (
    POLICY_INTENTCAP_SAVED_GATEWAY,
    POLICY_INTENTCAP_EXACT_LEASE,
    POLICY_TASK_REFERENCE_TOOL_ACL,
    POLICY_BROAD_PROPOSED_TOOL_ACL,
)

REPLAY_FIELDS = [
    "source_file",
    "source_mismatch_run",
    "source_run_id",
    "domain",
    "task_id",
    "round",
    "index",
    "model_tool",
    "model_args_json",
    "category",
    "policy",
    "policy_allowed",
    "exact_reference_call",
    "off_reference_call",
    "exact_reference_accepted",
    "off_reference_accepted",
    "same_tool_wrong_args_accepted",
    "wrong_or_hallucinated_tool_accepted",
    "repeated_or_consumed_exact_args_accepted",
    "observed_gateway_allowed",
    "observed_executed",
    "policy_reason",
]

POLICY_SUMMARY_FIELDS = [
    "policy",
    "policy_family",
    "total_model_calls",
    "exact_reference_calls",
    "off_reference_calls",
    "allowed_calls",
    "blocked_calls",
    "exact_reference_accepted",
    "off_reference_accepted",
    "same_tool_wrong_args_accepted",
    "wrong_or_hallucinated_tool_accepted",
    "repeated_or_consumed_exact_args_accepted",
    "blocked_off_reference_calls",
    "exact_proposal_preservation_rate",
    "off_reference_accept_rate",
    "false_accept_ratio_among_allowed",
    "tasks_with_off_reference_accepted",
    "notes",
]

RUN_POLICY_SUMMARY_FIELDS = [
    "source_run_id",
    "policy",
    "total_model_calls",
    "exact_reference_calls",
    "off_reference_calls",
    "allowed_calls",
    "exact_reference_accepted",
    "off_reference_accepted",
    "same_tool_wrong_args_accepted",
    "wrong_or_hallucinated_tool_accepted",
    "repeated_or_consumed_exact_args_accepted",
    "exact_proposal_preservation_rate",
    "off_reference_accept_rate",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build E1 saved-model wrapper replay")
    parser.add_argument("--run-id", default="R206E1M")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--mismatch-csv",
        dest="mismatch_csvs",
        action="append",
        type=Path,
        default=None,
        help="Saved model_call_mismatches.csv path; may be repeated.",
    )
    args = parser.parse_args()

    mismatch_csvs = tuple(args.mismatch_csvs) if args.mismatch_csvs else DEFAULT_MISMATCH_CSVS
    result = build_replay(run_id=args.run_id, mismatch_csvs=mismatch_csvs)
    write_outputs(args.output_dir, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def build_replay(
    *,
    run_id: str,
    mismatch_csvs: tuple[Path, ...] = DEFAULT_MISMATCH_CSVS,
) -> dict[str, Any]:
    raw_rows = _read_mismatch_rows(mismatch_csvs)
    call_rows, duplicate_rows_removed = _deduplicate_calls(raw_rows)
    replay_rows = _replay_rows(call_rows)
    policy_summary_rows = _policy_summary_rows(replay_rows)
    run_policy_summary_rows = _run_policy_summary_rows(replay_rows)
    summary = _summary(
        run_id=run_id,
        mismatch_csvs=mismatch_csvs,
        raw_rows=raw_rows,
        call_rows=call_rows,
        duplicate_rows_removed=duplicate_rows_removed,
        replay_rows=replay_rows,
        policy_summary_rows=policy_summary_rows,
    )
    return {
        "summary": summary,
        "replay_rows": replay_rows,
        "policy_summary_rows": policy_summary_rows,
        "run_policy_summary_rows": run_policy_summary_rows,
        "input_digests": [_file_digest(path) for path in mismatch_csvs],
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        output_dir / "e1_saved_model_wrapper_replay.csv",
        result["replay_rows"],
        REPLAY_FIELDS,
    )
    _write_rows(
        output_dir / "e1_saved_model_wrapper_policy_summary.csv",
        result["policy_summary_rows"],
        POLICY_SUMMARY_FIELDS,
    )
    _write_rows(
        output_dir / "e1_saved_model_wrapper_run_policy_summary.csv",
        result["run_policy_summary_rows"],
        RUN_POLICY_SUMMARY_FIELDS,
    )
    _write_rows(output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "e1_saved_model_wrapper_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())


def _read_mismatch_rows(mismatch_csvs: tuple[Path, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in mismatch_csvs:
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                copied = dict(row)
                copied["source_file"] = str(path)
                copied["source_mismatch_run"] = path.parent.name
                copied["source_run_id"] = (
                    copied.get("source_run_id") or copied.get("run_id") or path.parent.name
                )
                rows.append(copied)
    return rows


def _deduplicate_calls(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[str, ...]] = set()
    deduplicated: list[dict[str, Any]] = []
    for row in rows:
        key = _dedup_key(row)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(row)
    return deduplicated, len(rows) - len(deduplicated)


def _dedup_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("source_run_id") or row.get("run_id") or ""),
        str(row.get("domain") or ""),
        str(row.get("task_id") or ""),
        str(row.get("round") or ""),
        str(row.get("index") or ""),
        str(row.get("model_tool") or ""),
        _canonical_json(row.get("model_args_json")),
    )


def _replay_rows(call_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call_row in call_rows:
        for policy in POLICIES:
            allowed, reason = _policy_decision(policy, call_row)
            category = str(call_row.get("category") or "")
            exact = category == CATEGORY_EXACT
            off_reference = not exact
            rows.append(
                {
                    "source_file": str(call_row.get("source_file", "")),
                    "source_mismatch_run": str(call_row.get("source_mismatch_run", "")),
                    "source_run_id": str(call_row.get("source_run_id", "")),
                    "domain": str(call_row.get("domain", "")),
                    "task_id": str(call_row.get("task_id", "")),
                    "round": str(call_row.get("round", "")),
                    "index": str(call_row.get("index", "")),
                    "model_tool": str(call_row.get("model_tool", "")),
                    "model_args_json": _canonical_json(call_row.get("model_args_json")),
                    "category": category,
                    "policy": policy,
                    "policy_allowed": allowed,
                    "exact_reference_call": exact,
                    "off_reference_call": off_reference,
                    "exact_reference_accepted": allowed and exact,
                    "off_reference_accepted": allowed and off_reference,
                    "same_tool_wrong_args_accepted": (
                        allowed and category == CATEGORY_SAME_TOOL_WRONG_ARGS
                    ),
                    "wrong_or_hallucinated_tool_accepted": (
                        allowed and category == CATEGORY_WRONG_OR_HALLUCINATED_TOOL
                    ),
                    "repeated_or_consumed_exact_args_accepted": (
                        allowed and category == CATEGORY_REPEATED_OR_CONSUMED_EXACT
                    ),
                    "observed_gateway_allowed": _bool(call_row.get("gateway_allowed")),
                    "observed_executed": _bool(call_row.get("executed")),
                    "policy_reason": reason,
                }
            )
    return rows


def _policy_decision(policy: str, row: dict[str, Any]) -> tuple[bool, str]:
    category = str(row.get("category") or "")
    if policy == POLICY_INTENTCAP_SAVED_GATEWAY:
        allowed = _bool(row.get("gateway_allowed")) and _bool(row.get("executed"))
        return allowed, "observed saved gateway allowed and executed the one-shot call"
    if policy == POLICY_INTENTCAP_EXACT_LEASE:
        return category == CATEGORY_EXACT, "exact operation and arguments match the event lease"
    if policy == POLICY_TASK_REFERENCE_TOOL_ACL:
        allowed = category in {
            CATEGORY_EXACT,
            CATEGORY_SAME_TOOL_WRONG_ARGS,
            CATEGORY_REPEATED_OR_CONSUMED_EXACT,
        }
        return allowed, "task-reference tool ACL checks tool membership but not event arguments"
    if policy == POLICY_BROAD_PROPOSED_TOOL_ACL:
        return True, "broad proposed-tool ACL exposes every saved model-proposed tool"
    raise ValueError(f"unknown policy: {policy}")


def _policy_summary_rows(replay_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in replay_rows:
        grouped[str(row["policy"])].append(row)
    return [_summary_row(policy, grouped[policy]) for policy in POLICIES]


def _run_policy_summary_rows(replay_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in replay_rows:
        grouped[(str(row["source_run_id"]), str(row["policy"]))].append(row)
    rows: list[dict[str, Any]] = []
    for source_run_id, policy in sorted(grouped):
        summary = _summary_row(policy, grouped[(source_run_id, policy)])
        rows.append(
            {
                "source_run_id": source_run_id,
                "policy": policy,
                "total_model_calls": summary["total_model_calls"],
                "exact_reference_calls": summary["exact_reference_calls"],
                "off_reference_calls": summary["off_reference_calls"],
                "allowed_calls": summary["allowed_calls"],
                "exact_reference_accepted": summary["exact_reference_accepted"],
                "off_reference_accepted": summary["off_reference_accepted"],
                "same_tool_wrong_args_accepted": summary["same_tool_wrong_args_accepted"],
                "wrong_or_hallucinated_tool_accepted": summary[
                    "wrong_or_hallucinated_tool_accepted"
                ],
                "repeated_or_consumed_exact_args_accepted": summary[
                    "repeated_or_consumed_exact_args_accepted"
                ],
                "exact_proposal_preservation_rate": summary["exact_proposal_preservation_rate"],
                "off_reference_accept_rate": summary["off_reference_accept_rate"],
            }
        )
    return rows


def _summary_row(policy: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    exact_calls = sum(1 for row in rows if row["exact_reference_call"])
    off_reference_calls = sum(1 for row in rows if row["off_reference_call"])
    allowed = sum(1 for row in rows if row["policy_allowed"])
    exact_accepted = sum(1 for row in rows if row["exact_reference_accepted"])
    off_reference_accepted = sum(1 for row in rows if row["off_reference_accepted"])
    same_tool_wrong = sum(1 for row in rows if row["same_tool_wrong_args_accepted"])
    wrong_tool = sum(1 for row in rows if row["wrong_or_hallucinated_tool_accepted"])
    repeated = sum(1 for row in rows if row["repeated_or_consumed_exact_args_accepted"])
    tasks_with_off_reference = {
        (row["source_run_id"], row["domain"], row["task_id"])
        for row in rows
        if row["off_reference_accepted"]
    }
    return {
        "policy": policy,
        "policy_family": _policy_family(policy),
        "total_model_calls": total,
        "exact_reference_calls": exact_calls,
        "off_reference_calls": off_reference_calls,
        "allowed_calls": allowed,
        "blocked_calls": total - allowed,
        "exact_reference_accepted": exact_accepted,
        "off_reference_accepted": off_reference_accepted,
        "same_tool_wrong_args_accepted": same_tool_wrong,
        "wrong_or_hallucinated_tool_accepted": wrong_tool,
        "repeated_or_consumed_exact_args_accepted": repeated,
        "blocked_off_reference_calls": off_reference_calls - off_reference_accepted,
        "exact_proposal_preservation_rate": _rate(exact_accepted, exact_calls),
        "off_reference_accept_rate": _rate(off_reference_accepted, off_reference_calls),
        "false_accept_ratio_among_allowed": _rate(off_reference_accepted, allowed),
        "tasks_with_off_reference_accepted": len(tasks_with_off_reference),
        "notes": _policy_note(policy),
    }


def _policy_family(policy: str) -> str:
    if policy.startswith("intentcap_"):
        return "intentcap"
    if policy == POLICY_TASK_REFERENCE_TOOL_ACL:
        return "tool_only_task_acl"
    if policy == POLICY_BROAD_PROPOSED_TOOL_ACL:
        return "broad_tool_acl"
    return "other"


def _policy_note(policy: str) -> str:
    notes = {
        POLICY_INTENTCAP_SAVED_GATEWAY: (
            "Observed saved gateway behavior: only accepted calls that matched an active one-shot lease."
        ),
        POLICY_INTENTCAP_EXACT_LEASE: (
            "Counterfactual exact event lease: accepts exact reference operation and arguments only."
        ),
        POLICY_TASK_REFERENCE_TOOL_ACL: (
            "Tool-only task ACL: accepts correct task tools even when arguments or event budget are wrong."
        ),
        POLICY_BROAD_PROPOSED_TOOL_ACL: (
            "Broad proposed-tool ACL: accepts all saved model-proposed calls; upper-bounds permissive tool exposure."
        ),
    }
    return notes[policy]


def _summary(
    *,
    run_id: str,
    mismatch_csvs: tuple[Path, ...],
    raw_rows: list[dict[str, Any]],
    call_rows: list[dict[str, Any]],
    duplicate_rows_removed: int,
    replay_rows: list[dict[str, Any]],
    policy_summary_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    categories = Counter(str(row.get("category") or "") for row in call_rows)
    source_runs = sorted({str(row.get("source_run_id") or "") for row in call_rows})
    source_mismatch_runs = sorted({str(row.get("source_mismatch_run") or "") for row in call_rows})
    policy_rows = {str(row["policy"]): row for row in policy_summary_rows}
    intentcap_gateway = policy_rows[POLICY_INTENTCAP_SAVED_GATEWAY]
    exact_lease = policy_rows[POLICY_INTENTCAP_EXACT_LEASE]
    task_acl = policy_rows[POLICY_TASK_REFERENCE_TOOL_ACL]
    broad_acl = policy_rows[POLICY_BROAD_PROPOSED_TOOL_ACL]
    return {
        "run_id": run_id,
        "analysis": "E1 saved local-model proposal wrapper replay",
        "source_mismatch_runs": source_mismatch_runs,
        "source_model_runs": source_runs,
        "input_rows": len(raw_rows),
        "deduplicated_model_calls": len(call_rows),
        "duplicate_rows_removed": duplicate_rows_removed,
        "replay_rows": len(replay_rows),
        "category_counts": dict(sorted(categories.items())),
        "policy_order": list(POLICIES),
        "intentcap_saved_gateway_allowed_calls": intentcap_gateway["allowed_calls"],
        "intentcap_saved_gateway_off_reference_accepted": intentcap_gateway[
            "off_reference_accepted"
        ],
        "intentcap_exact_lease_allowed_calls": exact_lease["allowed_calls"],
        "intentcap_exact_lease_off_reference_accepted": exact_lease["off_reference_accepted"],
        "task_reference_tool_acl_off_reference_accepted": task_acl["off_reference_accepted"],
        "broad_proposed_tool_acl_off_reference_accepted": broad_acl["off_reference_accepted"],
        "saved_exact_proposals": intentcap_gateway["exact_reference_calls"],
        "intentcap_saved_gateway_exact_proposals_accepted": intentcap_gateway[
            "exact_reference_accepted"
        ],
        "intentcap_exact_lease_exact_proposals_accepted": exact_lease[
            "exact_reference_accepted"
        ],
        "task_reference_tool_acl_same_tool_wrong_args_accepted": task_acl[
            "same_tool_wrong_args_accepted"
        ],
        "broad_proposed_tool_acl_wrong_or_hallucinated_tool_accepted": broad_acl[
            "wrong_or_hallucinated_tool_accepted"
        ],
        "no_dataset_sync": True,
        "not_a_fresh_online_run": True,
        "not_a_task_success_result": True,
        "not_a_hidden_state_analysis": True,
        "claim_supported": (
            "On saved local-Qwen proposals, exact IntentCap leases preserve exact accepted "
            "reference calls while rejecting off-reference proposals that tool-only wrappers admit."
        ),
        "limitations": [
            "This is an action-level counterfactual replay over saved model proposals, not an online task trajectory.",
            "It does not measure model replanning, user-simulator interaction, approval burden, or recovery after denial.",
            "The broad_proposed_tool_acl row is a permissive saved-proposal proxy, not a complete domain catalog policy.",
        ],
        "input_digests": [_file_digest(path) for path in mismatch_csvs],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }


def _canonical_json(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if not isinstance(value, str) or not value:
        return "{}"
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    return json.dumps(parsed, sort_keys=True)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(os.path.basename(sys.executable))
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
