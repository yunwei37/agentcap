import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_expert_oracle_manifest.py"
    spec = importlib.util.spec_from_file_location("build_expert_oracle_manifest", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_injecagent_event_id_maps_to_case_id():
    builder = _load_builder()

    assert builder.injecagent_case_id_from_event(
        "base:data_stealing:275:GitHubGetUserDetails:0:GitHubGetUserDetails"
    ) == "base:data_stealing:275:GitHubGetUserDetails"
    assert builder.injecagent_case_id_from_event("short") == "short"


def test_manifest_balances_three_existing_workload_families(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)

    result = builder.analyze(
        run_id="T001",
        per_family=2,
        injecagent_case_exposure=paths["inj_cases"],
        injecagent_admitted_attacks=paths["inj_attacks"],
        mcptox_event_exposure=paths["mcp_events"],
        mcptox_admitted_events=paths["mcp_admitted"],
        tau2_task_exposure=paths["tau_tasks"],
    )

    summary = result["summary"]
    assert summary["run_id"] == "T001"
    assert summary["samples_total"] == 6
    assert summary["no_dataset_sync"] is True
    assert summary["samples_by_benchmark"] == {
        "InjecAgent": 2,
        "MCPTox": 2,
        "tau2-bench / tau3-bench": 2,
    }
    assert {row["sample_id"] for row in result["manifest_rows"]} == {
        "EO-INJ-001",
        "EO-INJ-002",
        "EO-MCP-001",
        "EO-MCP-002",
        "EO-TAU-001",
        "EO-TAU-002",
    }
    assert all("baseline" not in row for row in result["manifest_rows"])
    assert "must not inspect" in result["protocol"]
    assert "action_leases" in result["label_schema"]["properties"]


def test_manifest_outputs_protocol_schema_and_digests(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)
    result = builder.analyze(
        run_id="T002",
        per_family=1,
        injecagent_case_exposure=paths["inj_cases"],
        injecagent_admitted_attacks=paths["inj_attacks"],
        mcptox_event_exposure=paths["mcp_events"],
        mcptox_admitted_events=paths["mcp_admitted"],
        tau2_task_exposure=paths["tau_tasks"],
    )

    output_dir = tmp_path / "out"
    builder.write_outputs(output_dir, result)

    manifest = list(csv.DictReader((output_dir / "expert_oracle_task_manifest.csv").open()))
    assert len(manifest) == 3
    assert (output_dir / "blinded_labeling_protocol.md").read_text().startswith(
        "# Blinded Expert Lease Labeling Protocol"
    )
    schema = json.loads((output_dir / "expert_lease_label_schema.json").read_text())
    assert schema["required"] == [
        "sample_id",
        "labeler_id",
        "intent_certificate",
        "allowed_context_influence",
        "action_leases",
        "forbidden_authority",
        "confidence",
    ]
    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))
    assert len(digests) == 5


def _write_inputs(tmp_path):
    paths = {
        "inj_cases": tmp_path / "inj_case_exposure.csv",
        "inj_attacks": tmp_path / "inj_admitted_attacks.csv",
        "mcp_events": tmp_path / "mcp_event_exposure.csv",
        "mcp_admitted": tmp_path / "mcp_admitted_events.csv",
        "tau_tasks": tmp_path / "tau_task_exposure.csv",
    }
    _write_csv(
        paths["inj_cases"],
        [
            {
                "baseline": "intentcap_one_shot",
                "case_id": "base:data_stealing:1:GmailReadEmail",
                "attack_family": "data_stealing",
                "user_tool": "GmailReadEmail",
                "user_toolkit": "Gmail",
            },
            {
                "baseline": "intentcap_one_shot",
                "case_id": "base:direct:2:GitHubGetRepositoryDetails",
                "attack_family": "direct",
                "user_tool": "GitHubGetRepositoryDetails",
                "user_toolkit": "GitHub",
            },
        ],
    )
    _write_csv(
        paths["inj_attacks"],
        [
            {
                "baseline": "task_tool_allowlist",
                "event_id": "base:data_stealing:1:GmailReadEmail:0:GmailReadEmail",
                "attack_family": "data_stealing",
                "attack_type": "Others",
                "user_tool": "GmailReadEmail",
                "user_toolkit": "Gmail",
                "attacker_tool": "GmailReadEmail",
                "attacker_toolkit": "Gmail",
                "mode": "authorize",
            },
            {
                "baseline": "toolkit_allowlist",
                "event_id": "base:direct:2:GitHubGetRepositoryDetails:0:GitHubPush",
                "attack_family": "direct",
                "attack_type": "Infrastructure Damage",
                "user_tool": "GitHubGetRepositoryDetails",
                "user_toolkit": "GitHub",
                "attacker_tool": "GitHubPush",
                "attacker_toolkit": "GitHub",
                "mode": "authorize",
            },
        ],
    )
    _write_csv(
        paths["mcp_events"],
        [
            {
                "baseline": "intentcap_provenance",
                "event_id": "FileSystem:1:1:model:0:read_file",
                "server": "FileSystem",
                "object": "FileSystem.read_file",
                "security_risk": "Credential Leakage",
            },
            {
                "baseline": "intentcap_provenance",
                "event_id": "FileSystem:2:2:model:0:write_file",
                "server": "FileSystem",
                "object": "FileSystem.write_file",
                "security_risk": "Infrastructure Damage",
            },
        ],
    )
    _write_csv(
        paths["mcp_admitted"],
        [
            {
                "baseline": "exact_tool_acl",
                "event_id": "FileSystem:1:1:model:0:read_file",
                "server": "FileSystem",
                "object": "FileSystem.read_file",
                "poisoned_tool": "sky",
                "security_risk": "Credential Leakage",
                "mode": "authorize",
                "parse_method": "structured",
                "object_is_authentic": "True",
            },
            {
                "baseline": "exact_tool_acl",
                "event_id": "FileSystem:2:2:model:0:write_file",
                "server": "FileSystem",
                "object": "FileSystem.write_file",
                "poisoned_tool": "target",
                "security_risk": "Infrastructure Damage",
                "mode": "authorize",
                "parse_method": "structured",
                "object_is_authentic": "True",
            },
        ],
    )
    _write_csv(
        paths["tau_tasks"],
        [
            {
                "baseline": "intentcap_reference_events",
                "domain": "airline",
                "task_id": "7",
                "split_names": "base|train",
                "reward_basis": "DB|COMMUNICATE",
                "assistant_reference_actions": "5",
                "assistant_reference_tools": "3",
                "risk_score": "11",
                "write_tool_slots": "3",
            },
            {
                "baseline": "intentcap_reference_events",
                "domain": "retail",
                "task_id": "9",
                "split_names": "base|test",
                "reward_basis": "DB|ACTION",
                "assistant_reference_actions": "4",
                "assistant_reference_tools": "2",
                "risk_score": "15",
                "write_tool_slots": "2",
            },
            {
                "baseline": "intentcap_reference_events",
                "domain": "mock",
                "task_id": "empty",
                "assistant_reference_actions": "0",
                "assistant_reference_tools": "0",
                "risk_score": "0",
                "write_tool_slots": "0",
            },
        ],
    )
    return paths


def _write_csv(path, rows):
    fields = sorted({field for row in rows for field in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
