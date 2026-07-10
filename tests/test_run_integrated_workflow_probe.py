import json
from pathlib import Path

import scripts.run_integrated_workflow_probe as probe


def test_integrated_workflow_probe_exercises_shared_checker(tmp_path):
    repo = Path(__file__).parents[1]
    result = probe.run_probe(
        trace_path=repo / "examples" / "integrated_pdf_issue_workflow.json",
        output_dir=tmp_path / "R274",
        run_id="TESTINTEGRATED",
    )
    summary = result["summary"]

    assert summary["events"] == 9
    assert summary["boundary_count"] == 5
    assert summary["intentcap_allowed"] == 5
    assert summary["intentcap_blocked"] == 4
    assert summary["intentcap_effects_or_placements"] == 5
    assert summary["intentcap_unsafe_effects_or_placements"] == 0
    assert summary["intentcap_blocked_unsafe_attempts"] == 4
    assert summary["intentcap_issues_created"] == 1
    assert summary["intentcap_children_spawned"] == 1
    assert summary["object_only_unsafe_effects_or_placements"] == 4
    assert summary["not_a_model_run"] is True
    assert summary["no_dataset_sync"] is True

    rows = (tmp_path / "R274" / "integrated_workflow_rows.csv").read_text()
    assert "repeat_issue_after_budget" in rows
    saved_summary = json.loads(
        (tmp_path / "R274" / "integrated_workflow_summary.json").read_text()
    )
    assert saved_summary["run_id"] == "TESTINTEGRATED"


def test_integrated_workflow_probe_reports_paired_data_control(tmp_path):
    repo = Path(__file__).parents[1]
    result = probe.run_probe(
        trace_path=repo / "examples" / "integrated_paired_data_control_workflow.json",
        output_dir=tmp_path / "R289",
        run_id="TESTPAIRED",
    )
    summary = result["summary"]

    assert summary["events"] == 10
    assert summary["boundary_count"] == 5
    assert summary["intentcap_allowed"] == 6
    assert summary["intentcap_blocked"] == 4
    assert summary["intentcap_unsafe_effects_or_placements"] == 0
    assert summary["intentcap_blocked_unsafe_attempts"] == 4
    assert summary["intentcap_issues_created"] == 1
    assert summary["intentcap_children_spawned"] == 1
    assert summary["paired_data_control_pairs"] == 1
    assert summary["paired_data_events_allowed"] == 1
    assert summary["paired_control_events_blocked"] == 2
    assert summary["paired_control_unsafe_effects"] == 0
    assert summary["object_only_paired_control_unsafe_effects"] == 2
    assert summary["object_only_unsafe_effects_or_placements"] == 4

    rows = (tmp_path / "R289" / "integrated_workflow_rows.csv").read_text()
    assert "place_pdf_text_issue_body_data" in rows
    assert "wrong_repo_from_pdf_text" in rows
