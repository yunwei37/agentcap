import importlib.util
from pathlib import Path


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_env_backend_side_effect_probe.py"
    spec = importlib.util.spec_from_file_location("run_env_backend_side_effect_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_env_backend_blocks_side_effects_before_execution(tmp_path):
    runner = _load_runner()
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "env_adapter_side_effect_suite.json"
    )

    result = runner.run_probe(
        trace_path=trace_path,
        output_dir=tmp_path / "R211",
        run_id="test",
    )
    summary = result["summary"]

    assert summary["events"] == 10
    assert summary["intentcap_executed"] == 4
    assert summary["intentcap_blocked"] == 6
    assert summary["intentcap_unsafe_executed"] == 0
    assert summary["intentcap_secret_unchanged"] is True
    assert summary["intentcap_wrong_output_exists"] is False
    assert summary["intentcap_network_attempts"] == 0

    assert summary["object_only_executed"] == 8
    assert summary["object_only_unsafe_executed"] == 4
    assert summary["object_only_secret_unchanged"] is False
    assert summary["object_only_wrong_output_exists"] is True
    assert summary["object_only_network_attempts"] == 0

    intentcap_out = tmp_path / "R211" / "intentcap_backend" / "workspace" / "out" / "a.xlsx"
    assert intentcap_out.exists()
    assert intentcap_out.read_text().startswith("written_by=write_xlsx_allowed")
