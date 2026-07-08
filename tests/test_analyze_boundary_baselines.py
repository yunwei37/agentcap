from pathlib import Path

import scripts.analyze_boundary_baselines as baselines


def test_boundary_baselines_false_accept_unsafe_probes(tmp_path):
    result = baselines.analyze(
        output_dir=tmp_path / "R223BOUNDARYBASE",
        env_trace_path=Path("examples/env_adapter_side_effect_suite.json"),
        workflow_trace_path=Path("examples/residual_workflow_policy_suite.json"),
    )

    summary = result["summary"]

    assert summary["events"] == 5
    assert summary["unsafe_probe_events"] == 2
    assert summary["checker_unsafe_accepts"] == 0
    assert summary["object_only_unsafe_accepts"] == 2
    assert summary["lease_args_no_provenance_unsafe_accepts"] == 2
    assert summary["object_only_false_accepts"] == 2
    assert summary["lease_args_no_provenance_false_accepts"] == 2

    rows_by_id = {row["event_id"]: row for row in result["rows"]}
    assert rows_by_id["script_output_promotes_instruction"]["object_only_false_accept"] is True
    assert rows_by_id["calendar_subagent_overdelegates_email"][
        "lease_args_no_provenance_false_accept"
    ] is True

    output_dir = tmp_path / "R223BOUNDARYBASE"
    assert (output_dir / "boundary_baseline_decisions.csv").exists()
    assert (output_dir / "boundary_baseline_summary.json").exists()
