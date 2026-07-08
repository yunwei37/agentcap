import importlib.util
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_e3_benchmark_residual_lift.py"
    spec = importlib.util.spec_from_file_location("build_e3_benchmark_residual_lift", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_benchmark_residual_lift_uses_existing_mcptox_artifacts(tmp_path):
    builder = _load_builder()
    root = Path(__file__).parents[1]
    result = builder.build_residual_lift(
        trace_path=root / "results" / "mcptox" / "R007" / "intentcap_trace.json",
        response_all_path=root / "benchmarks" / "mcptox" / "response_all.json",
        output_dir=tmp_path / "R219",
        run_id="test",
        case_limit=6,
    )
    summary = result["summary"]
    rows = result["rows"]

    assert summary["cases"] == 6
    assert summary["events"] == 18
    assert summary["checker_allowed"] == 6
    assert summary["checker_blocked"] == 12
    assert summary["residual_after_closest_baselines"] == 12
    assert summary["residual_after_closest_by_scenario"] == {
        "tool_metadata_updates_policy": 6,
        "tool_metadata_widens_approval": 6,
    }
    assert summary["observed_authentic_tool_objects"] >= 6

    schema_rows = [row for row in rows if row["scenario"] == "schema_use"]
    assert len(schema_rows) == 6
    assert all(row["checker_allowed"] is True for row in schema_rows)

    residual_rows = [row for row in rows if row["residual_after_closest_baselines"]]
    assert len(residual_rows) == 12
    assert all(row["checker_allowed"] is False for row in residual_rows)
    assert all(row["closest_all_accept"] is True for row in residual_rows)

    written = tmp_path / "R219" / "benchmark_residual_lift_summary.json"
    assert written.exists()
