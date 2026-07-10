import importlib.util
from pathlib import Path


def _load_lowerer():
    path = Path(__file__).parents[1] / "scripts" / "lower_env_leases_actplane.py"
    spec = importlib.util.spec_from_file_location("lower_env_leases_actplane", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_actplane_style_lowering_matches_env_checker(tmp_path):
    lowerer = _load_lowerer()
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "env_adapter_side_effect_suite.json"
    )

    result = lowerer.run_lowering(
        trace_path=trace_path,
        output_dir=tmp_path / "R218",
        run_id="test",
    )
    summary = result["summary"]
    policy = result["policy"]

    assert summary["events"] == 10
    assert summary["lowered_rules"] == 4
    assert summary["checker_allowed"] == 4
    assert summary["checker_blocked"] == 6
    assert summary["monitor_allowed"] == 4
    assert summary["monitor_blocked"] == 6
    assert summary["decision_mismatches"] == 0
    assert summary["unsafe_monitor_allowed"] == 0
    assert summary["checker_allowed_monitor_denied"] == 0

    assert policy["default_action"] == "deny"
    assert "script_output" in policy["context_labels"]
    rule_classes = {rule["class"] for rule in policy["rules"]}
    assert rule_classes == {
        "context.use",
        "filesystem.read",
        "filesystem.write",
        "process.exec",
    }

    promotion_row = next(
        row for row in result["rows"] if row["event_id"] == "script_output_promotes_instruction"
    )
    assert promotion_row["checker_allowed"] is False
    assert promotion_row["monitor_allowed"] is False
    assert "control source 'script_output' not allowed" in promotion_row["monitor_reason"]

    written = tmp_path / "R218" / "actplane_lowering_summary.json"
    assert written.exists()
