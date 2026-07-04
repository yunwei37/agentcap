import scripts.analyze_tau2_residual_completion as analyzer


def test_executed_prefix_ignores_internal_intentcap_args():
    references = [
        {
            "event_id": "mock:t:1",
            "tool": "get_order",
            "arguments": {"order_id": "o1"},
        },
        {
            "event_id": "mock:t:2",
            "tool": "get_product",
            "arguments": {"product_id": "p1"},
        },
    ]
    record = {
        "model_calls": [
            {
                "tool": "get_order",
                "arguments": {
                    "order_id": "o1",
                    "_intentcap_synthesized_from_hint": True,
                },
            },
            {"tool": "get_user", "arguments": {"user_id": "u1"}},
        ]
    }

    assert analyzer.executed_prefix_actions(record, references) == 1


def test_missing_reference_visibility_uses_saved_state_grounded_hints_only():
    record = {
        "domain": "retail",
        "task_id": "t",
        "reference_actions": [
            {
                "event_id": "retail:t:1",
                "tool": "get_order",
                "arguments": {"order_id": "o1"},
            },
            {
                "event_id": "retail:t:2",
                "tool": "exchange",
                "arguments": {
                    "order_id": "o1",
                    "item_ids": ["i1"],
                    "payment_method_id": "pm1",
                },
            },
        ],
        "action_rows": [
            {
                "executed": True,
                "bound_reference_event_id": "retail:t:1",
            }
        ],
        "model_calls": [{"tool": "get_order", "arguments": {"order_id": "o1"}}],
        "task_row": {
            "model_calls": 1,
            "tool_oracle_pass": False,
            "all_reference_actions_executed": False,
            "exact_sequence_match": False,
            "action_reward": 0.0,
            "env_reward": 0.0,
        },
        "stepwise": {
            "steps": [
                {
                    "state_grounded_arg_hints": [
                        {
                            "tool": "exchange",
                            "arguments": {"order_id": "o1", "item_ids": ["i1"]},
                            "complete_arguments": False,
                        }
                    ]
                }
            ]
        },
    }

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["task_row"]["missing_reference_actions"] == 1
    assert result["task_row"]["missing_partial_visible_actions"] == 1
    assert result["task_row"]["residual_category"] == "missing_partial_visible_actions"
    assert result["missing_rows"][0]["grounded_keys"] == "item_ids|order_id"
    assert result["missing_rows"][0]["hidden_keys"] == "payment_method_id"


def test_complete_visible_missing_action_takes_priority_over_partial():
    record = {
        "domain": "retail",
        "task_id": "t",
        "reference_actions": [
            {
                "event_id": "retail:t:1",
                "tool": "get_product",
                "arguments": {"product_id": "p1"},
            }
        ],
        "action_rows": [],
        "model_calls": [],
        "task_row": {
            "model_calls": 0,
            "tool_oracle_pass": False,
            "all_reference_actions_executed": False,
            "exact_sequence_match": False,
            "action_reward": 0.0,
            "env_reward": 0.0,
        },
        "stepwise": {
            "steps": [
                {
                    "state_grounded_arg_hints": [
                        {
                            "tool": "get_product",
                            "arguments": {"product_id": "p1"},
                            "complete_arguments": True,
                        }
                    ]
                }
            ]
        },
    }

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["task_row"]["missing_complete_visible_actions"] == 1
    assert result["task_row"]["residual_category"] == "missing_complete_visible_actions"
    assert result["missing_rows"][0]["visibility"] == "complete_visible"


def test_all_references_executed_reward_failure_has_distinct_category():
    record = {
        "domain": "telecom",
        "task_id": "t",
        "reference_actions": [
            {
                "event_id": "telecom:t:1",
                "tool": "enable_roaming",
                "arguments": {"customer_id": "c1", "line_id": "l1"},
            }
        ],
        "action_rows": [
            {
                "executed": True,
                "bound_reference_event_id": "telecom:t:1",
            }
        ],
        "model_calls": [
            {
                "tool": "enable_roaming",
                "arguments": {"customer_id": "c1", "line_id": "l1"},
            }
        ],
        "task_row": {
            "model_calls": 1,
            "tool_oracle_pass": False,
            "all_reference_actions_executed": True,
            "exact_sequence_match": True,
            "action_reward": 0.0,
            "env_reward": 0.0,
        },
        "stepwise": {"steps": []},
    }

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["task_row"]["missing_reference_actions"] == 0
    assert (
        result["task_row"]["residual_category"]
        == "all_references_executed_but_reward_failed"
    )
