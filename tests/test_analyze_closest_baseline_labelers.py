import json
from pathlib import Path

import scripts.analyze_closest_baseline_labelers as analyzer


def _write_trace(tmp_path, trace):
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(trace))
    return path


def test_closest_baseline_labelers_separate_explained_and_residual_denials(tmp_path):
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "tool_select": ["safe.tool_choice"],
                }
            },
            "trusted_wrong_scope": {
                "allowed": {
                    "tool_select": ["other.tool_choice"],
                }
            },
            "untrusted_doc": {
                "allowed": {
                    "summarize": ["email.body"],
                }
            },
        },
        "leases": [
            {
                "id": "safe",
                "op": "tool.call",
                "object": "safe_tool",
                "args": {"intentcap_event_id": {"equals": "safe"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
            },
            {
                "id": "malicious_but_matching",
                "op": "tool.call",
                "object": "send_email",
                "args": {"intentcap_event_id": {"equals": "malicious"}},
                "control_may_depend_on": ["untrusted_doc"],
                "data_may_depend_on": ["untrusted_doc"],
            },
            {
                "id": "trusted_wrong_scope",
                "op": "tool.call",
                "object": "repo.push",
                "args": {"intentcap_event_id": {"equals": "wrong-scope"}},
                "control_may_depend_on": ["trusted_wrong_scope"],
                "data_may_depend_on": ["trusted_wrong_scope"],
            },
        ],
        "events": [
            {
                "id": "safe",
                "op": "tool.call",
                "object": "safe_tool",
                "args": {"intentcap_event_id": "safe"},
                "decision": "safe.tool_choice",
                "mode": "tool_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "malicious",
                "op": "tool.call",
                "object": "send_email",
                "args": {"intentcap_event_id": "malicious"},
                "decision": "email.sink",
                "mode": "sink_select",
                "control_provenance": ["untrusted_doc"],
                "data_provenance": ["untrusted_doc"],
            },
            {
                "id": "wrong-scope",
                "op": "tool.call",
                "object": "repo.push",
                "args": {"intentcap_event_id": "wrong-scope"},
                "decision": "repo.push.tool_choice",
                "mode": "tool_select",
                "control_provenance": ["trusted_wrong_scope"],
                "data_provenance": ["trusted_wrong_scope"],
            },
        ],
    }
    trace_path = _write_trace(tmp_path, trace)

    result = analyzer.analyze(run_id="test", trace_paths=(trace_path,))
    summary = result["summary"]

    assert summary["events"] == 3
    assert summary["checker_allowed"] == 1
    assert summary["checker_denied"] == 2
    assert summary["denied_explained_by_any_closest_baseline"] == 1
    assert summary["denied_residual_after_closest_baselines"] == 1
    assert summary["residual_after_closest_baselines_by_mode"] == {"tool_select": 1}

    malicious = next(row for row in result["event_rows"] if row["event_id"] == "malicious")
    assert malicious["explained_by_authgraph_pact_airguard"] is True
    assert malicious["explained_by_ifc_taint"] is True
    assert malicious["policy_dsl_false_accept"] is True
    assert malicious["residual_after_closest_baselines"] is False

    residual = next(row for row in result["event_rows"] if row["event_id"] == "wrong-scope")
    assert residual["authgraph_pact_airguard_accept"] is True
    assert residual["ifc_taint_accept"] is True
    assert residual["policy_dsl_accept"] is True
    assert residual["residual_after_closest_baselines"] is True


def test_closest_baseline_labelers_policy_dsl_explains_arg_mismatch(tmp_path):
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "sink_select": ["email.sink"],
                }
            }
        },
        "leases": [
            {
                "id": "email",
                "op": "tool.call",
                "object": "send_email",
                "args": {"recipient": {"equals": "approved@example.com"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
            }
        ],
        "events": [
            {
                "id": "wrong-recipient",
                "op": "tool.call",
                "object": "send_email",
                "args": {"recipient": "attacker@example.com"},
                "decision": "email.sink",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            }
        ],
    }
    trace_path = _write_trace(tmp_path, trace)

    result = analyzer.analyze(run_id="test", trace_paths=(trace_path,))
    row = result["event_rows"][0]

    assert result["summary"]["checker_denied"] == 1
    assert row["authgraph_pact_airguard_accept"] is True
    assert row["ifc_taint_accept"] is True
    assert row["policy_dsl_accept"] is False
    assert row["explained_by_policy_dsl"] is True
    assert row["residual_after_closest_baselines"] is False


def test_closest_baseline_labelers_loads_list_wrapped_trace_units(tmp_path):
    trace = {
        "labels": {},
        "leases": [],
        "events": [],
    }
    path = tmp_path / "intentcap_traces.json"
    path.write_text(json.dumps([{"domain": "mock", "task_id": "t0", "trace": trace}]))

    result = analyzer.analyze(run_id="test", trace_paths=(path,))

    assert result["summary"]["sources"] == 1
    assert result["source_rows"][0]["source"].endswith(":mock:t0")


def test_residual_suite_exercises_lease_semantics_beyond_closest_labelers():
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "residual_closest_baseline_suite.json"
    )

    result = analyzer.analyze(run_id="test", trace_paths=(trace_path,))
    summary = result["summary"]

    assert summary["events"] == 7
    assert summary["checker_allowed"] == 1
    assert summary["checker_denied"] == 6
    assert summary["denied_residual_after_closest_baselines"] == 6
    assert summary["residual_after_closest_baselines_by_mode"] == {
        "delegate": 1,
        "sink_select": 4,
        "tool_select": 1,
    }
    for row in result["event_rows"]:
        if row["checker_allowed"]:
            continue
        assert row["residual_after_closest_baselines"] is True
        assert row["authgraph_pact_airguard_accept"] is True
        assert row["ifc_taint_accept"] is True
        assert row["policy_dsl_accept"] is True


def test_residual_workflow_suite_lifts_residuals_to_concrete_workflows():
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "residual_workflow_suite.json"
    )

    result = analyzer.analyze(run_id="test", trace_paths=(trace_path,))
    summary = result["summary"]

    assert summary["events"] == 8
    assert summary["checker_allowed"] == 2
    assert summary["checker_denied"] == 6
    assert summary["denied_residual_after_closest_baselines"] == 6
    assert summary["residual_after_closest_baselines_by_mode"] == {
        "authorize": 1,
        "delegate": 1,
        "sink_select": 3,
        "tool_select": 1,
    }
    for row in result["event_rows"]:
        if row["checker_allowed"]:
            continue
        assert row["residual_after_closest_baselines"] is True
        assert row["authgraph_pact_airguard_accept"] is True
        assert row["ifc_taint_accept"] is True
        assert row["policy_dsl_accept"] is True
