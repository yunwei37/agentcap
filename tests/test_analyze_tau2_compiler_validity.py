import importlib.util
import json
import sys
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_tau2_compiler_validity.py"
    spec = importlib.util.spec_from_file_location("analyze_tau2_compiler_validity", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compiler_validity_labels_replay_schema_variants_and_task_loop(tmp_path):
    analyzer = _load_analyzer()
    compiler_dir = tmp_path / "R074"
    non_strict_dir = tmp_path / "R075"
    strict_dir = tmp_path / "R076"
    mismatch_dir = tmp_path / "R080"
    compiler_dir.mkdir()
    non_strict_dir.mkdir()
    strict_dir.mkdir()
    mismatch_dir.mkdir()

    (compiler_dir / "llm_visible_lease_compiler_summary.json").write_text(
        json.dumps(
            {
                "run_id": "R074",
                "tasks_evaluated": 1,
                "assistant_reference_actions": 3,
                "model_lease_slots_total": 2,
                "invalid_tool_slots_total": 1,
            }
        )
    )
    (compiler_dir / "reference_coverage.csv").write_text(
        "\n".join(
            [
                "coverage_class",
                "tool_and_non_eval_json_args",
                "tool_only_runtime_or_broad_args_needed",
                "missing_tool",
            ]
        )
        + "\n"
    )

    (non_strict_dir / "compiler_gateway_replay_summary.json").write_text(
        json.dumps(
            {
                "run_id": "R075",
                "source_run_id": "R074",
                "tasks_evaluated": 1,
                "assistant_reference_actions": 2,
                "active_leases_total": 2,
            }
        )
    )
    (non_strict_dir / "action_results.csv").write_text(
        "\n".join(
            [
                "run_id,domain,task_id,action_id,index,tool,args_json,gateway_allowed,coverage_class,missing_reference_arg_constraints",
                'R075,mock,t0,a0,0,read_user,"{""user_id"": ""u1""}",True,allowed_all_reference_args_constrained,',
                'R075,mock,t0,a1,1,update_order,"{""order_id"": ""o1""}",True,allowed_broad_or_runtime_args,order_id',
            ]
        )
        + "\n"
    )
    (non_strict_dir / "lease_results.csv").write_text(
        "\n".join(
            [
                "run_id,domain,task_id,lease_id,tool,valid_tool,object,constrained_args,broad_or_runtime_args,argument_policy_json",
                'R075,mock,t0,l0,read_user,True,tau2.mock.read_user,user_id,,"{}"',
                'R075,mock,t0,l1,update_order,True,tau2.mock.update_order,,order_id,"{}"',
            ]
        )
        + "\n"
    )

    (strict_dir / "compiler_gateway_replay_summary.json").write_text(
        json.dumps(
            {
                "run_id": "R076",
                "source_run_id": "R074",
                "require_all_tool_args_constrained": True,
                "tasks_evaluated": 1,
                "assistant_reference_actions": 2,
                "active_leases_total": 1,
            }
        )
    )
    (strict_dir / "action_results.csv").write_text(
        "\n".join(
            [
                "run_id,domain,task_id,action_id,index,tool,args_json,gateway_allowed,coverage_class,missing_reference_arg_constraints",
                'R076,mock,t0,a0,0,read_user,"{""user_id"": ""u1""}",True,allowed_all_reference_args_constrained,',
                'R076,mock,t0,a1,1,update_order,"{""order_id"": ""o1""}",False,blocked_broad_or_runtime_policy,',
            ]
        )
        + "\n"
    )
    (strict_dir / "lease_results.csv").write_text(
        "\n".join(
            [
                "run_id,domain,task_id,lease_id,tool,valid_tool,active,inactive_reason,object,constrained_args,broad_or_runtime_args,argument_policy_json",
                'R076,mock,t0,l0,read_user,True,True,,tau2.mock.read_user,user_id,,"{}"',
                'R076,mock,t0,l1,update_order,True,False,broad_or_runtime_args,tau2.mock.update_order,,order_id,"{}"',
            ]
        )
        + "\n"
    )

    (mismatch_dir / "tau2_task_gateway_mismatch_summary.json").write_text(
        json.dumps(
            {
                "run_id": "R080",
                "source_runs": ["R079"],
                "tasks": 1,
                "reference_actions": 2,
                "model_calls": 2,
            }
        )
    )
    (mismatch_dir / "model_call_mismatches.csv").write_text(
        "\n".join(
            [
                "run_id,domain,task_id,round,index,model_tool,category,arg_distance,arg_missing_keys,arg_extra_keys,arg_wrong_value_keys,gateway_allowed,executed,closest_reference_tool",
                "R079,mock,t0,step_1,0,read_user,exact_executed,0,,,,True,True,read_user",
                "R079,mock,t0,step_2,1,delete_user,off_lease_wrong_or_hallucinated_tool,2,user_id,,id,True,True,update_order",
            ]
        )
        + "\n"
    )

    result = analyzer.analyze(
        run_id="TEST",
        compiler_runs=(compiler_dir,),
        replay_runs=(non_strict_dir, strict_dir),
        task_mismatch_runs=(mismatch_dir,),
    )
    summary = result["summary"]

    assert summary["run_id"] == "TEST"
    assert summary["reference_action_label_rows"] == 4
    assert summary["action_label_counts"] == {
        "broad_or_runtime_arg_admitted": 1,
        "broad_or_runtime_arg_blocked": 1,
        "exact_reference_action_covered": 2,
    }
    assert summary["strict_action_label_counts"] == {
        "broad_or_runtime_arg_blocked": 1,
        "exact_reference_action_covered": 1,
    }
    assert summary["non_strict_action_label_counts"] == {
        "broad_or_runtime_arg_admitted": 1,
        "exact_reference_action_covered": 1,
    }
    assert summary["lease_label_counts"] == {
        "broad_or_runtime_active_lease": 1,
        "exact_active_lease": 2,
        "inactive_broad_or_runtime_lease": 1,
    }
    assert summary["task_loop_label_counts"] == {
        "exact_model_call_executed": 1,
        "wrong_or_hallucinated_tool_call": 1,
    }

    run_rows = {(row["run_id"], row["run_kind"]): row for row in result["run_rows"]}
    assert run_rows[("R074", "visible_lease_compiler")]["missing_tool_actions"] == 1
    assert run_rows[("R075", "compiler_gateway_replay")][
        "broad_or_runtime_active_leases"
    ] == 1
    assert run_rows[("R076", "compiler_gateway_replay")][
        "inactive_broad_or_runtime_leases"
    ] == 1
    assert run_rows[("R080", "task_loop_mismatch")][
        "wrong_or_hallucinated_tool_calls"
    ] == 1
    assert "does not run models" in summary["notes"][0]
