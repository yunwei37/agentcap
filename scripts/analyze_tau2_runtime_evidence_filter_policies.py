"""Simulate runtime-evidence candidate filter policies from saved R131 labels.

This script is an offline evaluator. It reads candidate-correctness labels from
R131, then compares non-oracle candidate filters against post-hoc oracle upper
bounds. It does not run models, execute tools, clone benchmarks, sync datasets,
or use reference labels to synthesize authority.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


STEP_KEY_FIELDS = ["source_run_id", "domain", "task_id", "step"]

POLICY_STEP_COLUMNS = [
    "policy",
    "uses_oracle_labels",
    "source_run_id",
    "domain",
    "task_id",
    "step",
    "selected",
    "abstain_reason",
    "selected_tool",
    "selected_args_json",
    "candidate_correctness",
    "rank_position",
    "rank_score",
    "rank_margin_to_next",
    "proof_status",
    "proof_probe",
    "selected_by_ranked_fallback",
    "exact_next_available",
    "any_exact_reference_available",
    "candidate_count",
]

POLICY_METRIC_COLUMNS = [
    "policy",
    "uses_oracle_labels",
    "description",
    "steps",
    "selected_steps",
    "abstained_steps",
    "selection_rate",
    "exact_next_available_steps",
    "selected_exact_next",
    "selected_any_exact_reference",
    "selected_exact_future",
    "selected_already_executed",
    "selected_same_tool_wrong_args",
    "selected_non_reference_tool",
    "selected_wrong_next",
    "exact_next_precision",
    "any_exact_reference_precision",
    "exact_next_recall_when_available",
    "wrong_next_rate",
    "steps_with_exact_next_but_policy_abstained",
    "steps_with_exact_next_but_policy_selected_wrong",
    "steps_without_exact_next_candidate",
]


@dataclass(frozen=True)
class Policy:
    name: str
    description: str
    uses_oracle_labels: bool
    selector: Callable[[list[dict[str, str]]], tuple[dict[str, str] | None, str]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate filter/planner policies over saved runtime-evidence candidates"
    )
    parser.add_argument("--run-id", default="R132")
    parser.add_argument(
        "--candidate-csv",
        type=Path,
        default=Path("results/eval/R131/runtime_evidence_candidate_correctness.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R132"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = read_candidate_rows(args.candidate_csv)
    result = evaluate_policies(candidates)
    summary = build_summary(
        args=args,
        candidates=candidates,
        policy_metrics=result["policy_metrics"],
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "runtime_evidence_filter_policy_steps.csv", result["policy_steps"])
    write_csv(
        args.output_dir / "runtime_evidence_filter_policy_metrics.csv",
        result["policy_metrics"],
    )
    (args.output_dir / "runtime_evidence_filter_policy_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(
        args.output_dir / "input_digests.csv",
        [
            {
                "path": str(args.candidate_csv),
                "sha256": sha256_file(args.candidate_csv),
                "bytes": args.candidate_csv.stat().st_size,
            }
        ],
    )
    (args.output_dir / "command.txt").write_text(" ".join(subprocess.list2cmdline([arg]) for arg in ["python", *subprocess.sys.argv]) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


def read_candidate_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def evaluate_policies(candidates: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    groups = group_by_step(candidates)
    policies = build_policies()
    step_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    for policy in policies:
        rows = [
            evaluate_step(policy, key, step_candidates)
            for key, step_candidates in sorted(groups.items(), key=_step_sort_key)
        ]
        step_rows.extend(rows)
        metric_rows.append(policy_metrics(policy, rows))
    return {"policy_steps": step_rows, "policy_metrics": metric_rows}


def group_by_step(candidates: list[dict[str, str]]) -> dict[tuple[str, str, str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        groups[step_key(row)].append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: int(row.get("rank_position") or 10**9))
    return dict(groups)


def build_policies() -> list[Policy]:
    return [
        Policy(
            name="rank_top_all",
            description="Select the top-ranked complete runtime-evidence candidate on every hint-bearing step.",
            uses_oracle_labels=False,
            selector=lambda rows: (rows[0], ""),
        ),
        Policy(
            name="r125_ranked_fallback_replay",
            description="Replay only the candidate actually selected by R125 deterministic ranked fallback.",
            uses_oracle_labels=False,
            selector=select_r125_ranked_fallback,
        ),
        Policy(
            name="rank_score_ge_50_margin_ge_0",
            description="Select top candidate when rank score is at least 50, matching R125 score threshold without empty-action gating.",
            uses_oracle_labels=False,
            selector=lambda rows: select_top_with_threshold(rows, min_score=50, min_margin=0),
        ),
        Policy(
            name="rank_score_ge_50_margin_ge_1",
            description="Select top candidate only when score is at least 50 and the top score is unique by at least 1 point.",
            uses_oracle_labels=False,
            selector=lambda rows: select_top_with_threshold(rows, min_score=50, min_margin=1),
        ),
        Policy(
            name="rank_score_ge_50_margin_ge_11",
            description="Select top candidate only when score is at least 50 and the top score beats the runner-up by more than the observed 10-point wrong-candidate gap.",
            uses_oracle_labels=False,
            selector=lambda rows: select_top_with_threshold(rows, min_score=50, min_margin=11),
        ),
        Policy(
            name="rank_score_ge_50_no_proof_probe",
            description="Select top candidate with score at least 50 while suppressing proof-probe candidates.",
            uses_oracle_labels=False,
            selector=lambda rows: select_top_with_threshold(
                rows,
                min_score=50,
                min_margin=0,
                allow_proof_probe=False,
            ),
        ),
        Policy(
            name="rank_score_ge_50_margin_ge_1_no_proof_probe",
            description="Select top candidate with score at least 50, unique top score, and no proof-probe marker.",
            uses_oracle_labels=False,
            selector=lambda rows: select_top_with_threshold(
                rows,
                min_score=50,
                min_margin=1,
                allow_proof_probe=False,
            ),
        ),
        Policy(
            name="oracle_exact_next_if_available",
            description="Post-hoc upper bound: select an exact-next reference candidate if this candidate pool contains one, otherwise abstain.",
            uses_oracle_labels=True,
            selector=select_oracle_exact_next,
        ),
        Policy(
            name="oracle_any_reference_if_available",
            description="Post-hoc upper bound for candidate relevance: select exact-next if present, otherwise any exact future/already-executed reference.",
            uses_oracle_labels=True,
            selector=select_oracle_any_reference,
        ),
    ]


def select_r125_ranked_fallback(rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, str]:
    selected = [row for row in rows if parse_bool(row.get("selected_by_ranked_fallback", ""))]
    if not selected:
        return None, "no_r125_ranked_fallback"
    return selected[0], ""


def select_top_with_threshold(
    rows: list[dict[str, str]],
    *,
    min_score: int,
    min_margin: int,
    allow_proof_probe: bool = True,
) -> tuple[dict[str, str] | None, str]:
    top = rows[0]
    if parse_int(top.get("rank_score")) < min_score:
        return None, "score_below_threshold"
    if parse_int(top.get("rank_margin_to_next")) < min_margin:
        return None, "margin_below_threshold"
    if not allow_proof_probe and parse_bool(top.get("proof_probe", "")):
        return None, "proof_probe_suppressed"
    return top, ""


def select_oracle_exact_next(rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, str]:
    for row in rows:
        if row.get("candidate_correctness") == "exact_next_reference":
            return row, ""
    return None, "no_exact_next_candidate"


def select_oracle_any_reference(rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, str]:
    exact_next, reason = select_oracle_exact_next(rows)
    if exact_next is not None:
        return exact_next, reason
    for row in rows:
        if is_any_exact_reference(row.get("candidate_correctness", "")):
            return row, ""
    return None, "no_exact_reference_candidate"


def evaluate_step(
    policy: Policy,
    key: tuple[str, str, str, str],
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    selected, reason = policy.selector(rows)
    exact_next_available = any(row.get("candidate_correctness") == "exact_next_reference" for row in rows)
    any_ref_available = any(is_any_exact_reference(row.get("candidate_correctness", "")) for row in rows)
    base = {
        "policy": policy.name,
        "uses_oracle_labels": policy.uses_oracle_labels,
        "source_run_id": key[0],
        "domain": key[1],
        "task_id": key[2],
        "step": key[3],
        "selected": selected is not None,
        "abstain_reason": reason if selected is None else "",
        "exact_next_available": exact_next_available,
        "any_exact_reference_available": any_ref_available,
        "candidate_count": len(rows),
    }
    if selected is None:
        return {
            **base,
            "selected_tool": "",
            "selected_args_json": "",
            "candidate_correctness": "",
            "rank_position": "",
            "rank_score": "",
            "rank_margin_to_next": "",
            "proof_status": "",
            "proof_probe": "",
            "selected_by_ranked_fallback": "",
        }
    return {
        **base,
        "selected_tool": selected.get("tool", ""),
        "selected_args_json": selected.get("args_json", ""),
        "candidate_correctness": selected.get("candidate_correctness", ""),
        "rank_position": selected.get("rank_position", ""),
        "rank_score": selected.get("rank_score", ""),
        "rank_margin_to_next": selected.get("rank_margin_to_next", ""),
        "proof_status": selected.get("proof_status", ""),
        "proof_probe": parse_bool(selected.get("proof_probe", "")),
        "selected_by_ranked_fallback": parse_bool(selected.get("selected_by_ranked_fallback", "")),
    }


def policy_metrics(policy: Policy, rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if row["selected"]]
    correctness = Counter(str(row["candidate_correctness"]) for row in selected)
    exact_next_available = sum(1 for row in rows if row["exact_next_available"])
    wrong_next = sum(
        1
        for row in selected
        if row["candidate_correctness"] != "exact_next_reference"
    )
    metric = {
        "policy": policy.name,
        "uses_oracle_labels": policy.uses_oracle_labels,
        "description": policy.description,
        "steps": len(rows),
        "selected_steps": len(selected),
        "abstained_steps": len(rows) - len(selected),
        "selection_rate": ratio(len(selected), len(rows)),
        "exact_next_available_steps": exact_next_available,
        "selected_exact_next": correctness["exact_next_reference"],
        "selected_any_exact_reference": sum(
            count for label, count in correctness.items() if is_any_exact_reference(label)
        ),
        "selected_exact_future": correctness["exact_future_reference"],
        "selected_already_executed": correctness["exact_already_executed_reference"],
        "selected_same_tool_wrong_args": correctness["same_tool_wrong_args"],
        "selected_non_reference_tool": correctness["non_reference_tool"],
        "selected_wrong_next": wrong_next,
        "exact_next_precision": ratio(correctness["exact_next_reference"], len(selected)),
        "any_exact_reference_precision": ratio(
            sum(count for label, count in correctness.items() if is_any_exact_reference(label)),
            len(selected),
        ),
        "exact_next_recall_when_available": ratio(
            correctness["exact_next_reference"],
            exact_next_available,
        ),
        "wrong_next_rate": ratio(wrong_next, len(selected)),
        "steps_with_exact_next_but_policy_abstained": sum(
            1 for row in rows if row["exact_next_available"] and not row["selected"]
        ),
        "steps_with_exact_next_but_policy_selected_wrong": sum(
            1
            for row in rows
            if row["exact_next_available"]
            and row["selected"]
            and row["candidate_correctness"] != "exact_next_reference"
        ),
        "steps_without_exact_next_candidate": sum(
            1 for row in rows if not row["exact_next_available"]
        ),
    }
    return metric


def build_summary(
    *,
    args: argparse.Namespace,
    candidates: list[dict[str, str]],
    policy_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    groups = group_by_step(candidates)
    metrics_by_policy = {row["policy"]: row for row in policy_metrics}
    return {
        "analysis": "saved local-Qwen tau2 runtime-evidence filter policy simulation",
        "run_id": args.run_id,
        "source_candidate_csv": str(args.candidate_csv),
        "candidate_rows": len(candidates),
        "steps_with_candidates": len(groups),
        "no_dataset_sync": True,
        "notes": [
            "This analysis reads R131 candidate-correctness labels only.",
            "It does not run models, execute tools, clone benchmarks, sync datasets, or reveal hidden reference actions to a model.",
            "Oracle policies are post-hoc upper bounds over the existing candidate pool, not implementable runtime policies.",
            "exact_next_reference is the task-correct next-action label; exact_future_reference is relevant but wrong for the current step.",
        ],
        "key_results": {
            "r125_ranked_fallback_exact_next_precision": metrics_by_policy[
                "r125_ranked_fallback_replay"
            ]["exact_next_precision"],
            "r125_ranked_fallback_selected_steps": metrics_by_policy[
                "r125_ranked_fallback_replay"
            ]["selected_steps"],
            "rank_score_ge_50_margin_ge_1_selected_steps": metrics_by_policy[
                "rank_score_ge_50_margin_ge_1"
            ]["selected_steps"],
            "rank_score_ge_50_margin_ge_1_exact_next_precision": metrics_by_policy[
                "rank_score_ge_50_margin_ge_1"
            ]["exact_next_precision"],
            "oracle_exact_next_available_steps": metrics_by_policy[
                "oracle_exact_next_if_available"
            ]["selected_steps"],
            "oracle_exact_next_recall_when_available": metrics_by_policy[
                "oracle_exact_next_if_available"
            ]["exact_next_recall_when_available"],
            "steps_without_exact_next_candidate": metrics_by_policy[
                "oracle_exact_next_if_available"
            ]["steps_without_exact_next_candidate"],
        },
        "policy_metrics": policy_metrics,
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "script_sha256": sha256_file(Path(__file__)),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def step_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return tuple(row.get(field, "") for field in STEP_KEY_FIELDS)  # type: ignore[return-value]


def _step_sort_key(item: tuple[tuple[str, str, str, str], list[dict[str, str]]]) -> tuple[str, int, int]:
    _, domain, task_id, step = item[0]
    return domain, parse_int(task_id), parse_int(step)


def is_any_exact_reference(label: str) -> bool:
    return label in {
        "exact_next_reference",
        "exact_future_reference",
        "exact_already_executed_reference",
    }


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_int(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    if path.name == "runtime_evidence_filter_policy_steps.csv":
        fieldnames = POLICY_STEP_COLUMNS
    elif path.name == "runtime_evidence_filter_policy_metrics.csv":
        fieldnames = POLICY_METRIC_COLUMNS
    else:
        fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


if __name__ == "__main__":
    main()
