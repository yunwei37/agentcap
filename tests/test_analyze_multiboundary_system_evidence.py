from pathlib import Path

import scripts.analyze_multiboundary_system_evidence as analyzer


def test_multiboundary_system_evidence_consolidates_existing_results(tmp_path):
    result = analyzer.analyze(
        output_dir=tmp_path / "R225MULTIBOUNDARY",
        inputs=analyzer.DEFAULT_INPUTS,
    )

    summary = result["summary"]

    assert summary["run_id"] == "R225MULTIBOUNDARY"
    assert summary["system_boundary_rows"] == 6
    assert summary["total_attempts"] == 38
    assert summary["authorized_effects_or_placements"] == 17
    assert summary["blocked_attempts"] == 21
    assert summary["unsafe_intentcap_effects_or_placements"] == 0
    assert summary["object_only_unsafe_accepts_observed"] == 12
    assert summary["no_provenance_unsafe_accepts_observed"] == 5
    assert summary["monitor_mismatches"] == 0
    assert summary["covered_boundaries"] == [
        "env_local_side_effects",
        "env_llm_model_loop",
        "actplane_style_env_lowering",
        "context_placement",
        "delegation_handoff",
        "skill_instruction_placement",
    ]

    rows = {row["row_id"]: row for row in result["rows"]}
    assert rows["skill_instruction_placement"]["blocked_attempts"] == 3
    assert rows["actplane_style_env_lowering"]["monitor_mismatches"] == 0

    output_dir = tmp_path / "R225MULTIBOUNDARY"
    assert (output_dir / "multiboundary_system_evidence.csv").exists()
    assert (output_dir / "multiboundary_system_summary.json").exists()
