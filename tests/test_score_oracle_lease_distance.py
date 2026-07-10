import importlib.util
import json
import sys
from pathlib import Path


def _load_scorer():
    path = Path(__file__).parents[1] / "scripts" / "score_oracle_lease_distance.py"
    spec = importlib.util.spec_from_file_location("score_oracle_lease_distance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_oracle_distance_penalizes_same_tool_without_provenance(tmp_path):
    scorer = _load_scorer()
    paths = _write_inputs(tmp_path)
    summaries = [json.loads(path.read_text()) for path in paths]

    result = scorer.analyze(summaries, tuple(paths))
    rows = {
        (row["benchmark"], row["baseline"]): row
        for row in result["rows"]
    }

    assert rows[("InjecAgent", "intentcap_one_shot")]["oracle_distance_score"] == 0
    assert rows[("MCPTox", "intentcap_provenance")]["oracle_distance_score"] == 0
    assert rows[("tau2-bench / tau3-bench", "intentcap_reference_events")][
        "oracle_distance_score"
    ] == 0

    exact_tool = rows[("MCPTox", "exact_tool_acl")]
    assert exact_tool["exposed_slots_total"] == exact_tool["oracle_slots_total"]
    assert exact_tool["unsafe_events_admitted"] == 2
    assert exact_tool["control_provenance_checked"] is False
    assert exact_tool["event_binding_checked"] is False
    assert exact_tool["argument_constraints_checked"] is False
    assert exact_tool["oracle_distance_score"] == 2450


def test_tau2_task_reference_is_closer_than_domain_acl_but_not_oracle(tmp_path):
    scorer = _load_scorer()
    paths = _write_inputs(tmp_path)
    summaries = [json.loads(path.read_text()) for path in paths]

    result = scorer.analyze(summaries, tuple(paths))
    rows = {
        (row["benchmark"], row["baseline"]): row
        for row in result["rows"]
    }
    tau_task = rows[("tau2-bench / tau3-bench", "task_reference_tools")]
    tau_domain = rows[("tau2-bench / tau3-bench", "domain_assistant_regular")]

    assert tau_task["exposed_slots_total"] == 2
    assert tau_task["granularity_deficit_slots_vs_oracle"] == 1
    assert tau_task["argument_constraints_checked"] is True
    assert tau_task["oracle_distance_score"] == 351
    assert tau_domain["extra_authority_slots_vs_oracle"] == 3
    assert tau_domain["argument_constraints_checked"] is False
    assert tau_domain["oracle_distance_score"] == 453
    assert tau_task["oracle_distance_score"] < tau_domain["oracle_distance_score"]


def test_summary_records_saved_result_only_boundary(tmp_path):
    scorer = _load_scorer()
    paths = _write_inputs(tmp_path)
    summaries = [json.loads(path.read_text()) for path in paths]

    result = scorer.analyze(summaries, tuple(paths))
    summary = result["summary"]

    assert summary["run_id"] == "R027"
    assert summary["benchmark_count"] == 3
    assert summary["oracle_rows"] == 3
    assert summary["non_oracle_rows"] == 4
    assert summary["total_non_oracle_unsafe_events_admitted"] == 3
    assert "does not run models, clone, sync, download" in summary["notes"][0]
    assert summary["closest_non_oracle_by_benchmark"]["tau2-bench / tau3-bench"] == (
        "task_reference_tools"
    )
    assert len(summary["input_digests"]) == 3


def _write_inputs(tmp_path):
    paths = []
    for name, payload in [
        ("injecagent.json", _injecagent_summary()),
        ("mcptox.json", _mcptox_summary()),
        ("tau2.json", _tau2_summary()),
    ]:
        path = tmp_path / name
        path.write_text(json.dumps(payload))
        paths.append(path)
    return paths


def _injecagent_summary():
    return {
        "benchmark": "InjecAgent",
        "cases": 2,
        "protected_attack_events": 3,
        "baseline_order": ["intentcap_one_shot", "task_tool_allowlist"],
        "baselines": {
            "intentcap_one_shot": {
                "description": "oracle",
                "protected_attack_events": 3,
                "admitted_attack_events": 0,
                "exposed_tool_slots_total": 2,
                "control_provenance_checked": True,
                "broad_arguments": False,
            },
            "task_tool_allowlist": {
                "description": "same tool without provenance",
                "protected_attack_events": 3,
                "admitted_attack_events": 1,
                "exposed_tool_slots_total": 2,
                "control_provenance_checked": False,
                "broad_arguments": True,
            },
        },
    }


def _mcptox_summary():
    return {
        "benchmark": "MCPTox",
        "protected_events": 2,
        "baseline_order": ["intentcap_provenance", "exact_tool_acl"],
        "baselines": {
            "intentcap_provenance": {
                "description": "oracle",
                "protected_events": 2,
                "admitted_events": 0,
                "mean_exposed_tools_per_event": 1.0,
                "control_provenance_checked": True,
                "argument_event_id_checked": True,
            },
            "exact_tool_acl": {
                "description": "same object without provenance",
                "protected_events": 2,
                "admitted_events": 2,
                "mean_exposed_tools_per_event": 1.0,
                "control_provenance_checked": False,
                "argument_event_id_checked": False,
            },
        },
    }


def _tau2_summary():
    return {
        "benchmark": "tau2-bench / tau3-bench",
        "tasks": 2,
        "assistant_reference_actions": 3,
        "baseline_order": [
            "intentcap_reference_events",
            "task_reference_tools",
            "domain_assistant_regular",
        ],
        "baselines": {
            "intentcap_reference_events": {
                "description": "oracle",
                "assistant_reference_actions": 3,
                "covered_assistant_reference_actions": 3,
                "exposed_tool_slots_total": 3,
                "control_provenance_checked": True,
                "event_id_checked": True,
                "argument_values_constrained": True,
            },
            "task_reference_tools": {
                "description": "task unique tools",
                "assistant_reference_actions": 3,
                "covered_assistant_reference_actions": 3,
                "exposed_tool_slots_total": 2,
                "control_provenance_checked": False,
                "event_id_checked": False,
                "argument_values_constrained": True,
            },
            "domain_assistant_regular": {
                "description": "domain ACL",
                "assistant_reference_actions": 3,
                "covered_assistant_reference_actions": 3,
                "exposed_tool_slots_total": 6,
                "control_provenance_checked": False,
                "event_id_checked": False,
                "argument_values_constrained": False,
            },
        },
    }
