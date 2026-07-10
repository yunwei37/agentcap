import csv
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


def test_e2_adjudication_audit_accepts_three_label_shapes(tmp_path):
    repo = Path(__file__).parents[1]
    adjudicator = _load_module(
        "adjudicate_expert_oracle_labels_codex",
        repo / "scripts" / "adjudicate_expert_oracle_labels_codex.py",
    )
    auditor = _load_module(
        "audit_e2_expert_adjudication",
        repo / "scripts" / "audit_e2_expert_adjudication.py",
    )
    manifest = tmp_path / "manifest.csv"
    labels = tmp_path / "labels"
    labels.mkdir()
    rows = _manifest_rows()
    _write_csv(manifest, rows)
    for row in rows:
        (labels / f"{row['sample_id']}.json").write_text(
            json.dumps(adjudicator.build_label(row), indent=2, sort_keys=True)
        )
    validation_summary = _write_validation_summary(tmp_path, 3)
    policy_summary = tmp_path / "policy_summary.csv"
    distance_rows = tmp_path / "distance.csv"
    _write_csv(
        policy_summary,
        [
            {"policy": "intentcap_one_shot", "total_oracle_distance_score": "0"},
            {"policy": "task_tool_allowlist", "total_oracle_distance_score": "10"},
        ],
    )
    _write_csv(distance_rows, [{"status": "ok"}, {"status": "ok"}])

    result = auditor.audit(
        run_id="T207E2A",
        manifest_path=manifest,
        label_dir=labels,
        validation_summary_path=validation_summary,
        policy_summary_path=policy_summary,
        distance_rows_path=distance_rows,
        output_dir=tmp_path / "out",
    )

    assert result["summary"]["audit_status"] == "ok"
    assert result["summary"]["failed_checks_total"] == 0
    report = list(
        csv.DictReader((tmp_path / "out" / "e2_expert_adjudication_audit_report.csv").open())
    )
    assert [row["status"] for row in report] == ["ok", "ok", "ok"]
    assert {row["confidence"] for row in report} == {"high", "medium"}
    assert (tmp_path / "out" / "input_digests.csv").exists()


def test_e2_adjudication_audit_flags_missing_injected_control_denial(tmp_path):
    repo = Path(__file__).parents[1]
    adjudicator = _load_module(
        "adjudicate_expert_oracle_labels_codex",
        repo / "scripts" / "adjudicate_expert_oracle_labels_codex.py",
    )
    auditor = _load_module(
        "audit_e2_expert_adjudication",
        repo / "scripts" / "audit_e2_expert_adjudication.py",
    )
    manifest = tmp_path / "manifest.csv"
    labels = tmp_path / "labels"
    labels.mkdir()
    row = _manifest_rows()[0]
    _write_csv(manifest, [row])
    label = adjudicator.build_label(row)
    label["action_leases"][0]["control_must_not_depend_on"] = []
    (labels / f"{row['sample_id']}.json").write_text(json.dumps(label, indent=2, sort_keys=True))
    validation_summary = _write_validation_summary(tmp_path, 1)
    policy_summary = tmp_path / "policy_summary.csv"
    distance_rows = tmp_path / "distance.csv"
    _write_csv(
        policy_summary,
        [
            {"policy": "intentcap_one_shot", "total_oracle_distance_score": "0"},
            {"policy": "task_tool_allowlist", "total_oracle_distance_score": "10"},
        ],
    )
    _write_csv(distance_rows, [{"status": "ok"}])

    result = auditor.audit(
        run_id="T207E2A",
        manifest_path=manifest,
        label_dir=labels,
        validation_summary_path=validation_summary,
        policy_summary_path=policy_summary,
        distance_rows_path=distance_rows,
        output_dir=tmp_path / "out",
    )

    assert result["summary"]["audit_status"] == "failed"
    assert result["summary"]["failed_samples"] == ["EO-INJ-001"]
    assert "injecagent_denies_injected_control" in result["report_rows"][0]["failed_checks"]


def _manifest_rows():
    return [
        {
            "sample_id": "EO-INJ-001",
            "benchmark": "InjecAgent",
            "workload_family": "tool_response_injection",
            "task_or_event_id": "base:data_stealing:1:GmailReadEmail",
            "domain_or_server": "Gmail",
            "primary_tool_or_object": "GmailReadEmail",
            "protected_decision_focus": "sink_select",
            "related_context": "attacker_tool=GmailSendEmail; attacker_toolkit=Gmail",
        },
        {
            "sample_id": "EO-MCP-001",
            "benchmark": "MCPTox",
            "workload_family": "mcp_tool_poisoning",
            "task_or_event_id": "Git:1:2:model:0:git_commit",
            "domain_or_server": "Git",
            "primary_tool_or_object": "Git.git_commit",
            "protected_decision_focus": "authorize",
            "related_context": "poisoned_tool_excerpt=commit_linter",
        },
        {
            "sample_id": "EO-TAU-001",
            "benchmark": "tau2-bench / tau3-bench",
            "workload_family": "stateful_utility_task",
            "task_or_event_id": "44",
            "domain_or_server": "airline",
            "primary_tool_or_object": "assistant_reference_tools=4; assistant_reference_actions=19",
            "protected_decision_focus": "tool_select/authorize/argument_bind",
            "related_context": "split_names=base|test; risk_score=25; write_tool_slots=3",
        },
    ]


def _write_validation_summary(tmp_path, labels_total):
    path = tmp_path / "validation_summary.json"
    path.write_text(
        json.dumps(
            {
                "labels_total": labels_total,
                "invalid_labels": 0,
                "validation_status": {"ok": labels_total},
            }
        )
    )
    return path


def _write_csv(path, rows):
    with path.open("w", newline="") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
