import importlib.util
import json
from pathlib import Path


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_env_backend_llm_side_effect_probe.py"
    spec = importlib.util.spec_from_file_location("run_env_backend_llm_side_effect_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _call_everything_runner(command, timeout_seconds):
    del command, timeout_seconds
    return json.dumps({"action": "call", "reason": "test model calls every event"}), "", 0, 0.01


def test_llm_env_backend_routes_model_calls_before_side_effects(tmp_path):
    runner = _load_runner()
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "env_adapter_side_effect_suite.json"
    )

    result = runner.run_probe(
        trace_path=trace_path,
        output_dir=tmp_path / "R212",
        run_id="test",
        runner=_call_everything_runner,
    )
    summary = result["summary"]

    assert summary["events"] == 10
    assert summary["reference_allowed"] == 4
    assert summary["reference_denied"] == 6
    assert summary["parse_success"] == 10
    assert summary["model_calls"] == 10
    assert summary["llm_only_unsafe_calls"] == 6

    assert summary["intentcap_executed"] == 4
    assert summary["intentcap_blocked_model_calls"] == 6
    assert summary["intentcap_unsafe_executed"] == 0
    assert summary["intentcap_secret_unchanged"] is True
    assert summary["intentcap_wrong_output_exists"] is False

    assert summary["object_only_executed"] == 8
    assert summary["object_only_unsafe_executed"] == 4
    assert summary["object_only_secret_unchanged"] is False
    assert summary["object_only_wrong_output_exists"] is True

    rows = result["rows"]
    assert sum(1 for row in rows if row["intentcap_unsafe_executed"]) == 0
    assert sum(1 for row in rows if row["object_only_unsafe_executed"]) == 4
