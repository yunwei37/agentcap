import csv
import json
import subprocess
import sys
from pathlib import Path


def test_paper_evidence_audit_matches_saved_results(tmp_path):
    repo = Path(__file__).parents[1]
    output_dir = tmp_path / "R237PAPERAUDIT"
    script = repo / "scripts" / "audit_paper_evidence_numbers.py"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-id",
            "T237PAPERAUDIT",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads((output_dir / "paper_evidence_audit_summary.json").read_text())
    assert summary["run_id"] == "T237PAPERAUDIT"
    assert summary["audit_status"] == "ok"
    assert summary["checks_total"] >= 50
    assert summary["checks_failed"] == 0
    assert summary["no_dataset_sync"] is True
    assert summary["not_a_model_run"] is True
    assert summary["not_a_new_experiment"] is True

    rows = list(csv.DictReader((output_dir / "paper_evidence_audit.csv").open()))
    assert len(rows) == summary["checks_total"]
    assert {row["status"] for row in rows} == {"ok"}
    claim_ids = {row["claim_id"] for row in rows}
    assert "E4.aggregate.rows" in claim_ids
    assert "E4.aggregate.events" in claim_ids
    assert "E4.aggregate.authorized" in claim_ids
    assert "E4.aggregate.blocked" in claim_ids
    assert "E4.aggregate.object_baseline" in claim_ids
    assert "E4.scope.not_production" in claim_ids
    assert "E4.scope.not_benchmark_utility" in claim_ids
    assert "E4.scope.r331_extended" in claim_ids
    assert "E4.proof_ext.events" in claim_ids
    assert "E4.proof_ext.complete" in claim_ids
    assert "E4.lower_contract.challenge_events" in claim_ids
    assert "E4.lower_contract.full_unsafe" in claim_ids
    assert "E4.lower_contract.weakened_unsafe" in claim_ids
    assert "E4.lower_contract.default_allow" in claim_ids
    assert "E4.lower_contract.no_arg" in claim_ids
    assert "E4.lower_contract.no_budget" in claim_ids
    assert "E4.bwrap.intentcap_allowed" in claim_ids
    assert "E4.bwrap.intentcap_unsafe_host" in claim_ids
    assert "E4.bwrap.object_contained" in claim_ids
    assert "E4.bwrap.object_unsafe_host" in claim_ids
    assert "E4.bwrap.network_blocked" in claim_ids
    assert "E4.mcp.intentcap_executed" in claim_ids
    assert "E4.mcp.intentcap_unsafe" in claim_ids
    assert "E4.mcp.object_unsafe" in claim_ids
    assert "E4.mcp.server_unsafe" in claim_ids
    assert "E4.proof.events" in claim_ids
    assert "E4.proof.complete" in claim_ids
    assert any(row["claim_id"] == "Recovery.feedback" for row in rows)
    assert any(row["claim_id"] == "Recovery.R266.recovered" for row in rows)
    assert any(row["claim_id"] == "Recovery.R267.feedback_mode" for row in rows)
    assert any(row["claim_id"] == "Recovery.R268.feedback_mode" for row in rows)
    assert any(row["claim_id"] == "CommitMin.tested_removals" for row in rows)
    assert any(row["claim_id"] == "CommitMin.gaps" for row in rows)
    assert any(row["claim_id"] == "E3.merge_coverage.pairs" for row in rows)
    assert any(
        row["claim_id"] == "E3.merge_coverage.instruction_tool_false_accepts"
        for row in rows
    )
    assert any(row["claim_id"] == "E3.merge_coverage.full_checker_unsafe" for row in rows)
    assert any(row["claim_id"] == "E3.integrated.events" for row in rows)
    assert any(row["claim_id"] == "E3.integrated.object_unsafe" for row in rows)
    assert any(row["claim_id"] == "E3.integrated.latency_max" for row in rows)
    assert any(row["claim_id"] == "E3.paired.events" for row in rows)
    assert any(row["claim_id"] == "E3.paired.object_paired_unsafe" for row in rows)
    assert any(row["claim_id"] == "OwnerMatrix.owner_classes" for row in rows)
    assert any(row["claim_id"] == "OwnerMatrix.pairwise_merges" for row in rows)
    assert any(row["claim_id"] == "OwnerMatrix.tested_removals" for row in rows)
    assert any(row["claim_id"] == "OwnerMatrix.recovery_surfaces" for row in rows)
    assert any(row["claim_id"] == "OwnerMatrix.no_global_taxonomy" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.denial_rows" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.matched_feedback_tasks" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.expanded_feedback_tasks" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.expanded_feedback_allowed" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.recovered_benchmark" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.handwritten" for row in rows)
    assert any(row["claim_id"] == "BenchRecovery.gate_status" for row in rows)
    assert any(row["claim_id"] == "OracleFeedbackShard.tasks" for row in rows)
    assert any(row["claim_id"] == "OracleFeedbackShard.gateway_blocks" for row in rows)
    assert any(row["claim_id"] == "OracleFeedbackShard.feedback_tasks" for row in rows)
    assert any(row["claim_id"] == "OracleFeedbackShard.tool_oracle" for row in rows)
    assert any(row["claim_id"] == "RetailCompiler.tasks" for row in rows)
    assert any(row["claim_id"] == "RetailCompiler.exact_args" for row in rows)
    assert any(row["claim_id"] == "RetailCompiler.runtime_needed" for row in rows)
    assert any(row["claim_id"] == "CompilerFeedback.gateway_blocks" for row in rows)
    assert any(row["claim_id"] == "CompilerFeedback.feedback_tasks" for row in rows)
    assert any(row["claim_id"] == "CompilerFeedback.feedback_allowed" for row in rows)
    assert any(row["claim_id"] == "CompilerFeedback.tool_oracle" for row in rows)
    assert any(row["claim_id"] == "ProtocolGap.step_outputs" for row in rows)
    assert any(row["claim_id"] == "ProtocolGap.think_outputs" for row in rows)
    assert any(row["claim_id"] == "ProtocolGap.truncated_outputs" for row in rows)
    assert any(row["claim_id"] == "ProtocolGap.parsed_calls" for row in rows)
    assert any(row["claim_id"] == "ProtocolGap.truncated_tasks" for row in rows)

    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))
    assert any(row["path"] == "docs/autopaper/intentcap-paper-zh.tex" for row in digests)
    assert (output_dir / "command.txt").exists()
