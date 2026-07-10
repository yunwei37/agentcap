import json

import pytest

import scripts.analyze_context_owner_evidence_matrix as analyzer


def test_context_owner_evidence_matrix_consolidates_saved_artifacts(tmp_path):
    result = analyzer.analyze(
        output_dir=tmp_path / "R307OWNERMATRIX",
        inputs=analyzer.DEFAULT_INPUTS,
        run_id="T307OWNERMATRIX",
    )

    summary = result["summary"]
    assert summary["run_id"] == "T307OWNERMATRIX"
    assert summary["owner_classes"] == ["agent", "instruction", "tool", "env"]
    assert summary["owner_class_count"] == 4
    assert summary["pairwise_merges"] == 6
    assert summary["pairwise_merges_with_counterexamples"] == 6
    assert summary["all_pairwise_merges_have_counterexample"] is True
    assert summary["tested_removals"] == 10
    assert summary["tested_removals_with_counterexamples"] == 10
    assert summary["audit_binding_gap_removals"] == 1
    assert summary["global_taxonomy_claim"] is False
    assert summary["global_minimality_claim"] is False
    assert summary["no_owner_false_accepts"] == 3593
    assert summary["no_owner_denied_total"] == 3823
    assert summary["prompt_builder_owner_class_count"] == 4
    assert summary["prompt_builder_unsafe_authority_placements"] == 0
    assert summary["local_boundary_rows"] == 8
    assert summary["local_boundary_attempts"] == 58
    assert summary["local_boundary_unsafe_effects_or_placements"] == 0
    assert summary["local_boundary_object_only_unsafe_accepts"] == 20
    assert summary["recovery_tasks"] == 8
    assert summary["recovery_surfaces_covered"] == 6
    assert summary["recovery_owner_classes_covered"] == ["agent", "env", "instruction", "tool"]
    assert summary["recovery_initial_blocks"] == 8
    assert summary["recovery_object_only_would_allow"] == 8
    assert summary["recovery_authorized_alternatives"] == 8
    assert summary["recovery_dangerous_executions"] == 0
    assert summary["no_dataset_sync"] is True
    assert summary["not_a_model_run"] is True
    assert summary["not_a_new_benchmark"] is True

    owner_rows = {row["owner_class"]: row for row in result["owner_rows"]}
    assert set(owner_rows) == {"agent", "instruction", "tool", "env"}
    assert "authorized sink" in owner_rows["agent"]["representative_fields"]
    assert "workflow scope" in owner_rows["instruction"]["representative_fields"]
    assert "schema" in owner_rows["tool"]["representative_fields"]
    assert "tool result" in owner_rows["env"]["representative_fields"]

    pair_rows = {row["merged_pair"]: row for row in result["pair_rows"]}
    assert set(pair_rows) == {
        "agent+instruction",
        "agent+tool",
        "agent+env",
        "instruction+tool",
        "instruction+env",
        "tool+env",
    }
    assert all(row["covered_by_counterexample"] for row in pair_rows.values())

    output_dir = tmp_path / "R307OWNERMATRIX"
    assert (output_dir / "context_owner_matrix.csv").exists()
    assert (output_dir / "owner_merge_counterexamples.csv").exists()
    assert (output_dir / "context_owner_matrix_summary.json").exists()
    persisted = json.loads((output_dir / "context_owner_matrix_summary.json").read_text())
    assert persisted["run_id"] == "T307OWNERMATRIX"


def test_context_owner_evidence_matrix_rejects_incomplete_owner_coverage(tmp_path):
    bad_recovery = tmp_path / "bad_recovery.json"
    data = json.loads(
        analyzer.DEFAULT_INPUTS["recovery"].read_text()
    )
    data["owner_classes_covered"] = ["agent", "instruction", "tool"]
    bad_recovery.write_text(json.dumps(data))

    inputs = dict(analyzer.DEFAULT_INPUTS)
    inputs["recovery"] = bad_recovery

    with pytest.raises(ValueError, match="recovery.owner_classes_covered"):
        analyzer.analyze(
            output_dir=tmp_path / "R307OWNERMATRIX_BAD",
            inputs=inputs,
            run_id="T307OWNERMATRIX",
        )
