import scripts.score_tau2_invalid_reference_oracle as scorer


def test_invalid_reference_only_task_becomes_adjusted_action_env_pass():
    residual_rows = [
        {
            "source_run_id": "R057",
            "domain": "retail",
            "task_id": "2",
            "reference_actions": "11",
            "executed_reference_actions": "10",
            "missing_reference_actions": "1",
            "tool_oracle_pass": "False",
            "all_reference_actions_executed": "False",
            "action_reward": "0.0",
            "env_reward": "1.0",
        }
    ]
    feasibility_rows = [
        {
            "domain": "retail",
            "task_id": "2",
            "feasibility": "invalid_schema_example_reference",
        }
    ]

    rows = scorer.score_task_rows(
        run_id="RTEST",
        residual_rows=residual_rows,
        feasibility_rows=feasibility_rows,
    )

    assert rows[0]["db_feasible_reference_actions"] == 10
    assert rows[0]["missing_db_feasible_reference_actions"] == 0
    assert rows[0]["db_feasible_reference_complete"] is True
    assert rows[0]["adjusted_action_env_pass"] is True
    assert rows[0]["adjusted_category"] == "invalid_reference_only"


def test_reward_failure_remains_failed_after_feasible_references_execute():
    residual_rows = [
        {
            "source_run_id": "R057",
            "domain": "telecom",
            "task_id": "hard",
            "reference_actions": "1",
            "executed_reference_actions": "1",
            "missing_reference_actions": "0",
            "tool_oracle_pass": "False",
            "all_reference_actions_executed": "True",
            "action_reward": "0.0",
            "env_reward": "0.0",
        }
    ]

    rows = scorer.score_task_rows(
        run_id="RTEST",
        residual_rows=residual_rows,
        feasibility_rows=[],
    )

    assert rows[0]["db_feasible_reference_complete"] is True
    assert rows[0]["adjusted_action_env_pass"] is False
    assert rows[0]["adjusted_category"] == "feasible_refs_complete_but_reward_failed"


def test_official_pass_stays_official_pass():
    residual_rows = [
        {
            "source_run_id": "R057",
            "domain": "airline",
            "task_id": "1",
            "reference_actions": "2",
            "executed_reference_actions": "2",
            "missing_reference_actions": "0",
            "tool_oracle_pass": "True",
            "all_reference_actions_executed": "True",
            "action_reward": "1.0",
            "env_reward": "1.0",
        }
    ]

    rows = scorer.score_task_rows(
        run_id="RTEST",
        residual_rows=residual_rows,
        feasibility_rows=[],
    )

    assert rows[0]["official_tool_oracle_pass"] is True
    assert rows[0]["adjusted_action_env_pass"] is True
    assert rows[0]["adjusted_category"] == "official_pass"
