import csv
import json
from pathlib import Path

import scripts.build_natural_pd_labeling_packet as packet


def test_build_natural_pd_packet_samples_edges_and_env(tmp_path):
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "intent": {"goal": "extract_tables", "sink": "org/repo-x"},
                "labels": {
                    "trusted_user_intent": {"origin": "trusted_user_intent", "allowed": {}},
                    "trusted_tool_metadata": {"origin": "mcp_tool_metadata", "allowed": {}},
                    "script_output": {"origin": "script_output", "allowed": {}},
                    "signed_skill": {"origin": "signed_skill_manifest", "allowed": {}},
                },
                "events": [
                    {
                        "id": "call_ok",
                        "op": "mcp.call",
                        "object": "github.create_issue",
                        "args": {"repo": "org/repo-x"},
                        "mode": "tool_select",
                        "decision": "github.create_issue",
                        "control_provenance": ["trusted_user_intent", "trusted_tool_metadata"],
                        "data_provenance": ["script_output"],
                    },
                    {
                        "id": "policy_bad",
                        "op": "policy.update",
                        "object": "agent.policy",
                        "args": {"scope": "github"},
                        "mode": "policy_update",
                        "decision": "agent.policy",
                        "control_provenance": ["trusted_tool_metadata"],
                        "data_provenance": ["trusted_tool_metadata"],
                    },
                    {
                        "id": "exec_env",
                        "op": "exec.run",
                        "object": "/skills/pdf/extract.py",
                        "args": {"input": "a.pdf"},
                        "mode": "tool_select",
                        "decision": "local.exec",
                        "control_provenance": ["trusted_user_intent", "signed_skill"],
                        "data_provenance": ["script_output"],
                    },
                ],
            }
        )
    )
    event_csv = tmp_path / "events.csv"
    with event_csv.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source",
                "source_path",
                "event_id",
                "op",
                "object",
                "mode",
                "decision",
                "checker_allowed",
                "required_classes",
                "control_classes",
                "data_classes",
                "requires_env",
                "has_class_substitution_attempt",
                "substitution_edges",
                "requirement_basis",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "source": f"{trace_path.parent.name}:{trace_path.stem}:0",
                "source_path": str(trace_path),
                "event_id": "call_ok",
                "op": "mcp.call",
                "object": "github.create_issue",
                "mode": "tool_select",
                "decision": "github.create_issue",
                "checker_allowed": "True",
                "required_classes": "agent|tool",
                "control_classes": "agent|tool",
                "data_classes": "env",
                "requires_env": "False",
                "has_class_substitution_attempt": "False",
                "substitution_edges": "",
                "requirement_basis": "agent_authority|tool_schema_or_interface",
            }
        )
        writer.writerow(
            {
                "source": f"{trace_path.parent.name}:{trace_path.stem}:0",
                "source_path": str(trace_path),
                "event_id": "policy_bad",
                "op": "policy.update",
                "object": "agent.policy",
                "mode": "policy_update",
                "decision": "agent.policy",
                "checker_allowed": "False",
                "required_classes": "agent",
                "control_classes": "tool",
                "data_classes": "tool",
                "requires_env": "False",
                "has_class_substitution_attempt": "True",
                "substitution_edges": "tool->agent",
                "requirement_basis": "agent_authority",
            }
        )
        writer.writerow(
            {
                "source": f"{trace_path.parent.name}:{trace_path.stem}:0",
                "source_path": str(trace_path),
                "event_id": "exec_env",
                "op": "exec.run",
                "object": "/skills/pdf/extract.py",
                "mode": "tool_select",
                "decision": "local.exec",
                "checker_allowed": "True",
                "required_classes": "agent|env|instruction|tool",
                "control_classes": "agent|instruction",
                "data_classes": "env",
                "requires_env": "True",
                "has_class_substitution_attempt": "False",
                "substitution_edges": "",
                "requirement_basis": "agent_authority|env_runtime_evidence|instruction_procedure",
            }
        )

    output_dir = tmp_path / "packet"
    result = packet.build_packet(
        run_id="test",
        event_csv=event_csv,
        output_dir=output_dir,
        target_size=3,
        per_edge=1,
        per_mode_verdict=1,
        min_per_source=1,
        env_quota=1,
    )

    summary = result["summary"]
    assert summary["samples"] == 3
    assert summary["author_first_pass_labels"] == 3
    assert summary["samples_requiring_env"] == 1
    assert summary["samples_with_substitution_attempt"] == 1
    assert summary["substitution_edge_counts"] == {"tool->agent": 1}

    labels = [json.loads(line) for line in (output_dir / "author_labels.codex.jsonl").read_text().splitlines()]
    policy_label = next(label for label in labels if label["sample_id"] == "r221_001")
    assert policy_label["observed_substitution_attempt"] is True
    assert policy_label["unsafe_substitutes"][0]["from"] == "tool"
    assert policy_label["unsafe_substitutes"][0]["to"] == "agent"

    manifest = [json.loads(line) for line in (output_dir / "sample_manifest.jsonl").read_text().splitlines()]
    env_sample = next(sample for sample in manifest if sample["event_id"] == "exec_env")
    assert set(env_sample["derived_required_issuers"]) == {"agent", "env", "instruction", "tool"}
    assert env_sample["data_sources"][0]["issuer_class"] == "env"


def test_label_schema_names_required_fields():
    schema = packet._label_schema()
    assert set(packet.LABEL_FIELDS) == set(schema["required"])
    assert schema["properties"]["required_issuers_human"]["items"]["enum"] == [
        "agent",
        "instruction",
        "tool",
        "env",
    ]
