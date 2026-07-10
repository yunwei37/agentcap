import importlib.util
from pathlib import Path


def _load_auditor():
    path = Path(__file__).parents[1] / "scripts" / "audit_mcptox_reconciliation.py"
    spec = importlib.util.spec_from_file_location("audit_mcptox_reconciliation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcptox_audit_reconciles_cases_success_labels_and_events(tmp_path):
    auditor = _load_auditor()
    def_tool_dir = tmp_path / "def_tool"
    def_tool_dir.mkdir()
    (def_tool_dir / "1.py").write_text("# generated poisoned tool\n")
    (def_tool_dir / "2.py").write_text("# generated poisoned tool\n")
    (def_tool_dir / "3.py").write_text("# generated poisoned tool\n")

    response_all = {
        "data_length": 2,
        "attack_scopes": ["Privacy Leakage", "Other"],
        "label_scopes": ["Success", "Failure"],
        "call_behaviors": ["Template-1"],
        "servers": {
            "Email": {
                "tool_names": ["send_email", "read_email"],
                "malicious_instance": [
                    {
                        "metadata": {"security risk": "Privacy Leakage"},
                        "datas": [
                            {
                                "id": 10,
                                "label": {
                                    "model-a": "Success",
                                    "model-b": "Failure",
                                },
                            }
                        ],
                    },
                    {
                        "metadata": {"security risk": "Other"},
                        "datas": [
                            {
                                "id": 11,
                                "label": {
                                    "model-a": "Success",
                                },
                            }
                        ],
                    },
                ],
            }
        },
    }
    pure_tool = [
        {
            "Email_1": {
                "server_name": "Email",
                "tool_name": "poison-a",
            },
            "Email_2": {
                "server_name": "Email",
                "tool_name": "poison-b",
            },
            "Email_3": {
                "server_name": "Email",
                "tool_name": "poison-b",
            },
        }
    ]
    trace = {
        "events": [
            {
                "id": "Email:0:10:model-a:0:send_email",
                "mode": "sink_select",
                "mcptox": {
                    "server": "Email",
                    "instance_index": 0,
                    "data_index": 0,
                    "data_id": 10,
                    "model": "model-a",
                    "security_risk": "Privacy Leakage",
                    "parse_method": "structured",
                },
            },
            {
                "id": "Email:0:10:model-a:1:read_email",
                "mode": "authorize",
                "mcptox": {
                    "server": "Email",
                    "instance_index": 0,
                    "data_index": 0,
                    "data_id": 10,
                    "model": "model-a",
                    "security_risk": "Privacy Leakage",
                    "parse_method": "fallback",
                },
            },
            {
                "id": "Email:1:11:model-a:0:noop",
                "mode": "tool_select",
                "mcptox": {
                    "server": "Email",
                    "instance_index": 1,
                    "data_index": 0,
                    "data_id": 11,
                    "model": "model-a",
                    "security_risk": "Other",
                    "parse_method": "structured",
                },
            },
        ]
    }
    verdicts = [
        {"event_id": "Email:0:10:model-a:0:send_email", "allowed": False},
        {"event_id": "Email:0:10:model-a:1:read_email", "allowed": False},
        {"event_id": "Email:1:11:model-a:0:noop", "allowed": False},
    ]

    audit = auditor.audit_mcptox(
        response_all,
        pure_tool,
        trace,
        verdicts=verdicts,
        def_tool_dir=def_tool_dir,
    )
    summary = audit["summary"]

    assert summary["artifact_counts"]["malicious_instances"] == 2
    assert summary["artifact_counts"]["server_tool_name_refs"] == 2
    assert summary["artifact_counts"]["pure_tool_entries"] == 3
    assert summary["artifact_counts"]["pure_tool_unique_server_tool_pairs"] == 2
    assert summary["artifact_counts"]["def_tool_python_files"] == 3
    assert summary["artifact_counts"]["success_labels"] == 2
    assert summary["trace_counts"]["trace_events"] == 3
    assert summary["trace_counts"]["unique_success_responses_with_events"] == 2
    assert summary["trace_counts"]["events_per_success_response_counts"] == {1: 1, 2: 1}
    assert summary["trace_counts"]["parse_method_counts"] == {"fallback": 1, "structured": 2}
    assert summary["trace_counts"]["checker_denied"] == 3
    assert summary["reporting_guidance"]["paper_benchmark_case_count"] == 2
    assert summary["reporting_guidance"]["intentcap_events_are_replay_events"] == 3
    assert summary["audit_verdict"] == "warn"
    assert audit["server_audit"][0]["intentcap_events"] == 3
    assert audit["risk_audit"][0]["security_risk"] == "Other"
