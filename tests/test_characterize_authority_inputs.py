import json
from pathlib import Path

import scripts.characterize_authority_inputs as analyzer


def test_authority_characterization_detects_four_classes_and_substitution(tmp_path):
    trace = {
        "labels": {
            "trusted_user_intent": {
                "origin": "trusted_user_intent",
                "allowed": {
                    "sink_select": ["github.repo"],
                    "tool_select": ["local.exec"],
                },
            },
            "signed_pdf_skill_manifest": {
                "origin": "signed_skill_manifest",
                "allowed": {"tool_select": ["local.exec"]},
            },
            "trusted_tool_metadata": {
                "origin": "mcp_tool_metadata",
                "allowed": {"tool_select": ["local.exec"]},
            },
            "script_output": {
                "origin": "script_output",
                "allowed": {"parameterize": ["xlsx.cells"]},
            },
        },
        "leases": [
            {
                "id": "exec",
                "op": "exec.run",
                "object": "/skills/pdf/extract.py",
                "args": {"input": {"equals": "a.pdf"}},
                "control_may_depend_on": [
                    "trusted_user_intent",
                    "signed_pdf_skill_manifest",
                    "trusted_tool_metadata",
                ],
                "data_may_depend_on": ["script_output"],
            },
            {
                "id": "bad_policy_shape",
                "op": "policy.update",
                "object": "agent.policy",
                "args": {"scope": {"equals": "github"}},
                "control_may_depend_on": ["trusted_tool_metadata"],
                "data_may_depend_on": ["trusted_tool_metadata"],
            },
        ],
        "events": [
            {
                "id": "exec_ok",
                "op": "exec.run",
                "object": "/skills/pdf/extract.py",
                "args": {"input": "a.pdf"},
                "decision": "local.exec",
                "mode": "tool_select",
                "control_provenance": [
                    "trusted_user_intent",
                    "signed_pdf_skill_manifest",
                    "trusted_tool_metadata",
                ],
                "data_provenance": ["script_output"],
            },
            {
                "id": "tool_metadata_policy_update",
                "op": "policy.update",
                "object": "agent.policy",
                "args": {"scope": "github"},
                "decision": "agent.policy",
                "mode": "policy_update",
                "control_provenance": ["trusted_tool_metadata"],
                "data_provenance": ["trusted_tool_metadata"],
            },
        ],
    }
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace))

    result = analyzer.analyze(run_id="test", trace_paths=(trace_path,), runtime_paths=())
    summary = result["summary"]

    assert summary["events"] == 2
    assert summary["events_requiring_multiple_issuer_classes"] == 1
    assert summary["events_requiring_env"] == 1
    assert summary["denied_events_with_class_substitution_attempt"] == 1
    assert summary["collapse_rows"] == [
        {
            "substitution_edge": "tool->agent",
            "events": 1,
            "example_event_ids": "tool_metadata_policy_update",
        }
    ]
    assert summary["events_requiring_tool_schema_or_interface"] == 1
    assert summary["events_requiring_env_runtime_evidence"] == 1
    assert summary["events_with_observed_multi_provenance_classes"] == 1

    decision_rows = {row["mode"]: row for row in result["decision_rows"]}
    assert decision_rows["tool_select"]["events_requiring_tool"] == 1
    assert decision_rows["tool_select"]["events_requiring_env"] == 1
    assert decision_rows["policy_update"]["substitution_edges"] == "tool->agent:1"

    class_counts = {row["class_name"]: row for row in result["class_rows"]}
    assert class_counts["agent"]["required_events"] == 2
    assert class_counts["instruction"]["required_events"] == 1
    assert class_counts["tool"]["control_source_events"] == 2
    assert class_counts["env"]["data_source_events"] == 1


def test_authority_characterization_summarizes_runtime_binding(tmp_path):
    summary_path = tmp_path / "task_gateway_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "reference_actions": 12,
                "model_calls": 5,
                "executed_calls": 4,
                "compiler_runtime_binding_attempts": 3,
                "compiler_runtime_binding_successes": 2,
                "compiler_runtime_binding_missing_evidence": 1,
                "compiler_runtime_binding_missing_value_proof": 0,
                "stepwise_runtime_evidence_lease_hint_steps": 7,
                "tool_oracle_pass_tasks": 1,
                "tool_oracle_pass_rate": 0.25,
            }
        )
    )

    result = analyzer.analyze(run_id="test", trace_paths=(), runtime_paths=(summary_path,))

    assert result["summary"]["runtime_binding_attempts"] == 3
    assert result["summary"]["runtime_binding_successes"] == 2
    assert result["summary"]["runtime_binding_success_rate"] == 2 / 3
    assert result["summary"]["runtime_evidence_hint_steps"] == 7
    assert result["runtime_rows"][0]["runtime_binding_missing_evidence"] == 1
