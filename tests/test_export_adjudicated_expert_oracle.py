import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_exporter():
    path = Path(__file__).parents[1] / "scripts" / "export_adjudicated_expert_oracle.py"
    spec = importlib.util.spec_from_file_location("export_adjudicated_expert_oracle", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_export_writes_flattened_oracle_rows_and_jsonl(tmp_path):
    exporter = _load_exporter()
    inputs = _write_inputs(tmp_path)
    label_dir = tmp_path / "adjudicated"
    label_dir.mkdir()
    (label_dir / "EO-INJ-001.json").write_text(
        json.dumps(_complete_label("EO-INJ-001", "adjudicated", "GmailReadEmail"))
    )
    (label_dir / "EO-TAU-001.json").write_text(
        json.dumps(_complete_label("EO-TAU-001", "adjudicated", "update_reservation"))
    )

    result = exporter.export_adjudicated_oracle(
        run_id="T201",
        manifest_path=inputs["manifest"],
        schema_path=inputs["schema"],
        label_dir=label_dir,
        output_dir=tmp_path / "R201",
    )

    assert result["summary"]["run_id"] == "T201"
    assert result["summary"]["export_status"] == "ok"
    assert result["summary"]["exported_rows"] == 2
    assert result["summary"]["invalid_labels"] == 0
    rows = list(csv.DictReader((tmp_path / "R201" / "adjudicated_expert_oracle.csv").open()))
    assert [row["sample_id"] for row in rows] == ["EO-INJ-001", "EO-TAU-001"]
    assert rows[0]["action_lease_count"] == "1"
    assert rows[0]["lease_operations"] == "tool.call"
    assert rows[0]["budget_invocations_total"] == "1"
    assert rows[0]["influence_modes"] == "authorize|parameterize"
    records = [
        json.loads(line)
        for line in (tmp_path / "R201" / "adjudicated_expert_oracle.jsonl")
        .read_text()
        .splitlines()
    ]
    assert records[0]["label"]["sample_id"] == "EO-INJ-001"
    validation = list(csv.DictReader((tmp_path / "R201" / "label_validation_report.csv").open()))
    assert {row["status"] for row in validation} == {"ok"}


def test_export_marks_missing_samples_incomplete_by_default(tmp_path):
    exporter = _load_exporter()
    inputs = _write_inputs(tmp_path)
    label_dir = tmp_path / "adjudicated"
    label_dir.mkdir()
    (label_dir / "EO-INJ-001.json").write_text(
        json.dumps(_complete_label("EO-INJ-001", "adjudicated", "GmailReadEmail"))
    )

    result = exporter.export_adjudicated_oracle(
        run_id="T201",
        manifest_path=inputs["manifest"],
        schema_path=inputs["schema"],
        label_dir=label_dir,
        output_dir=tmp_path / "R201",
    )

    assert result["summary"]["export_status"] == "incomplete"
    assert result["summary"]["missing_samples"] == ["EO-TAU-001"]
    assert result["summary"]["exported_rows"] == 1


def test_export_rejects_ambiguous_adjudicated_labels(tmp_path):
    exporter = _load_exporter()
    inputs = _write_inputs(tmp_path)
    label_dir = tmp_path / "adjudicated"
    label_dir.mkdir()
    (label_dir / "a.json").write_text(
        json.dumps(_complete_label("EO-INJ-001", "expert_a", "GmailReadEmail"))
    )
    (label_dir / "b.json").write_text(
        json.dumps(_complete_label("EO-INJ-001", "expert_b", "GmailReadEmail"))
    )

    result = exporter.export_adjudicated_oracle(
        run_id="T201",
        manifest_path=inputs["manifest"],
        schema_path=inputs["schema"],
        label_dir=label_dir,
        output_dir=tmp_path / "R201",
        allow_partial=True,
    )

    assert result["summary"]["export_status"] == "incomplete"
    assert result["summary"]["ambiguous_adjudicated_samples"] == ["EO-INJ-001"]
    assert result["summary"]["exported_rows"] == 0


def _write_inputs(tmp_path):
    manifest = tmp_path / "manifest.csv"
    schema = tmp_path / "schema.json"
    _write_csv(
        manifest,
        [
            {
                "sample_id": "EO-INJ-001",
                "benchmark": "InjecAgent",
                "workload_family": "tool_response_injection",
                "task_or_event_id": "base:data_stealing:1:GmailReadEmail",
                "domain_or_server": "Gmail",
                "primary_tool_or_object": "GmailReadEmail",
                "protected_decision_focus": "sink_select",
            },
            {
                "sample_id": "EO-TAU-001",
                "benchmark": "tau2-bench / tau3-bench",
                "workload_family": "stateful_utility",
                "task_or_event_id": "airline:7",
                "domain_or_server": "airline",
                "primary_tool_or_object": "assistant reference tools",
                "protected_decision_focus": "tool_select",
            },
        ],
    )
    schema.write_text(json.dumps(_schema()))
    return {"manifest": manifest, "schema": schema}


def _write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _schema():
    return {
        "properties": {
            "sample_id": {"type": "string"},
            "labeler_id": {"type": "string"},
            "intent_certificate": {"type": "object"},
            "allowed_context_influence": {"type": "array"},
            "action_leases": {"type": "array"},
            "forbidden_authority": {"type": "array"},
            "confidence": {"type": "string"},
            "notes": {"type": "string"},
        },
        "required": [
            "sample_id",
            "labeler_id",
            "intent_certificate",
            "allowed_context_influence",
            "action_leases",
            "forbidden_authority",
            "confidence",
        ],
    }


def _complete_label(sample_id, labeler_id, object_name):
    return {
        "sample_id": sample_id,
        "labeler_id": labeler_id,
        "intent_certificate": {
            "goal": "perform the selected trusted task",
            "trusted_sources": ["trusted_user_request"],
            "objects": [object_name],
            "sinks": [],
            "expiry": "task_completion",
        },
        "allowed_context_influence": [
            {
                "source": "trusted_user_request",
                "modes": ["authorize"],
                "decision_classes": ["tool_select"],
            },
            {
                "source": "task_data",
                "modes": ["parameterize"],
                "decision_classes": ["tool_arguments"],
            },
        ],
        "action_leases": [
            {
                "operation": "tool.call",
                "object": object_name,
                "argument_constraints": {"mode": "exact"},
                "allowed_sinks": [],
                "budget": {"invocations": 1},
                "expiry": "task_completion",
            }
        ],
        "forbidden_authority": ["external network"],
        "confidence": "high",
        "notes": "complete adjudicated label",
    }
