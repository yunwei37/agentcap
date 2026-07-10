import importlib.util
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_adapter_proof_completeness.py"
    spec = importlib.util.spec_from_file_location("analyze_adapter_proof_completeness", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_adapter_proof_completeness_audits_existing_e4_records(tmp_path):
    analyzer = _load_analyzer()
    result = analyzer.analyze(
        output_dir=tmp_path / "R240ADAPTERPROOF",
        inputs=analyzer.DEFAULT_INPUTS,
        run_id="R240ADAPTERPROOF",
    )
    summary = result["summary"]

    assert summary["run_id"] == "R240ADAPTERPROOF"
    assert summary["events"] == 38
    assert summary["allowed"] == 17
    assert summary["blocked"] == 21
    assert summary["unsafe_effects_or_placements"] == 0
    assert summary["proof_complete_for_verdict"] == 38
    assert summary["incomplete_or_unclassified_denials"] == 0
    assert summary["pre_effect_or_pre_handoff_blockpoints"] == 38
    assert summary["denial_classes"]["allowed"] == 17
    assert summary["denial_classes"]["control_provenance_or_influence"] == 6
    assert summary["denial_classes"]["delegation_attenuation"] == 1
    assert summary["denial_classes"]["holder_scope"] == 3
    assert summary["denial_classes"]["operation_object_argument_or_no_lease"] == 11
    assert summary["proof_obligation_counts"]["control_provenance"] == 38
    assert summary["proof_obligation_counts"]["data_provenance"] == 38
    assert summary["proof_obligation_counts"]["operation_object_argument_contract"] == 38

    rows = {(row["boundary"], row["event_id"]): row for row in result["rows"]}
    assert rows[("delegation_handoff", "calendar_subagent_overdelegates_email")][
        "denial_class"
    ] == "delegation_attenuation"
    assert rows[("skill_instruction_placement", "tool_result_spoofs_skill_instruction")][
        "denial_class"
    ] == "control_provenance_or_influence"
    assert rows[("os_monitor_style_lowering", "exec_holder_mismatch")][
        "denial_class"
    ] == "holder_scope"

    output_dir = tmp_path / "R240ADAPTERPROOF"
    assert (output_dir / "adapter_proof_completeness.csv").exists()
    assert (output_dir / "adapter_proof_completeness_summary.json").exists()
    assert (output_dir / "denial_classes.csv").exists()
