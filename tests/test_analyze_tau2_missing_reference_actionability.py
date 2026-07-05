import csv

import scripts.analyze_tau2_missing_reference_actionability as analyzer


def missing_row(event_id="event:1", **overrides):
    row = {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "reference_index": "0",
        "event_id": event_id,
        "tool": "lookup",
        "args_json": '{"id": "A"}',
        "arg_values": "A",
        "complete_compiler_hint_steps": "",
        "partial_compiler_hint_steps": "",
        "tool_visible_steps": "",
        "all_arg_evidence_steps": "",
        "any_arg_evidence_steps": "",
        "task_arg_evidence": "false",
        "missing_arg_values_from_prompt_evidence": "",
        "gap_class": "",
    }
    row.update(overrides)
    return row


def candidate(event_id="event:1", **overrides):
    row = {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "step": "2",
        "rank_position": "1",
        "tool": "lookup",
        "candidate_correctness": "exact_next_reference",
        "exact_reference_event_id": event_id,
        "selected_by_model": "False",
        "selected_by_ranked_fallback": "False",
        "executed": "False",
    }
    row.update(overrides)
    return row


def classify(row, candidates=None, feasibility="valid_visible_reference"):
    grouped = analyzer.group_exact_candidates_by_event(candidates or [])
    return analyzer.classify_missing_row(
        row,
        grouped,
        {row["event_id"]: {"feasibility": feasibility, "source": "test"}},
    )


def test_invalid_reference_takes_priority_over_candidate():
    row = classify(
        missing_row(),
        [candidate(selected_by_model="True")],
        feasibility="invalid_schema_example_reference",
    )

    assert row["actionability_class"] == "invalid_reference"
    assert row["db_feasible"] is False


def test_existing_runtime_exact_candidate_is_selection_gap():
    row = classify(missing_row(), [candidate(selected_by_ranked_fallback="True")])

    assert row["actionability_class"] == "candidate_selection_or_planning_gap"
    assert row["runtime_exact_candidate_count"] == 1
    assert row["runtime_ranked_fallback_steps"] == "2"


def test_complete_compiler_hint_without_candidate_is_hint_execution_gap():
    row = classify(missing_row(complete_compiler_hint_steps="1"))

    assert row["actionability_class"] == "complete_compiler_hint_not_called"


def test_visible_tool_and_arguments_without_candidate_is_generation_gap():
    row = classify(missing_row(tool_visible_steps="1|2", all_arg_evidence_steps="2"))

    assert row["actionability_class"] == "runtime_candidate_generation_gap"
    assert row["next_experiment_target"] == (
        "generate_runtime_candidate_from_visible_tool_and_arguments"
    )


def test_tool_activation_argument_evidence_and_argument_gap_are_separated():
    hidden_tool = classify(missing_row(all_arg_evidence_steps="2"))
    visible_tool = classify(missing_row(tool_visible_steps="1", any_arg_evidence_steps=""))

    assert hidden_tool["actionability_class"] == "tool_activation_gap"
    assert visible_tool["actionability_class"] == "argument_evidence_gap"


def test_no_tool_or_argument_evidence_is_upstream_planning_gap():
    row = classify(missing_row())

    assert row["actionability_class"] == "upstream_planning_gap"


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_analyze_actionability_rolls_up_task_and_reward_residual(tmp_path):
    missing_csv = tmp_path / "missing.csv"
    candidate_csv = tmp_path / "candidates.csv"
    feasibility_csv = tmp_path / "feasibility.csv"
    adjusted_csv = tmp_path / "adjusted.csv"

    write_csv(
        missing_csv,
        [
            missing_row("event:1", tool_visible_steps="1", all_arg_evidence_steps="1"),
            missing_row("event:2"),
        ],
    )
    write_csv(candidate_csv, [candidate("event:2", candidate_correctness="exact_future_reference")])
    write_csv(
        feasibility_csv,
        [
            {
                "event_id": "event:1",
                "feasibility": "valid_visible_reference",
            },
            {
                "event_id": "event:2",
                "feasibility": "valid_visible_reference",
            },
        ],
    )
    write_csv(
        adjusted_csv,
        [
            {
                "source_run_id": "RTEST",
                "domain": "demo",
                "task_id": "1",
                "adjusted_category": "missing_db_feasible_reference_actions",
                "official_reference_actions": "2",
                "invalid_reference_actions": "0",
                "db_feasible_reference_actions": "2",
                "official_executed_reference_actions": "0",
                "executed_db_feasible_reference_actions": "0",
                "official_missing_reference_actions": "2",
                "missing_db_feasible_reference_actions": "2",
                "db_feasible_reference_complete": "False",
                "official_tool_oracle_pass": "False",
                "official_action_reward": "0.0",
                "official_env_reward": "0.0",
                "adjusted_action_env_pass": "False",
            },
            {
                "source_run_id": "RTEST",
                "domain": "demo",
                "task_id": "2",
                "adjusted_category": "feasible_refs_complete_but_reward_failed",
                "official_reference_actions": "1",
                "invalid_reference_actions": "0",
                "db_feasible_reference_actions": "1",
                "official_executed_reference_actions": "1",
                "executed_db_feasible_reference_actions": "1",
                "official_missing_reference_actions": "0",
                "missing_db_feasible_reference_actions": "0",
                "db_feasible_reference_complete": "True",
                "official_tool_oracle_pass": "False",
                "official_action_reward": "1.0",
                "official_env_reward": "0.0",
                "adjusted_action_env_pass": "False",
            },
        ],
    )

    result = analyzer.analyze_actionability(
        missing_csv=missing_csv,
        candidate_csv=candidate_csv,
        feasibility_csv=feasibility_csv,
        adjusted_task_csv=adjusted_csv,
        run_id="RTEST",
    )

    summary = result["summary"]
    assert summary["missing_db_feasible_reference_actions"] == 2
    assert summary["db_feasible_actionability_class_counts"] == {
        "candidate_selection_or_planning_gap": 1,
        "runtime_candidate_generation_gap": 1,
    }
    assert summary["reward_residual_tasks_without_missing_action"] == 1
