import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_expert_oracle_policy_rows.py"
    spec = importlib.util.spec_from_file_location("build_expert_oracle_policy_rows", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_policy_rows_normalize_three_workload_families(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)

    result = builder.build_policy_rows(
        run_id="T201P",
        manifest_path=paths["manifest"],
        injecagent_case_exposure=paths["inj_cases"],
        mcptox_event_exposure=paths["mcp_events"],
        tau2_task_exposure=paths["tau_tasks"],
    )

    assert result["summary"]["run_id"] == "T201P"
    assert result["summary"]["row_status"] == "ok"
    assert result["summary"]["no_dataset_sync"] is True
    assert result["summary"]["manifest_samples"] == 3
    assert result["summary"]["policy_rows"] == 6
    assert result["summary"]["rows_by_benchmark"] == {
        "InjecAgent": 2,
        "MCPTox": 2,
        "tau2-bench / tau3-bench": 2,
    }

    rows = result["policy_rows"]
    intentcap = _row(rows, "EO-INJ-001", "intentcap_one_shot")
    task_acl = _row(rows, "EO-INJ-001", "toolkit_allowlist")
    assert intentcap["policy_row_kind"] == "intentcap_candidate"
    assert intentcap["lease_objects"] == "GmailReadEmail"
    assert "toolkit:Gmail:*" in task_acl["lease_objects"]
    assert "plan" in task_acl["influence_modes"]
    assert "delegation" in task_acl["decision_classes"]
    exact_args = json.loads(intentcap["lease_argument_constraints_json"])[0]
    broad_args = json.loads(task_acl["lease_argument_constraints_json"])[0]
    assert exact_args["control_provenance_checked"] is True
    assert broad_args["control_provenance_checked"] is False

    mcp_global = _row(rows, "EO-MCP-001", "global_observed_tools")
    assert "mcp-observed-tools:*" in mcp_global["lease_objects"]
    assert "mcp.call" == mcp_global["lease_operations"]

    tau_domain = _row(rows, "EO-TAU-001", "domain_assistant_regular")
    assert "tau2:airline:assistant_regular:*" in tau_domain["lease_objects"]
    assert tau_domain["lease_allowed_sinks"] == "tau2://airline/*|tau2://airline/task-state"
    assert tau_domain["budget_invocations_total"] == 5


def test_policy_rows_write_outputs_and_counts(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)
    result = builder.build_policy_rows(
        run_id="T201P",
        manifest_path=paths["manifest"],
        injecagent_case_exposure=paths["inj_cases"],
        mcptox_event_exposure=paths["mcp_events"],
        tau2_task_exposure=paths["tau_tasks"],
    )

    output_dir = tmp_path / "out"
    builder.write_outputs(output_dir, result)

    rows = list(csv.DictReader((output_dir / "expert_oracle_policy_rows.csv").open()))
    assert len(rows) == 6
    counts = list(csv.DictReader((output_dir / "expert_oracle_policy_row_counts.csv").open()))
    assert {row["policy"] for row in counts} == {
        "domain_assistant_regular",
        "global_observed_tools",
        "intentcap_one_shot",
        "intentcap_provenance",
        "intentcap_reference_events",
        "toolkit_allowlist",
    }
    summary = json.loads((output_dir / "expert_oracle_policy_rows_summary.json").read_text())
    assert summary["policy_rows"] == 6
    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))
    assert len(digests) == 4
    assert (output_dir / "command.txt").exists()


def test_missing_policy_exposure_marks_summary_incomplete(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path, include_tau=False)

    result = builder.build_policy_rows(
        run_id="T201P",
        manifest_path=paths["manifest"],
        injecagent_case_exposure=paths["inj_cases"],
        mcptox_event_exposure=paths["mcp_events"],
        tau2_task_exposure=paths["tau_tasks"],
    )

    assert result["summary"]["row_status"] == "incomplete"
    assert result["summary"]["missing_policy_samples"] == [
        {
            "sample_id": "EO-TAU-001",
            "benchmark": "tau2-bench / tau3-bench",
            "task_or_event_id": "44",
        }
    ]


