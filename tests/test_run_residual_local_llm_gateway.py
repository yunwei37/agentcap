import importlib.util
import json
from pathlib import Path


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_residual_local_llm_gateway.py"
    spec = importlib.util.spec_from_file_location("run_residual_local_llm_gateway", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _call_everything_runner(command, timeout_seconds):
    del timeout_seconds
    prompt_path = Path(command[command.index("-f") + 1])
    prompt = prompt_path.read_text()
    payload_text = prompt.split("Input JSON:\n", 1)[1].split("\nOutput JSON:", 1)[0]
    payload = json.loads(payload_text)
    return json.dumps(payload["required_call_json"]), "", 0, 0.01


def _call_then_abort_on_feedback_runner(command, timeout_seconds):
    del timeout_seconds
    prompt_path = Path(command[command.index("-f") + 1])
    prompt = prompt_path.read_text()
    payload_text = prompt.split("Input JSON:\n", 1)[1].split("\nOutput JSON:", 1)[0]
    payload = json.loads(payload_text)
    if "gateway_feedback" in payload:
        return json.dumps(payload["required_abort_json"]), "", 0, 0.01
    return json.dumps(payload["required_call_json"]), "", 0, 0.01


def test_residual_local_llm_probe_routes_model_calls_through_gateway(tmp_path):
    runner = _load_runner()
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "residual_closest_baseline_suite.json"
    )

    result = runner.run_experiment(
        trace_path=trace_path,
        output_dir=tmp_path,
        run_id="test",
        dry_run=False,
        runner=_call_everything_runner,
    )
    summary = result["summary"]

    assert summary["events"] == 7
    assert summary["parse_success"] == 7
    assert summary["model_calls"] == 7
    assert summary["reference_allowed"] == 1
    assert summary["reference_denied"] == 6
    assert summary["llm_only_unsafe_calls"] == 6
    assert summary["gateway_allowed"] == 1
    assert summary["gateway_blocked"] == 6
    assert summary["callable_invocations"] == 1
    assert summary["dangerous_executes"] == 0
    assert summary["outcome_counts"] == {
        "correct_execute": 1,
        "gateway_blocked_unsafe": 6,
    }


def test_residual_workflow_local_llm_probe_routes_calls_through_gateway(tmp_path):
    runner = _load_runner()
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "residual_workflow_suite.json"
    )

    result = runner.run_experiment(
        trace_path=trace_path,
        output_dir=tmp_path,
        run_id="test",
        dry_run=False,
        runner=_call_everything_runner,
    )
    summary = result["summary"]

    assert summary["events"] == 8
    assert summary["parse_success"] == 8
    assert summary["model_calls"] == 8
    assert summary["reference_allowed"] == 2
    assert summary["reference_denied"] == 6
    assert summary["llm_only_unsafe_calls"] == 6
    assert summary["gateway_allowed"] == 2
    assert summary["gateway_blocked"] == 6
    assert summary["callable_invocations"] == 2
    assert summary["dangerous_executes"] == 0
    assert summary["outcome_counts"] == {
        "correct_execute": 2,
        "gateway_blocked_unsafe": 6,
    }


def test_residual_workflow_feedback_recovers_blocked_unsafe_calls(tmp_path):
    runner = _load_runner()
    trace_path = (
        Path(__file__).parents[1]
        / "examples"
        / "residual_workflow_suite.json"
    )

    result = runner.run_experiment(
        trace_path=trace_path,
        output_dir=tmp_path,
        run_id="test",
        feedback_rounds=1,
        dry_run=False,
        runner=_call_then_abort_on_feedback_runner,
    )
    summary = result["summary"]

    assert summary["events"] == 8
    assert summary["model_calls"] == 8
    assert summary["llm_only_unsafe_calls"] == 6
    assert summary["gateway_allowed"] == 2
    assert summary["gateway_blocked"] == 6
    assert summary["feedback_attempts"] == 6
    assert summary["feedback_parse_success"] == 6
    assert summary["recovered_after_gateway_feedback"] == 6
    assert summary["final_model_calls"] == 2
    assert summary["final_model_aborts"] == 6
    assert summary["final_gateway_allowed"] == 2
    assert summary["final_gateway_blocked"] == 0
    assert summary["callable_invocations"] == 2
    assert summary["dangerous_executes"] == 0
    assert summary["final_dangerous_executes"] == 0
    assert summary["final_outcome_counts"] == {
        "correct_abort": 6,
        "correct_execute": 2,
    }
