import scripts.analyze_tau2_task_gateway_mismatches as analyzer


def test_classify_exact_executed_and_same_tool_wrong_args():
    record = {
        "domain": "mock",
        "task_id": "t",
        "reference_actions": [
            {
                "event_id": "mock:t:create_1",
                "tool": "create_task",
                "arguments": {"title": "Expected", "user_id": "u1"},
            }
        ],
    }

    exact = analyzer.classify_action_row(
        run_id="RTEST",
        record=record,
        references=record["reference_actions"],
        action_row={
            "round": "initial",
            "index": 0,
            "model_tool": "create_task",
            "model_args_json": '{"title": "Expected", "user_id": "u1"}',
            "bound_reference_event_id": "mock:t:create_1",
            "gateway_allowed": True,
            "executed": True,
            "gateway_reason": "lease matched",
        },
    )
    wrong_args = analyzer.classify_action_row(
        run_id="RTEST",
        record=record,
        references=record["reference_actions"],
        action_row={
            "round": "feedback_1",
            "index": 1,
            "model_tool": "create_task",
            "model_args_json": '{"title": "Wrong"}',
            "bound_reference_event_id": "",
            "gateway_allowed": False,
            "executed": False,
            "gateway_reason": "no matching lease",
        },
    )

    assert exact["category"] == "exact_executed"
    assert wrong_args["category"] == "off_lease_same_tool_wrong_args"
    assert wrong_args["arg_missing_keys"] == "user_id"
    assert wrong_args["arg_wrong_value_keys"] == "title"


def test_classify_wrong_tool_and_repeated_reference_args():
    references = [
        {
            "event_id": "mock:t:create_1",
            "tool": "create_task",
            "arguments": {"title": "Expected"},
        }
    ]
    record = {"domain": "mock", "task_id": "t", "reference_actions": references}

    wrong_tool = analyzer.classify_action_row(
        run_id="RTEST",
        record=record,
        references=references,
        action_row={
            "round": "step_1",
            "index": 0,
            "model_tool": "delete_task",
            "model_args_json": '{"title": "Expected"}',
            "bound_reference_event_id": "",
            "gateway_allowed": False,
            "executed": False,
            "gateway_reason": "no matching lease",
        },
    )
    repeated = analyzer.classify_action_row(
        run_id="RTEST",
        record=record,
        references=references,
        action_row={
            "round": "step_2",
            "index": 1,
            "model_tool": "create_task",
            "model_args_json": '{"title": "Expected"}',
            "bound_reference_event_id": "",
            "gateway_allowed": False,
            "executed": False,
            "gateway_reason": "no matching lease",
        },
    )

    assert wrong_tool["category"] == "off_lease_wrong_or_hallucinated_tool"
    assert repeated["category"] == "off_lease_repeated_or_consumed_exact_args"


def test_analyze_task_record_summarizes_categories():
    record = {
        "domain": "mock",
        "task_id": "t",
        "reference_actions": [
            {
                "event_id": "mock:t:create_1",
                "tool": "create_task",
                "arguments": {"title": "Expected"},
            }
        ],
        "task_row": {
            "all_reference_actions_executed": True,
            "tool_oracle_pass": True,
        },
        "action_rows": [
            {
                "round": "initial",
                "index": 0,
                "model_tool": "create_task",
                "model_args_json": '{"title": "Expected"}',
                "bound_reference_event_id": "mock:t:create_1",
                "gateway_allowed": True,
                "executed": True,
                "gateway_reason": "lease matched",
            },
            {
                "round": "feedback_1",
                "index": 1,
                "model_tool": "delete_task",
                "model_args_json": '{"title": "Expected"}',
                "bound_reference_event_id": "",
                "gateway_allowed": False,
                "executed": False,
                "gateway_reason": "no matching lease",
            },
        ],
    }

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["task_row"]["model_calls"] == 2
    assert result["task_row"]["exact_executed_calls"] == 1
    assert result["task_row"]["off_lease_calls"] == 1
    assert result["task_row"]["wrong_or_hallucinated_tool_calls"] == 1