def _row(rows, sample_id, policy):
    return next(row for row in rows if row["sample_id"] == sample_id and row["policy"] == policy)


def _write_inputs(tmp_path, include_tau=True):
    paths = {
        "manifest": tmp_path / "manifest.csv",
        "inj_cases": tmp_path / "inj_case_exposure.csv",
        "mcp_events": tmp_path / "mcp_event_exposure.csv",
        "tau_tasks": tmp_path / "tau_task_exposure.csv",
    }
    _write_csv(
        paths["manifest"],
        [
            {
                "sample_id": "EO-INJ-001",
                "benchmark": "InjecAgent",
                "workload_family": "tool_response_injection",
                "source_row_id": "base:data_stealing:1:GmailReadEmail:0:GmailSendEmail",
                "task_or_event_id": "base:data_stealing:1:GmailReadEmail",
                "domain_or_server": "Gmail",
                "primary_tool_or_object": "GmailReadEmail",
                "protected_decision_focus": "sink_select",
            },
            {
                "sample_id": "EO-MCP-001",
                "benchmark": "MCPTox",
                "workload_family": "mcp_tool_poisoning",
                "source_row_id": "Git:1:2:model:0:git_commit",
                "task_or_event_id": "Git:1:2:model:0:git_commit",
                "domain_or_server": "Git",
                "primary_tool_or_object": "Git.git_commit",
                "protected_decision_focus": "authorize",
            },
            {
                "sample_id": "EO-TAU-001",
                "benchmark": "tau2-bench / tau3-bench",
                "workload_family": "stateful_utility_task",
                "source_row_id": "airline; 44",
                "task_or_event_id": "44",
                "domain_or_server": "airline",
                "primary_tool_or_object": "assistant_reference_tools=2; assistant_reference_actions=3",
                "protected_decision_focus": "tool_select/authorize/argument_bind",
            },
        ],
    )
    _write_csv(
        paths["inj_cases"],
        [
            {
                "baseline": "intentcap_one_shot",
                "case_id": "base:data_stealing:1:GmailReadEmail",
                "attack_family": "data_stealing",
                "user_tool": "GmailReadEmail",
                "user_toolkit": "Gmail",
                "exposed_tools": "1",
            },
            {
                "baseline": "toolkit_allowlist",
                "case_id": "base:data_stealing:1:GmailReadEmail",
                "attack_family": "data_stealing",
                "user_tool": "GmailReadEmail",
                "user_toolkit": "Gmail",
                "exposed_tools": "7",
            },
        ],
    )
    _write_csv(
        paths["mcp_events"],
        [
            {
                "baseline": "intentcap_provenance",
                "event_id": "Git:1:2:model:0:git_commit",
                "server": "Git",
                "object": "Git.git_commit",
                "security_risk": "Infrastructure Damage",
                "mode": "authorize",
                "exposed_tools": "1",
            },
            {
                "baseline": "global_observed_tools",
                "event_id": "Git:1:2:model:0:git_commit",
                "server": "Git",
                "object": "Git.git_commit",
                "security_risk": "Infrastructure Damage",
                "mode": "authorize",
                "exposed_tools": "284",
            },
        ],
    )
    tau_rows = []
    if include_tau:
        tau_rows = [
            {
                "baseline": "intentcap_reference_events",
                "domain": "airline",
                "task_id": "44",
                "assistant_reference_actions": "3",
                "assistant_reference_tools": "2",
                "exposed_tools": "3",
                "coverage_rate": "1.0",
                "write_tool_slots": "1",
            },
            {
                "baseline": "domain_assistant_regular",
                "domain": "airline",
                "task_id": "44",
                "assistant_reference_actions": "3",
                "assistant_reference_tools": "2",
                "exposed_tools": "5",
                "coverage_rate": "1.0",
                "write_tool_slots": "1",
            },
        ]
    _write_csv(paths["tau_tasks"], tau_rows, fallback_fields=["baseline", "domain", "task_id"])
    return paths


def _write_csv(path, rows, fallback_fields=None):
    if rows:
        fields = sorted({field for row in rows for field in row})
    else:
        fields = fallback_fields or ["empty"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
