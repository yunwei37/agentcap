import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_e1_utility_wrapper_matrix.py"
    spec = importlib.util.spec_from_file_location("build_e1_utility_wrapper_matrix", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_utility_matrix_separates_replay_from_coverage_proxy(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)

    result = builder.build_matrix(
        run_id="T203E1U",
        authority_summary=paths["authority"],
        oracle_summary=paths["oracle"],
    )

    summary = result["summary"]
    assert summary["run_id"] == "T203E1U"
    assert summary["not_a_fresh_online_run"] is True
    assert summary["not_a_model_task_success_result"] is True
    assert summary["matrix_rows"] == 4
    assert summary["intentcap_reference_action_coverage_rate"] == 1.0
    assert summary["exact_or_task_tool_acl_reference_action_coverage_rate"] == 1.0
    assert summary["intentcap_replay_tool_oracle_pass_tasks"] == 9
    assert summary["max_extra_tool_slots_vs_intentcap"] == 90

    rows = result["matrix_rows"]
    intentcap = _row(rows, "intentcap_reference_events")
    exact_acl = _row(rows, "task_reference_tools")
    domain = _row(rows, "domain_assistant_regular")
    global_all = _row(rows, "global_all_tools")

    assert intentcap["direct_intentcap_reference_replay"] is True
    assert intentcap["replay_tool_oracle_pass_rate"] == 0.9
    assert exact_acl["direct_intentcap_reference_replay"] is False
    assert exact_acl["replay_tool_oracle_pass_tasks"] == ""
    assert exact_acl["allowed_reference_actions"] == 12
    assert domain["blocked_reference_actions"] == 0
    assert global_all["extra_tool_slots_vs_intentcap"] == 90

    families = {row["policy_family"]: row for row in result["family_rows"]}
    assert families["intentcap"]["any_direct_intentcap_reference_replay"] is True
    assert families["exact_or_task_tool_acl"]["all_rows_check_control_provenance"] is False
    assert families["global_catalog_acl"]["max_extra_tool_slots_vs_intentcap"] == 90


def test_utility_matrix_writes_outputs(tmp_path):
    builder = _load_builder()
    paths = _write_inputs(tmp_path)
    result = builder.build_matrix(
        run_id="T203E1U",
        authority_summary=paths["authority"],
        oracle_summary=paths["oracle"],
    )

    output_dir = tmp_path / "out"
    builder.write_outputs(output_dir, result)

    matrix = list(csv.DictReader((output_dir / "e1_utility_wrapper_matrix.csv").open()))
    assert len(matrix) == 4
    families = list(csv.DictReader((output_dir / "e1_utility_policy_family_summary.csv").open()))
    assert {row["policy_family"] for row in families} == {
        "domain_allowlist",
        "exact_or_task_tool_acl",
        "global_catalog_acl",
        "intentcap",
    }
    summary = json.loads((output_dir / "e1_utility_wrapper_summary.json").read_text())
    assert summary["assistant_reference_actions"] == 12
    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))
    assert len(digests) == 2
    assert (output_dir / "command.txt").exists()


def _row(rows, policy):
    return next(row for row in rows if row["policy"] == policy)


def _write_inputs(tmp_path):
    paths = {
        "authority": tmp_path / "authority.json",
        "oracle": tmp_path / "oracle.json",
    }
    paths["authority"].write_text(json.dumps(_authority_summary()))
    paths["oracle"].write_text(json.dumps(_oracle_summary()))
    return paths


def _authority_summary():
    return {
        "benchmark": "tau2-bench / tau3-bench",
        "tasks": 10,
        "assistant_reference_actions": 12,
        "baseline_order": [
            "intentcap_reference_events",
            "task_reference_tools",
            "domain_assistant_regular",
            "global_all_tools",
        ],
        "baselines": {
            "intentcap_reference_events": _baseline(
                covered=12,
                mean_tools=1.2,
                max_tools=3,
                exposed_slots=12,
                extra_slots=0,
                ratio=1.0,
                provenance=True,
                event_id=True,
                args=True,
            ),
            "task_reference_tools": _baseline(
                covered=12,
                mean_tools=1.0,
                max_tools=2,
                exposed_slots=10,
                extra_slots=-2,
                ratio=0.8,
                provenance=False,
                event_id=False,
                args=True,
            ),
            "domain_assistant_regular": _baseline(
                covered=12,
                mean_tools=5.0,
                max_tools=7,
                exposed_slots=50,
                extra_slots=38,
                ratio=4.2,
                provenance=False,
                event_id=False,
                args=False,
            ),
            "global_all_tools": _baseline(
                covered=12,
                mean_tools=11.0,
                max_tools=11,
                exposed_slots=110,
                extra_slots=90,
                ratio=9.2,
                provenance=False,
                event_id=False,
                args=False,
            ),
        },
    }


def _baseline(
    *,
    covered,
    mean_tools,
    max_tools,
    exposed_slots,
    extra_slots,
    ratio,
    provenance,
    event_id,
    args,
):
    return {
        "tasks": 10,
        "tasks_with_assistant_reference_actions": 8,
        "assistant_reference_actions": 12,
        "covered_assistant_reference_actions": covered,
        "tasks_with_full_assistant_reference_coverage": 10,
        "control_provenance_checked": provenance,
        "event_id_checked": event_id,
        "argument_values_constrained": args,
        "mean_exposed_tools_per_task": mean_tools,
        "median_exposed_tools_per_task": mean_tools,
        "p95_exposed_tools_per_task": max_tools,
        "max_exposed_tools_per_task": max_tools,
        "exposed_tool_slots_total": exposed_slots,
        "extra_tool_slots_vs_intentcap": extra_slots,
        "tool_slot_over_intentcap_ratio": ratio,
        "write_tool_slots_total": exposed_slots // 2,
        "discoverable_tool_slots_total": 0,
    }


def _oracle_summary():
    return {
        "tool_oracle_applicable_tasks": 10,
        "tool_oracle_pass_tasks": 9,
        "tool_oracle_pass_rate": 0.9,
        "tool_error_events": 1,
    }
