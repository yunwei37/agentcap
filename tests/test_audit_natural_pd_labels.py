import importlib.util
import json
import sys
from pathlib import Path


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_natural_pd_label_audit_accepts_packet(tmp_path):
    repo = Path(__file__).parents[1]
    builder = _load_module(
        "build_natural_pd_label_packet_for_audit_test",
        repo / "scripts" / "build_natural_pd_labeling_packet.py",
    )
    auditor = _load_module(
        "audit_natural_pd_labels_for_test",
        repo / "scripts" / "audit_natural_pd_labels.py",
    )
    event_csv, trace_path = _write_packet_inputs(tmp_path)
    packet_dir = tmp_path / "packet"
    builder.build_packet(
        run_id="T335NATPD",
        event_csv=event_csv,
        output_dir=packet_dir,
        target_size=2,
        per_edge=1,
        per_mode_verdict=1,
        min_per_source=1,
        env_quota=1,
        sample_id_prefix="t335",
        require_existing_source=True,
    )

    result = auditor.audit(
        run_id="T336AUDIT",
        packet_dir=packet_dir,
        output_dir=tmp_path / "audit",
        min_samples=2,
        min_protected=1,
        min_multiple=1,
        min_env=1,
        min_substitution=1,
        require_existing_source=True,
    )

    summary = result["summary"]
    assert summary["audit_status"] == "ok"
    assert summary["samples_audited"] == 2
    assert summary["failed_checks_total"] == 0
    assert summary["source_path_counts"] == {str(trace_path): 2}


def test_natural_pd_label_audit_flags_wrong_owner_field(tmp_path):
    repo = Path(__file__).parents[1]
    builder = _load_module(
        "build_natural_pd_label_packet_for_bad_audit_test",
        repo / "scripts" / "build_natural_pd_labeling_packet.py",
    )
    auditor = _load_module(
        "audit_natural_pd_labels_for_bad_test",
        repo / "scripts" / "audit_natural_pd_labels.py",
    )
    event_csv, _trace_path = _write_packet_inputs(tmp_path)
    packet_dir = tmp_path / "packet"
    builder.build_packet(
        run_id="T335NATPD",
        event_csv=event_csv,
        output_dir=packet_dir,
        target_size=1,
        per_edge=1,
        per_mode_verdict=1,
        min_per_source=1,
        env_quota=0,
        sample_id_prefix="t335",
        require_existing_source=True,
    )
    labels_path = packet_dir / "author_labels.codex.jsonl"
    label = json.loads(labels_path.read_text().splitlines()[0])
    label["owner_fields"][0]["field"] = "wrong_field"
    labels_path.write_text(json.dumps(label, sort_keys=True) + "\n")

    result = auditor.audit(
        run_id="T336AUDIT",
        packet_dir=packet_dir,
        output_dir=tmp_path / "audit",
        min_samples=1,
        min_protected=1,
        min_multiple=1,
        min_env=0,
        min_substitution=1,
        require_existing_source=True,
    )

    assert result["summary"]["audit_status"] == "failed"
    assert result["summary"]["failed_samples_count"] == 1
    assert "owner_field_matches_protocol" in result["report_rows"][0]["failed_checks"]


def _write_packet_inputs(tmp_path):
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "intent": {"goal": "extract_tables", "sink": "org/repo-x"},
                "labels": {
                    "trusted_user_intent": {"origin": "trusted_user_intent", "allowed": {}},
                    "trusted_tool_metadata": {"origin": "mcp_tool_metadata", "allowed": {}},
                    "script_output": {"origin": "script_output", "allowed": {}},
                },
                "events": [
                    {
                        "id": "call_bad",
                        "op": "mcp.call",
                        "object": "github.create_issue",
                        "args": {"repo": "attacker/repo"},
                        "mode": "sink_select",
                        "decision": "github.repo",
                        "control_provenance": ["script_output"],
                        "data_provenance": ["script_output"],
                    },
                    {
                        "id": "ctx_env",
                        "op": "ctx.use",
                        "object": "script.output",
                        "args": {"value": "table cell"},
                        "mode": "parameterize",
                        "decision": "xlsx.cells",
                        "control_provenance": ["trusted_user_intent"],
                        "data_provenance": ["script_output"],
                    },
                ],
            }
        )
    )
    event_csv = tmp_path / "events.csv"
    event_csv.write_text(
        "\n".join(
            [
                "source,source_path,event_id,op,object,mode,decision,checker_allowed,required_classes,control_classes,data_classes,requires_env,has_class_substitution_attempt,substitution_edges,requirement_basis",
                f"tmp:trace:0,{trace_path},call_bad,mcp.call,github.create_issue,sink_select,github.repo,False,agent|tool,env,env,False,True,env->agent|env->tool,agent_authority|tool_schema_or_interface",
                f"tmp:trace:0,{trace_path},ctx_env,ctx.use,script.output,parameterize,xlsx.cells,True,env,agent,env,True,False,,env_runtime_evidence",
                "",
            ]
        )
    )
    return event_csv, trace_path
