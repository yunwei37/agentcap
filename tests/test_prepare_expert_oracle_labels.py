import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_preparer():
    path = Path(__file__).parents[1] / "scripts" / "prepare_expert_oracle_labels.py"
    spec = importlib.util.spec_from_file_location("prepare_expert_oracle_labels", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_prepare_writes_templates_and_adjudication_packet(tmp_path):
    preparer = _load_preparer()
    inputs = _write_inputs(tmp_path)
    out = tmp_path / "R200"

    result = preparer.prepare(
        run_id="T200",
        manifest_path=inputs["manifest"],
        schema_path=inputs["schema"],
        output_dir=out,
        labelers=("expert_a", "expert_b"),
    )

    assert result["summary"]["run_id"] == "T200"
    assert result["summary"]["samples_total"] == 2
    assert result["summary"]["templates_total"] == 4
    assert result["summary"]["template_validation_status"] == {"ok": 4}
    assert (out / "label_templates" / "expert_a" / "EO-INJ-001.json").exists()
    assert (out / "label_templates" / "expert_b" / "EO-TAU-001.json").exists()
    adjudication = list(csv.DictReader((out / "adjudication_sheet.csv").open()))
    assert [row["status"] for row in adjudication] == [
        "needs_independent_labels",
        "needs_independent_labels",
    ]
    report = list(csv.DictReader((out / "template_validation_report.csv").open()))
    assert {row["status"] for row in report} == {"ok"}
    assert all(int(row["placeholder_count"]) > 0 for row in report)


def test_final_validation_rejects_template_placeholders(tmp_path):
    preparer = _load_preparer()
    inputs = _write_inputs(tmp_path)
    out = tmp_path / "R200"
    preparer.prepare(
        run_id="T200",
        manifest_path=inputs["manifest"],
        schema_path=inputs["schema"],
        output_dir=out,
        labelers=("expert_a",),
    )

    result = preparer.validate_label_dir(
        label_dir=out / "label_templates",
        manifest_path=inputs["manifest"],
        schema_path=inputs["schema"],
        output_dir=tmp_path / "validation",
    )

    assert result["summary"]["labels_total"] == 2
    assert result["summary"]["invalid_labels"] == 2
    assert all("placeholder markers remain" in row["errors"] for row in result["validation_rows"])


def test_validation_catches_unknown_sample_duplicate_and_extra_fields(tmp_path):
    preparer = _load_preparer()
    inputs = _write_inputs(tmp_path)
    label_dir = tmp_path / "labels"
    label_dir.mkdir()
    schema = json.loads(inputs["schema"].read_text())
    good = _complete_label("EO-INJ-001", "expert_a")
    duplicate = _complete_label("EO-INJ-001", "expert_a")
    unknown = _complete_label("EO-UNKNOWN", "expert_a")
    unknown["unexpected"] = "not allowed"
    (label_dir / "good.json").write_text(json.dumps(good))
    (label_dir / "duplicate.json").write_text(json.dumps(duplicate))
    (label_dir / "unknown.json").write_text(json.dumps(unknown))

    rows = preparer.validate_label_paths(
        sorted(label_dir.glob("*.json")),
        manifest_sample_ids={"EO-INJ-001", "EO-TAU-001"},
        schema=schema,
    )

    errors = "\n".join(row["errors"] for row in rows)
    assert sum(1 for row in rows if row["status"] == "invalid") == 2
    assert "duplicate label for sample_id/labeler_id: EO-INJ-001/expert_a" in errors
    assert "sample_id not in manifest: EO-UNKNOWN" in errors
    assert "additional top-level field not allowed: unexpected" in errors


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
                "labeler_view": "Write minimal leases for a trusted Gmail read.",
            },
            {
                "sample_id": "EO-TAU-001",
                "benchmark": "tau2-bench / tau3-bench",
                "workload_family": "stateful_utility",
                "task_or_event_id": "airline:7",
                "domain_or_server": "airline",
                "primary_tool_or_object": "assistant reference tools",
                "protected_decision_focus": "tool_select",
                "labeler_view": "Write minimal leases for the stateful task.",
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


def _complete_label(sample_id, labeler_id):
    return {
        "sample_id": sample_id,
        "labeler_id": labeler_id,
        "intent_certificate": {
            "goal": "extract the selected task result",
            "trusted_sources": ["trusted_user_request"],
            "objects": ["selected task object"],
            "sinks": [],
            "expiry": "task_completion",
        },
        "allowed_context_influence": [
            {
                "source": "trusted_user_request",
                "modes": ["authorize"],
                "decision_classes": ["tool_select"],
            }
        ],
        "action_leases": [
            {
                "operation": "tool.call",
                "object": "selected_tool",
                "argument_constraints": {"mode": "exact"},
                "budget": {"invocations": 1},
                "expiry": "task_completion",
            }
        ],
        "forbidden_authority": ["external network"],
        "confidence": "high",
        "notes": "complete label",
    }
