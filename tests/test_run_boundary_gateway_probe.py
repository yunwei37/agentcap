from pathlib import Path

import scripts.run_boundary_gateway_probe as probe


def test_boundary_gateway_probe_runs_existing_traces(tmp_path):
    result = probe.run_probe(
        output_dir=tmp_path / "R222BOUNDARY",
        env_trace_path=Path("examples/env_adapter_side_effect_suite.json"),
        workflow_trace_path=Path("examples/residual_workflow_policy_suite.json"),
    )

    summary = result["summary"]

    assert summary["context_attempts"] == 3
    assert summary["context_placed"] == 2
    assert summary["context_blocked"] == 1
    assert summary["delegation_attempts"] == 2
    assert summary["delegation_spawned"] == 1
    assert summary["delegation_blocked"] == 1
    assert summary["unsafe_context_placements"] == 0
    assert summary["unsafe_delegations"] == 0

    output_dir = tmp_path / "R222BOUNDARY"
    assert (output_dir / "boundary_gateway_records.csv").exists()
    assert (output_dir / "boundary_gateway_summary.json").exists()
    assert (output_dir / "input_digests.csv").exists()
