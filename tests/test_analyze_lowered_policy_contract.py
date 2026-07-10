import importlib.util
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_lowered_policy_contract.py"
    spec = importlib.util.spec_from_file_location("analyze_lowered_policy_contract", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lowered_policy_contract_audits_full_policy_and_weakened_variants(tmp_path):
    analyzer = _load_analyzer()
    result = analyzer.analyze(
        output_dir=tmp_path / "R296LOWERINGCONTRACT",
        inputs=analyzer.DEFAULT_INPUTS,
        run_id="R296LOWERINGCONTRACT",
    )
    summary = result["summary"]

    assert summary["run_id"] == "R296LOWERINGCONTRACT"
    assert summary["challenge_sequences"] == 7
    assert summary["challenge_events"] == 8
    assert summary["variants"] == 6
    assert summary["full_policy_unsafe_accepts"] == 0
    assert summary["full_policy_decision_mismatches"] == 0
    assert summary["weakened_variant_unsafe_accepts"] == 12
    assert summary["unsafe_accepts_by_variant"] == {
        "default_allow_unmatched": 7,
        "full_policy": 0,
        "no_argument_constraints": 2,
        "no_budget_state": 1,
        "no_holder_binding": 1,
        "no_provenance_influence": 1,
    }

    contract = summary["contract"]
    assert contract["default_action"] == "deny"
    assert contract["rules"] == 4
    assert contract["rule_classes"] == [
        "context.use",
        "filesystem.read",
        "filesystem.write",
        "process.exec",
    ]
    assert contract["rules_with_holder_binding"] == 3
    assert contract["rules_with_argument_constraints"] == 4
    assert contract["rules_with_control_policy"] == 4
    assert contract["rules_with_data_policy"] == 4
    assert contract["stateful_budget_rules"] == 1

    variant_rows = {row["variant"]: row for row in result["variant_rows"]}
    assert variant_rows["full_policy"]["decision_mismatches"] == 0
    assert variant_rows["no_budget_state"]["unsafe_accepts"] == 1
    assert variant_rows["no_provenance_influence"]["unsafe_accepts"] == 1

    rows = {
        (row["variant"], row["challenge_id"], row["event_id"]): row
        for row in result["rows"]
    }
    assert rows[
        ("no_holder_binding", "holder_binding", "exec_holder_mismatch")
    ]["unsafe_accept"]
    assert rows[
        ("no_argument_constraints", "argument_output_constraint", "exec_wrong_output_path")
    ]["unsafe_accept"]
    assert rows[
        ("no_provenance_influence", "control_influence", "script_output_promotes_instruction")
    ]["unsafe_accept"]
    assert rows[
        ("no_budget_state", "budget_consume", "exec_pdf_skill_allowed_duplicate")
    ]["unsafe_accept"]
    assert rows[
        ("default_allow_unmatched", "default_deny_network", "net_connect_attacker")
    ]["unsafe_accept"]

    output_dir = tmp_path / "R296LOWERINGCONTRACT"
    assert (output_dir / "lowered_policy_contract_rows.csv").exists()
    assert (output_dir / "lowered_policy_contract_summary.json").exists()
    assert (output_dir / "lowered_policy_variant_summary.csv").exists()
