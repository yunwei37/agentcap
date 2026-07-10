import json
from pathlib import Path

import scripts.analyze_commit_object_minimality as analyzer


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data))
    return path


def test_commit_object_minimality_matrix_reports_counterexamples_and_gap(tmp_path):
    weak = _write_json(
        tmp_path / "weak.json",
        {
            "authority_checker_denied": 10,
            "full_intentcap_unsafe_false_accepts": 0,
            "no_owner_collapsed_context_false_accepts": 8,
            "collapse_edge_false_accepts": {
                "tool->agent": 4,
                "env->agent": 3,
                "env->tool": 2,
                "instruction->agent": 1,
            },
            "workflow_checker_denied": 3,
            "workflow_policy_dsl_false_accepts": 3,
            "workflow_split_lifecycle_false_accepts": 2,
        },
    )
    typed = _write_json(
        tmp_path / "typed.json",
        {
            "workflow_checker_denied": 3,
            "typed_provenance_state_guard_false_accepts": 1,
        },
    )
    multi = _write_json(
        tmp_path / "multi.json",
        {
            "total_attempts": 5,
            "unsafe_intentcap_effects_or_placements": 0,
            "object_only_unsafe_accepts_observed": 2,
            "no_provenance_unsafe_accepts_observed": 1,
        },
    )
    proof = _write_json(
        tmp_path / "proof.json",
        {
            "events": 5,
            "proof_complete_for_verdict": 5,
        },
    )

    result = analyzer.analyze(
        weak_summary=weak,
        typed_summary=typed,
        multi_summary=multi,
        proof_summary=proof,
        run_id="TEST",
    )

    summary = result["summary"]
    assert summary["tested_removals"] == 10
    assert summary["tested_removals_with_counterexamples"] == 10
    assert summary["gap_removal_ids"] == ["audit_binding_removed"]
    assert summary["global_minimality_claim"] is False

    rows = {row["removal_id"]: row for row in result["rows"]}
    assert rows["owner_projection_all"]["false_accepts_or_unsafe_accepts"] == 8
    assert rows["missing_parent_child_handoff_commit"]["false_accepts_or_unsafe_accepts"] == 1
    assert rows["audit_binding_removed"]["evidence_status"] == "gap"
