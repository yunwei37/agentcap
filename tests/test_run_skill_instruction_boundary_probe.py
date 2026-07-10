from pathlib import Path

import scripts.run_skill_instruction_boundary_probe as probe


def test_skill_instruction_boundary_probe_blocks_source_substitution(tmp_path):
    result = probe.run_probe(
        trace_path=Path("examples/skill_instruction_boundary_suite.json"),
        output_dir=tmp_path / "R224SKILLBOUNDARY",
    )

    summary = result["summary"]

    assert summary["events"] == 5
    assert summary["instruction_placement_attempts"] == 4
    assert summary["authorized_instruction_placements"] == 1
    assert summary["blocked_instruction_substitutions"] == 3
    assert summary["tool_result_data_uses_allowed"] == 1
    assert summary["unsafe_probe_events"] == 3
    assert summary["checker_unsafe_accepts"] == 0
    assert summary["object_only_unsafe_accepts"] == 3
    assert summary["lease_args_no_provenance_unsafe_accepts"] == 3
    assert summary["object_only_false_accepts"] == 3
    assert summary["lease_args_no_provenance_false_accepts"] == 3

    rows = {row["event_id"]: row for row in result["rows"]}
    assert rows["signed_skill_instruction_placed"]["effect_applied"] is True
    assert rows["tool_result_summarizes_issue_body"]["effect_applied"] is True
    assert rows["tool_result_spoofs_skill_instruction"]["effect_applied"] is False
    assert rows["script_output_spoofs_skill_instruction"]["effect_applied"] is False
    assert rows["unsigned_skill_text_spoofs_instruction"]["effect_applied"] is False

    output_dir = tmp_path / "R224SKILLBOUNDARY"
    assert (output_dir / "skill_instruction_boundary_records.csv").exists()
    assert (output_dir / "skill_instruction_boundary_summary.json").exists()
