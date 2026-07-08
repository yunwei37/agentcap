"""Audit paper-facing numbers against saved IntentCap result artifacts.

This script is intentionally read-only with respect to datasets and model runs.
It checks that the Chinese paper's main evaluation numbers are backed by local
result summaries, then writes a small reproducibility report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_PAPER = Path("docs/autopaper/intentcap-paper-zh.tex")

FIELDNAMES = [
    "claim_id",
    "paper_number",
    "source_path",
    "source_field",
    "expected",
    "actual",
    "status",
    "notes",
]

DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit paper evidence numbers against local results")
    parser.add_argument("--run-id", default="R237PAPERAUDIT")
    parser.add_argument("--paper", type=Path, default=DEFAULT_PAPER)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    paper_text = args.paper.read_text()
    rows: list[dict[str, Any]] = []
    input_paths = {args.paper}

    for check in _checks():
        source_path = Path(check["source_path"])
        input_paths.add(source_path)
        actual = _extract(source_path, check)
        expected = check["expected"]
        status = _compare(actual, expected, check.get("compare", "exact"))
        paper_number = check["paper_number"]
        if paper_number and paper_number not in paper_text:
            status = "fail"
            notes = f"paper token not found: {paper_number}"
        else:
            notes = check.get("notes", "")
        rows.append(
            {
                "claim_id": check["claim_id"],
                "paper_number": paper_number,
                "source_path": str(source_path),
                "source_field": check["source_field"],
                "expected": expected,
                "actual": actual,
                "status": status,
                "notes": notes,
            }
        )

    failed = [row for row in rows if row["status"] != "ok"]
    summary = {
        "analysis": "paper-facing evidence number audit",
        "run_id": args.run_id,
        "paper": str(args.paper),
        "checks_total": len(rows),
        "checks_failed": len(failed),
        "checks_passed": len(rows) - len(failed),
        "audit_status": "ok" if not failed else "failed",
        "failed_claims": [row["claim_id"] for row in failed],
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_new_experiment": True,
        "machine": platform.platform(),
        "python": platform.python_version(),
        "project_head": _git("rev-parse", "HEAD"),
        "notes": [
            "The audit reads the paper and saved result summaries only.",
            "It does not execute tools, call models, clone repositories, sync datasets, or download data.",
            "Some source artifacts still use historical field names such as dangerous_accepted; the paper-facing terminology is unsafe accept/execution.",
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output_dir / "paper_evidence_audit.csv", rows, FIELDNAMES)
    digests = [_digest(path) for path in sorted(input_paths, key=str)]
    _write_csv(args.output_dir / "input_digests.csv", digests, DIGEST_FIELDS)
    (args.output_dir / "paper_evidence_audit_summary.json").write_text(
        json.dumps({**summary, "input_digests": digests}, indent=2, sort_keys=True)
    )
    (args.output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if failed else 0


def _checks() -> list[dict[str, Any]]:
    return [
        _json("E1.security.events", "3,746", "results/eval/R202E1/e1_security_wrapper_summary.json", "intentcap_matched_events", 3746),
        _json("E1.security.unsafe_accepts", "0 个 unsafe accepts", "results/eval/R202E1/e1_security_wrapper_summary.json", "intentcap_dangerous_accepted", 0),
        _json("E1.utility.reference_actions", "3,813/3,813", "results/eval/R203E1U/e1_utility_wrapper_summary.json", "assistant_reference_actions", 3813),
        _json("E1.utility.oracle_pass", "2,554/2,556", "results/eval/R203E1U/e1_utility_wrapper_summary.json", "intentcap_replay_tool_oracle_pass_tasks", 2554),
        _json("E1.utility.oracle_applicable", "2,554/2,556", "results/eval/R203E1U/e1_utility_wrapper_summary.json", "intentcap_replay_tool_oracle_applicable_tasks", 2556),
        _json("E1.saved_qwen.exact", "11/11", "results/eval/R206E1M/e1_saved_model_wrapper_summary.json", "intentcap_saved_gateway_exact_proposals_accepted", 11),
        _json("E1.saved_qwen.off_reference", "47/47", "results/eval/R206E1M/e1_saved_model_wrapper_summary.json", "intentcap_saved_gateway_off_reference_accepted", 0),
        _json("E1.matched.leased_schema_avg", "2.61", "results/eval/R216E1MATCH8/matched_online_summary.json", "leased.tool_schema_count_avg", 2.61, compare="round2"),
        _json("E1.matched.all_schema_avg", "14.72", "results/eval/R216E1MATCH8/matched_online_summary.json", "all_tools.tool_schema_count_avg", 14.72, compare="round2"),
        _json("E1.matched.leased_calls", "62", "results/eval/R216E1MATCH8/matched_online_summary.json", "leased.model_calls", 62),
        _json("E1.matched.all_calls", "74", "results/eval/R216E1MATCH8/matched_online_summary.json", "all_tools.model_calls", 74),
        _json("E1.matched.reward", "8/18", "results/eval/R216E1MATCH8/matched_online_summary.json", "leased.action_reward_pass_tasks", 8),
        _json("E1.matched.tool_oracle", "0/18", "results/eval/R216E1MATCH8/matched_online_summary.json", "leased.tool_oracle_pass_tasks", 0),
        _json("E3.authority.events", "8,696", "results/eval/R220AUTHCHAR/authority_input_characterization_summary.json", "events", 8696),
        _json("E3.authority.multiple_issuers", "8,691", "results/eval/R220AUTHCHAR/authority_input_characterization_summary.json", "events_requiring_multiple_issuer_classes", 8691),
        _json("E3.authority.env_runtime", "198", "results/eval/R220AUTHCHAR/authority_input_characterization_summary.json", "events_requiring_env_runtime_evidence", 198),
        _json("E3.authority.substitution_attempts", "3,593", "results/eval/R220AUTHCHAR/authority_input_characterization_summary.json", "denied_events_with_class_substitution_attempt", 3593),
        _json("E3.labels.samples", "48 个 sampled protected-decision labels", "results/eval/R221NATPD/natural_pd_labeling_summary.json", "samples", 48),
        _json("E3.labels.protected", "45 个样本", "results/eval/R221NATPD/natural_pd_labeling_summary.json", "protected_decision_labels", 45),
        _json("E3.labels.multi", "43 个需要多个 issuer classes", "results/eval/R221NATPD/natural_pd_labeling_summary.json", "samples_requiring_multiple_issuers", 43),
        _json("E3.labels.env", "13 个需要 env/runtime proof", "results/eval/R221NATPD/natural_pd_labeling_summary.json", "samples_requiring_env", 13),
        _json("E3.labels.substitution", "37 个暴露 class-substitution attempts", "results/eval/R221NATPD/natural_pd_labeling_summary.json", "samples_with_substitution_attempt", 37),
        _json("E3.workflow.executed", "执行 2 个合法 workflow events", "results/eval/R217E3POLICY/gateway/gateway_summary.json", "executed_events", 2),
        _json("E3.workflow.blocked", "阻止 7 个 lifecycle/issuer violations", "results/eval/R217E3POLICY/gateway/gateway_summary.json", "blocked_events", 7),
        _json("E3.workflow.baseline_accepts", "接受全部 9 个 events", "results/eval/R217E3POLICY/closest_baseline/closest_baseline_labeler_summary.json", "baseline_rows.0.accept", 9),
        _json("E3.mcptox.schema_allowed", "24/24 个合法 schema-use events", "results/eval/R219E3LIFT/benchmark_residual_lift_summary.json", "checker_allowed", 24),
        _json("E3.mcptox.promotions_blocked", "48/48 个 trusted-tool-metadata", "results/eval/R219E3LIFT/benchmark_residual_lift_summary.json", "checker_blocked", 48),
        _json("E3.skill.substitutions", "3/3 个 tool result", "results/eval/R224SKILLBOUNDARY/skill_instruction_boundary_summary.json", "blocked_instruction_substitutions", 3),
        _json("E4.env.allowed", "执行 4 个授权 effects", "results/eval/R211ENVBACKEND/env_backend_summary.json", "intentcap_executed", 4),
        _json("E4.env.blocked", "阻止 6 个 violations", "results/eval/R211ENVBACKEND/env_backend_summary.json", "intentcap_blocked", 6),
        _json("E4.env.unsafe", "0 个 unsafe executions", "results/eval/R211ENVBACKEND/env_backend_summary.json", "intentcap_unsafe_executed", 0),
        _json("E4.qwen.outputs", "模型返回 10 个 outputs", "results/eval/R212ENVLLM/env_llm_backend_summary.json", "parse_success", 10),
        _json("E4.qwen.calls", "8 个形成 checker-submitted calls", "results/eval/R212ENVLLM/env_llm_backend_summary.json", "model_calls", 8),
        _json("E4.qwen.aborts", "2 个是模型直接 abort", "results/eval/R212ENVLLM/env_llm_backend_summary.json", "model_aborts", 2),
        _json("E4.qwen.unsafe_calls", "4 个 unsafe", "results/eval/R212ENVLLM/env_llm_backend_summary.json", "llm_only_unsafe_calls", 4),
        _json("E4.lower.rules", "4 条 deny-by-default monitor rules", "results/eval/R218ACTLOWER/actplane_lowering_summary.json", "lowered_rules", 4),
        _json("E4.lower.mismatches", "0 个 decision mismatches", "results/eval/R218ACTLOWER/actplane_lowering_summary.json", "decision_mismatches", 0),
        _json("E4.aggregate.events", "38 个提交给 checker", "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json", "total_attempts", 38),
        _json("E4.aggregate.authorized", "17 个授权 effects", "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json", "authorized_effects_or_placements", 17),
        _json("E4.aggregate.blocked", "21 个 events", "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json", "blocked_attempts", 21),
        _json("E4.aggregate.unsafe", "0 个 unsafe executions/placements", "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json", "unsafe_intentcap_effects_or_placements", 0),
        _json("E4.aggregate.object_baseline", "12 个 unsafe accepts", "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json", "object_only_unsafe_accepts_observed", 12),
        _json("E4.aggregate.no_prov_baseline", "5 个 unsafe accepts", "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json", "no_provenance_unsafe_accepts_observed", 5),
        _json("Aux.labels.audit", "24/24 个 labels", "results/eval/R207E2A/e2_expert_adjudication_audit_summary.json", "samples_audited", 24),
        _json("Recovery.events", "8 个 workflow counterexample events", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "events", 8),
        _json("Recovery.initial_executes", "2 个合法 calls", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "outcome_counts.correct_execute", 2),
        _json("Recovery.initial_aborts", "5 个正确 aborts", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "outcome_counts.correct_abort", 5),
        _json("Recovery.initial_block", "1 个 unsafe duplicate", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "outcome_counts.gateway_blocked_unsafe", 1),
        _json("Recovery.feedback", "1/1 blocked unsafe", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "recovered_after_gateway_feedback", 1),
        _json("Recovery.final_executes", "最终执行 2 个合法 call", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "final_gateway_allowed", 2),
        _json("Recovery.final_unsafe", "0 个 unsafe executions", "results/eval/R236RECOVRESIDBLINDQWEN36/residual_llm_gateway_summary.json", "final_dangerous_executes", 0),
    ]


def _json(
    claim_id: str,
    paper_number: str,
    source_path: str,
    source_field: str,
    expected: Any,
    *,
    compare: str = "exact",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "paper_number": paper_number,
        "source_path": source_path,
        "source_field": source_field,
        "expected": expected,
        "compare": compare,
        "notes": notes,
    }


def _extract(source_path: Path, check: dict[str, Any]) -> Any:
    data = json.loads(source_path.read_text())
    value: Any = data
    for part in check["source_field"].split("."):
        if isinstance(value, list):
            value = value[int(part)]
        else:
            value = value[part]
    return value


def _compare(actual: Any, expected: Any, compare: str) -> str:
    if compare == "round2":
        return "ok" if round(float(actual), 2) == round(float(expected), 2) else "fail"
    return "ok" if actual == expected else "fail"


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
