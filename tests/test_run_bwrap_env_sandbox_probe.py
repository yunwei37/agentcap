import importlib.util
import shutil
from pathlib import Path

import pytest


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_bwrap_env_sandbox_probe.py"
    spec = importlib.util.spec_from_file_location("run_bwrap_env_sandbox_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is not installed")
def test_bwrap_env_sandbox_probe_shows_os_containment_and_semantic_gap(tmp_path):
    runner = _load_runner()
    trace_path = Path(__file__).parents[1] / "examples" / "env_adapter_side_effect_suite.json"

    result = runner.run_probe(
        trace_path=trace_path,
        output_dir=tmp_path / "R298BWRAP",
        run_id="R298BWRAP",
    )
    summary = result["summary"]

    assert summary["run_id"] == "R298BWRAP"
    assert summary["bwrap_version"].startswith("bubblewrap ")
    assert summary["forced_network_probe"]["attempted"] is True
    assert summary["forced_network_probe"]["blocked"] is True

    intentcap = summary["backends"]["intentcap_bwrap"]
    assert intentcap["events"] == 10
    assert intentcap["allowed_by_backend"] == 4
    assert intentcap["sandbox_attempts"] == 3
    assert intentcap["sandbox_successes"] == 3
    assert intentcap["unsafe_reference_events_allowed"] == 0
    assert intentcap["unsafe_host_effects"] == 0
    assert intentcap["unsafe_semantic_effects"] == 0

    object_only = summary["backends"]["object_only_bwrap"]
    assert object_only["events"] == 10
    assert object_only["allowed_by_backend"] == 8
    assert object_only["sandbox_attempts"] == 6
    assert object_only["sandbox_successes"] == 6
    assert object_only["unsafe_reference_events_allowed"] == 4
    assert object_only["unsafe_events_contained_by_sandbox"] == 2
    assert object_only["unsafe_host_effects"] == 1
    assert object_only["unsafe_semantic_effects"] == 1

    rows = {
        (row["backend"], row["event_id"]): row
        for row in result["rows"]
    }
    assert rows[("object_only_bwrap", "exec_wrong_output_path")]["contained_by_sandbox"]
    assert rows[("object_only_bwrap", "write_path_traversal")]["contained_by_sandbox"]
    assert rows[("object_only_bwrap", "exec_holder_mismatch")]["unsafe_host_effect"]
    assert rows[("object_only_bwrap", "script_output_promotes_instruction")][
        "unsafe_semantic_effect"
    ]

    output_dir = tmp_path / "R298BWRAP"
    assert (output_dir / "bwrap_env_sandbox_rows.csv").exists()
    assert (output_dir / "bwrap_env_sandbox_summary.json").exists()
