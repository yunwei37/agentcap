import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_adjudicator():
    path = Path(__file__).parents[1] / "scripts" / "adjudicate_expert_oracle_labels_codex.py"
    spec = importlib.util.spec_from_file_location("adjudicate_expert_oracle_labels_codex", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_codex_adjudicator_writes_three_benchmark_label_shapes(tmp_path):
    adjudicator = _load_adjudicator()
    manifest = tmp_path / "manifest.csv"
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
                "primary_tool_or_object": (
                    "assistant_reference_tools=4; assistant_reference_actions=19"
                ),
                "protected_decision_focus": "tool_select/authorize/argument_bind",
                "related_context": "split_names=base|test; risk_score=25; write_tool_slots=3",
            },
        ],
    )

    result = adjudicator.adjudicate(
        run_id="T204E2",
        manifest_path=manifest,
        output_dir=tmp_path / "out",
    )

    assert result["summary"]["adjudication_status"] == "ok"
    labels = {label["sample_id"]: label for label in result["labels"]}
    assert labels["EO-INJ-001"]["action_leases"][0]["operation"] == "tool.call"
    assert labels["EO-INJ-001"]["action_leases"][0]["allowed_sinks"] == [
        "sink://trusted/Gmail"
    ]
    assert "attacker_tool:GmailSendEmail" in labels["EO-INJ-001"]["forbidden_authority"]
    assert labels["EO-MCP-001"]["action_leases"][0]["operation"] == "mcp.call"
    assert labels["EO-MCP-001"]["action_leases"][0]["argument_constraints"][
        "argument_event_id_checked"
    ] is True
    assert labels["EO-TAU-001"]["action_leases"][0]["budget"]["invocations"] == 19
    assert labels["EO-TAU-001"]["action_leases"][0]["object"] == (
        "tau2:airline:44:assistant_reference_actions"
    )
    review = list(csv.DictReader((tmp_path / "out" / "codex_adjudication_review.csv").open()))
    assert [row["status"] for row in review] == ["adjudicated", "adjudicated", "adjudicated"]
    assert (tmp_path / "out" / "codex_adjudication_command.txt").exists()


def test_codex_adjudicator_labels_are_placeholder_free(tmp_path):
    adjudicator = _load_adjudicator()
    manifest = tmp_path / "manifest.csv"
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
                "protected_decision_focus": "authorize",
                "related_context": "",
            }
        ],
    )
    adjudicator.adjudicate(
        run_id="T204E2",
        manifest_path=manifest,
        output_dir=tmp_path / "out",
    )

    label = json.loads((tmp_path / "out" / "adjudicated_labels" / "EO-INJ-001.json").read_text())
    assert "TODO" not in json.dumps(label)
    assert "TEMPLATE" not in json.dumps(label)
    assert label["labeler_id"] == "codex_adjudicated"


def _write_csv(path, rows):
    with path.open("w", newline="") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
