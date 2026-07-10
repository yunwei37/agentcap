import importlib.util
import json
import sys
from pathlib import Path


def _load_runner():
    root = Path(__file__).parents[1]
    for path in (root / "src", root / "scripts"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    script = root / "scripts" / "run_closed_loop_recovery_suite.py"
    spec = importlib.util.spec_from_file_location("run_closed_loop_recovery_suite", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload_from_prompt_path(command):
    prompt_path = Path(command[command.index("-f") + 1])
    prompt = prompt_path.read_text()
    payload_text = prompt.split("Input JSON:\n", 1)[1].split("\nOutput JSON:", 1)[0]
    return json.loads(payload_text)


def _payload_from_prompt(prompt):
    payload_text = prompt.split("Input JSON:\n", 1)[1].split("\nOutput JSON:", 1)[0]
    return json.loads(payload_text)


def _expected_event_runner(command, timeout_seconds):
    del timeout_seconds
    payload = _payload_from_prompt_path(command)
    expected = payload["candidate_events"][1]["id"]
    return json.dumps({"action": "call", "event_id": expected}), "", 0, 0.01


def _initial_expected_then_abort_runner(command, timeout_seconds):
    del timeout_seconds
    payload = _payload_from_prompt_path(command)
    if "gateway_feedback" in payload:
        return json.dumps(payload["abort_json"]), "", 0, 0.01
    expected = payload["candidate_events"][1]["id"]
    return json.dumps({"action": "call", "event_id": expected}), "", 0, 0.01


def test_force_initial_feedback_recovers_to_allowed_alternatives(tmp_path):
    runner = _load_runner()
    suite_path = Path(__file__).parents[1] / "examples" / "closed_loop_recovery_suite.json"

    result = runner.run_experiment(
        suite_path=suite_path,
        output_dir=tmp_path / "out",
        run_id="test",
        initial_strategy="force-initial-event",
        feedback_rounds=1,
        dry_run=False,
        runner=_expected_event_runner,
    )
    summary = result["summary"]

    assert summary["tasks"] == 6
    assert summary["initial_gateway_blocked_unsafe"] == 6
    assert summary["initial_llm_only_unsafe"] == 6
    assert summary["initial_object_only_would_allow"] == 6
    assert summary["feedback_attempts"] == 6
    assert summary["feedback_parse_success"] == 6
    assert summary["recovered_to_allowed_alternative"] == 6
    assert summary["recovered_to_safe_abort"] == 0
    assert summary["final_correct_executes"] == 6
    assert summary["final_dangerous_executes"] == 0
    assert summary["callable_invocations"] == 6
    assert summary["recovery_rate_to_allowed_alternative"] == 1.0
    assert summary["recovery_rate_to_safe_outcome"] == 1.0


def test_blinded_candidate_prompt_hides_semantic_ids_and_recovers(tmp_path):
    runner = _load_runner()
    suite_path = Path(__file__).parents[1] / "examples" / "closed_loop_recovery_suite.json"
    suite = json.loads(suite_path.read_text())
    task = suite["tasks"][0]
    prompt_view = runner._prompt_view(task, "blinded")

    prompt = runner.build_prompt(task, prompt_view=prompt_view)
    payload_text = prompt.split("Input JSON:\n", 1)[1].split("\nOutput JSON:", 1)[0]
    payload = json.loads(payload_text)

    assert [candidate["id"] for candidate in payload["candidate_events"]] == [
        "candidate_1",
        "candidate_2",
    ]
    assert payload["candidate_events"][0]["event"]["id"] == "candidate_1"
    assert "pdf_issue_attacker_repo" not in prompt
    assert "pdf_issue_authorized_repo" not in prompt
    assert "Untrusted PDF chooses a different repository" not in prompt
    assert "User-selected repository and trusted summary" not in prompt

    result = runner.run_experiment(
        suite_path=suite_path,
        output_dir=tmp_path / "out",
        run_id="test",
        initial_strategy="force-initial-event",
        candidate_prompt_mode="blinded",
        feedback_rounds=1,
        dry_run=False,
        runner=_expected_event_runner,
    )
    summary = result["summary"]
    rows = result["rows"]

    assert summary["candidate_prompt_mode"] == "blinded"
    assert summary["feedback_prompt_mode"] == "structured"
    assert summary["recovered_to_allowed_alternative"] == 6
    assert summary["final_dangerous_executes"] == 0
    assert {row["candidate_prompt_mode"] for row in rows} == {"blinded"}
    assert {row["feedback_prompt_mode"] for row in rows} == {"structured"}
    assert rows[0]["feedback_event_id"] == task["expected_event_id"]


def test_llm_initial_correct_path_skips_feedback(tmp_path):
    runner = _load_runner()
    suite_path = Path(__file__).parents[1] / "examples" / "closed_loop_recovery_suite.json"

    result = runner.run_experiment(
        suite_path=suite_path,
        output_dir=tmp_path / "out",
        run_id="test",
        initial_strategy="llm",
        feedback_rounds=1,
        dry_run=False,
        runner=_initial_expected_then_abort_runner,
    )
    summary = result["summary"]

    assert summary["tasks"] == 6
    assert summary["initial_correct_executes"] == 6
    assert summary["initial_gateway_blocked_unsafe"] == 0
    assert summary["feedback_attempts"] == 0
    assert summary["final_correct_executes"] == 6
    assert summary["final_dangerous_executes"] == 0


def test_feedback_prompt_preserves_gateway_authority(tmp_path):
    runner = _load_runner()
    suite_path = Path(__file__).parents[1] / "examples" / "closed_loop_recovery_suite.json"
    suite = json.loads(suite_path.read_text())
    task = suite["tasks"][0]
    initial = {"action": "call", "event_id": task["initial_event_id"]}
    trace = runner._trace_for_task(task)
    tools = runner._tool_registry(trace, [])
    initial_eval = runner.evaluate_choice(
        task=task,
        parsed=initial,
        trace=trace,
        tools=tools,
        expected_event_id=task["expected_event_id"],
    )

    prompt = runner.build_feedback_prompt(task, initial, initial_eval)
    payload = _payload_from_prompt(prompt)

    assert payload["gateway_feedback"]["blocked_event_id"] == task["initial_event_id"]
    assert payload["gateway_feedback"]["reason"] == initial_eval["gateway_reason"]
    assert payload["feedback_prompt_mode"] == "structured"
    assert "does not grant authority" not in prompt
    assert "Do not widen scope" in payload["instruction"]
    assert payload["leases"] == task["leases"]
    assert payload["untrusted_context"] == task["untrusted_context"]


def test_feedback_prompt_ablation_modes_hide_denial_detail(tmp_path):
    runner = _load_runner()
    suite_path = Path(__file__).parents[1] / "examples" / "closed_loop_recovery_suite.json"
    suite = json.loads(suite_path.read_text())
    task = suite["tasks"][0]
    initial = {"action": "call", "event_id": task["initial_event_id"]}
    trace = runner._trace_for_task(task)
    tools = runner._tool_registry(trace, [])
    initial_eval = runner.evaluate_choice(
        task=task,
        parsed=initial,
        trace=trace,
        tools=tools,
        expected_event_id=task["expected_event_id"],
    )

    generic_prompt = runner.build_feedback_prompt(
        task,
        initial,
        initial_eval,
        feedback_prompt_mode="generic",
    )
    generic_payload = _payload_from_prompt(generic_prompt)
    assert generic_payload["feedback_prompt_mode"] == "generic"
    assert generic_payload["gateway_feedback"]["blocked_event_id"] == task["initial_event_id"]
    assert generic_payload["gateway_feedback"]["reason"] == "blocked_by_gateway"
    assert initial_eval["gateway_reason"] not in generic_prompt

    candidate_only_prompt = runner.build_feedback_prompt(
        task,
        initial,
        initial_eval,
        feedback_prompt_mode="candidate-only",
    )
    candidate_only_payload = _payload_from_prompt(candidate_only_prompt)
    assert candidate_only_payload["feedback_prompt_mode"] == "candidate-only"
    assert "gateway_feedback" not in candidate_only_payload
    assert "previous_model_json" not in candidate_only_payload
    assert task["initial_event_id"] in candidate_only_prompt
    assert initial_eval["gateway_reason"] not in candidate_only_prompt


def test_feedback_prompt_mode_is_recorded_in_rows_and_summary(tmp_path):
    runner = _load_runner()
    suite_path = Path(__file__).parents[1] / "examples" / "closed_loop_recovery_suite.json"

    result = runner.run_experiment(
        suite_path=suite_path,
        output_dir=tmp_path / "out",
        run_id="test",
        initial_strategy="force-initial-event",
        candidate_prompt_mode="blinded",
        feedback_prompt_mode="candidate-only",
        feedback_rounds=1,
        dry_run=False,
        runner=_expected_event_runner,
    )
    summary = result["summary"]
    rows = result["rows"]

    assert summary["candidate_prompt_mode"] == "blinded"
    assert summary["feedback_prompt_mode"] == "candidate-only"
    assert summary["recovered_to_allowed_alternative"] == 6
    assert {row["feedback_prompt_mode"] for row in rows} == {"candidate-only"}


def test_multiboundary_suite_records_surface_and_owner_metadata(tmp_path):
    runner = _load_runner()
    suite_path = (
        Path(__file__).parents[1]
        / "examples"
        / "closed_loop_multiboundary_recovery_suite.json"
    )

    result = runner.run_experiment(
        suite_path=suite_path,
        output_dir=tmp_path / "out",
        run_id="test",
        initial_strategy="force-initial-event",
        candidate_prompt_mode="blinded",
        feedback_prompt_mode="structured",
        feedback_rounds=1,
        dry_run=False,
        runner=_expected_event_runner,
    )
    summary = result["summary"]
    rows = result["rows"]

    assert summary["tasks"] == 8
    assert summary["surfaces_covered"] == 6
    assert summary["owner_classes_covered"] == ["agent", "env", "instruction", "tool"]
    assert summary["initial_gateway_blocked_unsafe"] == 8
    assert summary["initial_llm_only_unsafe"] == 8
    assert summary["initial_object_only_would_allow"] == 8
    assert summary["feedback_attempts"] == 8
    assert summary["recovered_to_allowed_alternative"] == 8
    assert summary["final_correct_executes"] == 8
    assert summary["final_dangerous_executes"] == 0
    assert summary["surface_counts"]["mcp_broker"] == 1
    assert summary["surface_counts"]["env_side_effect"] == 1
    assert summary["surface_counts"]["prompt_builder"] == 2
    assert summary["owner_boundary_counts"]["env_to_agent"] == 3
    assert summary["initial_blocks_by_surface"]["mcp_broker"] == 1
    assert summary["recovered_to_allowed_alternative_by_surface"]["env_side_effect"] == 1
    assert {row["surface"] for row in rows} >= {
        "approval_gateway",
        "delegation_monitor",
        "env_side_effect",
        "mcp_broker",
        "prompt_builder",
        "skill_cmd_gateway",
    }
