import csv
import importlib.util
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_e3_typed_provenance_baseline.py"
    spec = importlib.util.spec_from_file_location("analyze_e3_typed_provenance_baseline", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_typed_provenance_baseline_keeps_strong_predicates_but_misses_attenuation(tmp_path):
    analyzer = _load_analyzer()
    workflow_baseline = tmp_path / "workflow.csv"
    _write_csv(
        workflow_baseline,
        ["event_id", "op", "object", "mode", "decision", "checker_allowed", "checker_reason"],
        [
            {
                "event_id": "ok",
                "op": "mcp.call",
                "object": "github.create_issue",
                "mode": "sink_select",
                "decision": "github.repo",
                "checker_allowed": "true",
                "checker_reason": "allowed",
            },
            {
                "event_id": "early",
                "op": "mcp.call",
                "object": "github.create_issue",
                "mode": "sink_select",
                "decision": "github.repo",
                "checker_allowed": "false",
                "checker_reason": "post_review_single_issue: temporal prerequisites not satisfied: ['review_complete']",
            },
            {
                "event_id": "delegation",
                "op": "subagent.spawn",
                "object": "calendar_summary_subagent",
                "mode": "delegate",
                "decision": "calendar_subagent.capabilities",
                "checker_allowed": "false",
                "checker_reason": "calendar_summary_subagent_only: delegated capability exceeds lease attenuation: {'op': 'mcp.call'}",
            },
            {
                "event_id": "missing_approval",
                "op": "approve.request",
                "object": "github.issue_scope_approval",
                "mode": "authorize",
                "decision": "github.issue_scope",
                "checker_allowed": "false",
                "checker_reason": "fresh_issue_scope_approval: missing required approval proof: ['fresh_issue_approval']",
            },
        ],
    )

    result = analyzer.analyze(workflow_baseline=workflow_baseline, run_id="unit")
    summary = result["summary"]

    assert summary["workflow_events"] == 4
    assert summary["workflow_checker_denied"] == 3
    assert summary["typed_provenance_state_guard_false_accepts"] == 1
    assert summary["typed_provenance_state_guard_blocks"] == 2
    assert summary["typed_false_accept_classes"] == {
        "delegation_attenuation_without_parent_lease_commit": 1
    }
    assert summary["typed_block_classes"] == {
        "approval_mint_state": 1,
        "temporal_state": 1,
    }

    rows = {row["event_id"]: row for row in result["event_rows"]}
    assert rows["delegation"]["typed_provenance_state_guard_false_accept"] is True
    assert rows["early"]["typed_provenance_state_guard_false_accept"] is False
