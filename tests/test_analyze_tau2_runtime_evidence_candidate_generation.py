from pathlib import Path

import scripts.analyze_tau2_runtime_evidence_candidate_generation as analyzer


def reference(tool="lookup", args=None, event_id="event:1"):
    return {"tool": tool, "arguments": args or {"id": "A"}, "event_id": event_id}


def step_payload(*, tools=("lookup",), previous=None, task=None, runtime_hints=None):
    return {
        "step": 1,
        "prompt_payload": {
            "available_tools": [{"name": tool} for tool in tools],
            "previous_gateway_results": previous or [],
            "task": task or {},
            "active_compiler_lease_hints": [],
        },
        "runtime_evidence_lease_hints": runtime_hints or [],
        "new_action_rows": [],
    }


def candidate(correctness, tool="lookup"):
    return {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "step": "1",
        "rank_position": "1",
        "tool": tool,
        "candidate_correctness": correctness,
    }


def analyze(step, candidates, ref=None):
    record = {"domain": "demo", "task_id": "1"}
    return analyzer.analyze_step(
        "RTEST",
        record,
        step,
        candidates,
        references=[ref or reference()],
        executed_ids_before=set(),
        feasibility_by_event={},
        run_dir=Path("."),
    )


def test_existing_exact_next_candidate_is_not_generation_gap():
    row = analyze(
        step_payload(previous=[{"tool_result_preview": "A"}]),
        [candidate("exact_next_reference")],
    )

    assert row["generation_gap_class"] == "existing_exact_next_candidate"
    assert row["generator_upper_bound_exact_next_possible"] is True


def test_runtime_evidence_generation_gap_when_tool_and_prior_result_argument_visible():
    row = analyze(
        step_payload(
            previous=[{"tool_result_preview": '{"id":"A"}'}],
            runtime_hints=[
                {"tool": "lookup", "arguments": {"id": "B"}, "complete_arguments": True}
            ],
        ),
        [candidate("same_tool_wrong_args")],
    )

    assert row["generation_gap_class"] == "runtime_evidence_generation_gap"
    assert row["runtime_evidence_upper_bound_exact_next_possible"] is True


def test_task_text_generation_gap_is_not_runtime_evidence_gap():
    row = analyze(
        step_payload(task={"known": "A"}),
        [candidate("same_tool_wrong_args")],
    )

    assert row["generation_gap_class"] == "task_text_candidate_generation_gap"
    assert row["generator_upper_bound_exact_next_possible"] is True
    assert row["runtime_evidence_upper_bound_exact_next_possible"] is False


def test_tool_and_argument_visibility_failures_are_separated():
    hidden_tool = analyze(
        step_payload(tools=("other",), previous=[{"tool_result_preview": "A"}]),
        [candidate("non_reference_tool", tool="other")],
    )
    missing_arg = analyze(
        step_payload(tools=("lookup",), previous=[{"tool_result_preview": "B"}]),
        [candidate("same_tool_wrong_args")],
    )

    assert hidden_tool["generation_gap_class"] == "tool_exposure_gap"
    assert missing_arg["generation_gap_class"] == "argument_evidence_gap"


def test_invalid_reference_is_separated_from_argument_gap():
    record = {"domain": "demo", "task_id": "1"}
    row = analyzer.analyze_step(
        "RTEST",
        record,
        step_payload(tools=("lookup",), previous=[{"tool_result_preview": "B"}]),
        [candidate("same_tool_wrong_args")],
        references=[reference(event_id="event:bad")],
        executed_ids_before=set(),
        feasibility_by_event={"event:bad": "invalid_schema_example_reference"},
        run_dir=Path("."),
    )

    assert row["generation_gap_class"] == "invalid_exact_next_reference"
    assert row["db_feasible_generator_upper_bound_exact_next_possible"] is False
