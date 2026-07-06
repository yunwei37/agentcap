import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_e1_security_wrapper_matrix.py"
    spec = importlib.util.spec_from_file_location("build_e1_security_wrapper_matrix", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_security_matrix_consolidates_injecagent_and_mcptox(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)

    result = builder.build_matrix(
        run_id="T202E1",
        injecagent_summary=paths["injecagent"],
        mcptox_summary=paths["mcptox"],
    )

    summary = result["summary"]
    assert summary["run_id"] == "T202E1"
    assert summary["no_dataset_sync"] is True
    assert summary["not_a_fresh_online_run"] is True
    assert summary["matrix_rows"] == 6
    assert summary["intentcap_dangerous_accepted"] == 0
    assert summary["exact_or_task_tool_acl_dangerous_accepted"] == 11
    assert summary["same_event_security_delta"] == 11

    rows = result["matrix_rows"]
    exact_mcp = _row(rows, "MCPTox", "exact_tool_acl")
    intentcap_mcp = _row(rows, "MCPTox", "intentcap_provenance")
    assert exact_mcp["matched_event_count"] == 10
    assert exact_mcp["dangerous_accepted"] == 10
    assert exact_mcp["mean_exposed_tools"] == 1.0
    assert exact_mcp["control_provenance_checked"] is False
    assert intentcap_mcp["dangerous_accepted"] == 0
    assert intentcap_mcp["control_provenance_checked"] is True
    assert intentcap_mcp["dangerous_block_rate"] == 1.0

    family_rows = {row["policy_family"]: row for row in result["family_rows"]}
    assert family_rows["intentcap"]["dangerous_accept_rate"] == 0.0
    assert family_rows["exact_or_task_tool_acl"]["dangerous_accept_rate"] == 0.55
    assert family_rows["toolkit_or_server_allowlist"]["dangerous_accepted"] == 12


def test_security_matrix_writes_outputs(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)
    result = builder.build_matrix(
        run_id="T202E1",
        injecagent_summary=paths["injecagent"],
        mcptox_summary=paths["mcptox"],
    )

    output_dir = tmp_path / "out"
    builder.write_outputs(output_dir, result)

    matrix = list(csv.DictReader((output_dir / "e1_security_wrapper_matrix.csv").open()))
    assert len(matrix) == 6
    families = list(csv.DictReader((output_dir / "e1_security_policy_family_summary.csv").open()))
    assert {row["policy_family"] for row in families} == {
        "exact_or_task_tool_acl",
        "intentcap",
        "toolkit_or_server_allowlist",
    }
    summary = json.loads((output_dir / "e1_security_wrapper_summary.json").read_text())
    assert summary["matrix_rows"] == 6
    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))
    assert len(digests) == 2
    assert (output_dir / "command.txt").exists()


def _row(rows, benchmark, policy):
    return next(row for row in rows if row["benchmark"] == benchmark and row["policy"] == policy)


def _write_inputs(tmp_path):
    paths = {
        "injecagent": tmp_path / "injecagent.json",
        "mcptox": tmp_path / "mcptox.json",
    }
    paths["injecagent"].write_text(json.dumps(_injecagent_summary()))
    paths["mcptox"].write_text(json.dumps(_mcptox_summary()))
    return paths


def _injecagent_summary():
    return {
        "benchmark": "InjecAgent",
        "baseline_order": [
            "intentcap_one_shot",
            "task_tool_allowlist",
            "toolkit_allowlist",
        ],
        "baselines": {
            "intentcap_one_shot": {
                "protected_attack_events": 10,
                "admitted_attack_events": 0,
                "control_provenance_checked": True,
                "broad_arguments": False,
                "mean_exposed_tools_per_case": 1,
                "median_exposed_tools_per_case": 1,
                "p95_exposed_tools_per_case": 1,
                "max_exposed_tools_per_case": 1,
                "exposed_tool_slots_total": 10,
                "tool_slot_over_intentcap_ratio": 1,
                "admitted_by_mode": {},
                "admitted_by_attack_family": {},
            },
            "task_tool_allowlist": {
                "protected_attack_events": 10,
                "admitted_attack_events": 1,
                "control_provenance_checked": False,
                "broad_arguments": True,
                "mean_exposed_tools_per_case": 1,
                "median_exposed_tools_per_case": 1,
                "p95_exposed_tools_per_case": 1,
                "max_exposed_tools_per_case": 1,
                "exposed_tool_slots_total": 10,
                "tool_slot_over_intentcap_ratio": 1,
                "admitted_by_mode": {"authorize": 1},
                "admitted_by_attack_family": {"data_stealing": 1},
            },
            "toolkit_allowlist": {
                "protected_attack_events": 10,
                "admitted_attack_events": 2,
                "control_provenance_checked": False,
                "broad_arguments": True,
                "mean_exposed_tools_per_case": 5,
                "median_exposed_tools_per_case": 5,
                "p95_exposed_tools_per_case": 5,
                "max_exposed_tools_per_case": 7,
                "exposed_tool_slots_total": 50,
                "tool_slot_over_intentcap_ratio": 5,
                "admitted_by_mode": {"sink_select": 2},
                "admitted_by_attack_family": {"data_stealing": 2},
            },
        },
    }


def _mcptox_summary():
    return {
        "benchmark": "MCPTox",
        "baseline_order": [
            "intentcap_provenance",
            "exact_tool_acl",
            "authentic_server_allowlist",
        ],
        "baselines": {
            "intentcap_provenance": {
                "protected_events": 10,
                "admitted_events": 0,
                "control_provenance_checked": True,
                "argument_event_id_checked": True,
                "mean_exposed_tools_per_event": 1,
                "median_exposed_tools_per_event": 1,
                "p95_exposed_tools_per_event": 1,
                "max_exposed_tools_per_event": 1,
                "mean_tool_exposure_over_intentcap": 1,
                "admitted_by_mode": {},
                "admitted_by_security_risk": {},
            },
            "exact_tool_acl": {
                "protected_events": 10,
                "admitted_events": 10,
                "control_provenance_checked": False,
                "argument_event_id_checked": False,
                "mean_exposed_tools_per_event": 1,
                "median_exposed_tools_per_event": 1,
                "p95_exposed_tools_per_event": 1,
                "max_exposed_tools_per_event": 1,
                "mean_tool_exposure_over_intentcap": 1,
                "admitted_by_mode": {"authorize": 10},
                "admitted_by_security_risk": {"Credential Leakage": 10},
            },
            "authentic_server_allowlist": {
                "protected_events": 10,
                "admitted_events": 10,
                "control_provenance_checked": False,
                "argument_event_id_checked": False,
                "mean_exposed_tools_per_event": 4,
                "median_exposed_tools_per_event": 4,
                "p95_exposed_tools_per_event": 4,
                "max_exposed_tools_per_event": 8,
                "mean_tool_exposure_over_intentcap": 4,
                "admitted_by_mode": {"authorize": 10},
                "admitted_by_security_risk": {"Credential Leakage": 10},
            },
        },
    }
