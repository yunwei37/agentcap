import importlib.util
from pathlib import Path


def _load_aggregate_runner():
    path = Path(__file__).parents[1] / "scripts" / "aggregate_injecagent_cached_outputs_gateway.py"
    spec = importlib.util.spec_from_file_location("aggregate_injecagent_cached_outputs_gateway", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_aggregate_rows_sums_cached_output_gateway_results(tmp_path):
    runner = _load_aggregate_runner()
    zip_path = tmp_path / "results.zip"
    zip_path.write_bytes(b"zip-bytes")
    rows = [
        {
            "model_result_dir": "results/model_a",
            "setting": "base",
            "full_case_coverage": True,
            "cases": 1054,
            "attempted_events": 1200,
            "executed_events": 1054,
            "blocked_events": 146,
            "tool_errors": 0,
            "registered_executed_events": 1054,
            "registered_blocked_events": 146,
            "callable_invocations": 1054,
            "missing_tool_events": 0,
            "counterfactual_attempts": 40,
            "cached_eval_counts": {
                "stage1": {"succ": 106, "unsucc": 900, "invalid": 48},
                "stage2": {"succ": 40, "unsucc": 2, "missing": 502},
            },
            "attempted_event_type_counts": {
                "benchmark_setup_user_tool": 1054,
                "cached_model_attacker_tool_model_stage1": 106,
                "cached_model_attacker_tool_model_stage2_counterfactual": 40,
            },
            "executed_event_type_counts": {"benchmark_setup_user_tool": 1054},
            "blocked_event_type_counts": {
                "cached_model_attacker_tool_model_stage1": 106,
                "cached_model_attacker_tool_model_stage2_counterfactual": 40,
            },
            "executed_mode_counts": {"tool_select": 1054},
            "blocked_mode_counts": {"authorize": 100, "sink_select": 46},
        },
        {
            "model_result_dir": "results/model_b",
            "setting": "enhanced",
            "full_case_coverage": False,
            "cases": 510,
            "attempted_events": 520,
            "executed_events": 510,
            "blocked_events": 10,
            "tool_errors": 0,
            "registered_executed_events": 510,
            "registered_blocked_events": 10,
            "callable_invocations": 510,
            "missing_tool_events": 0,
            "counterfactual_attempts": 0,
            "cached_eval_counts": {
                "stage1": {"succ": 10, "unsucc": 500},
                "stage2": {},
            },
            "attempted_event_type_counts": {
                "benchmark_setup_user_tool": 510,
                "cached_model_attacker_tool_model_stage1": 10,
            },
            "executed_event_type_counts": {"benchmark_setup_user_tool": 510},
            "blocked_event_type_counts": {"cached_model_attacker_tool_model_stage1": 10},
            "executed_mode_counts": {"tool_select": 510},
            "blocked_mode_counts": {"authorize": 10},
        },
    ]

    aggregate = runner.aggregate_rows(
        rows,
        discovered={
            "result_dir_count": 3,
            "complete_result_dir_count": 2,
            "incomplete_result_dir_count": 1,
        },
        results_zip=zip_path,
        settings=["base", "enhanced"],
        include_counterfactual_stage2=True,
        limit_result_dirs=None,
        start_index=0,
        errors=[],
    )

    assert aggregate["processed_result_sets"] == 2
    assert aggregate["settings_seen"] == {"base": 1, "enhanced": 1}
    assert aggregate["totals"]["cases"] == 1564
    assert aggregate["totals"]["blocked_events"] == 156
    assert aggregate["totals"]["callable_invocations"] == 1564
    assert aggregate["cached_eval_counts"]["stage1"] == {
        "invalid": 48,
        "succ": 116,
        "unsucc": 1400,
    }
    assert aggregate["blocked_event_type_counts"] == {
        "cached_model_attacker_tool_model_stage1": 116,
        "cached_model_attacker_tool_model_stage2_counterfactual": 40,
    }
    assert aggregate["incomplete_case_rows"] == [
        {
            "model_result_dir": "results/model_b",
            "setting": "enhanced",
            "cases": 510,
        }
    ]
