import scripts.analyze_tau2_runtime_evidence_candidates as analyzer


def _base_record(steps, action_rows=None):
    return {
        "domain": "retail",
        "task_id": "t",
        "reference_actions": [
            {
                "event_id": "retail:t:0",
                "tool": "get_user_details",
                "arguments": {"user_id": "u1"},
            },
            {
                "event_id": "retail:t:1",
                "tool": "get_order_details",
                "arguments": {"order_id": "#W1"},
            },
            {
                "event_id": "retail:t:2",
                "tool": "modify_pending_order_items",
                "arguments": {
                    "order_id": "#W1",
                    "item_ids": ["old"],
                    "new_item_ids": ["new"],
                },
            },
        ],
        "action_rows": action_rows or [],
        "task_row": {
            "tool_oracle_pass": False,
            "all_reference_actions_executed": False,
            "action_reward": 0.0,
            "env_reward": 0.0,
        },
        "stepwise": {"steps": steps},
    }


def test_ranked_top_wrong_when_correct_next_candidate_exists():
    record = _base_record(
        [
            {
                "step": 1,
                "runtime_evidence_lease_hints": [
                    {
                        "tool": "get_user_details",
                        "arguments": {"user_id": "wrong"},
                        "complete_arguments": True,
                        "rank_score": 90,
                    },
                    {
                        "tool": "get_user_details",
                        "arguments": {"user_id": "u1"},
                        "complete_arguments": True,
                        "rank_score": 50,
                    },
                ],
                "model_calls": [
                    {
                        "tool": "get_user_details",
                        "arguments": {
                            "_intentcap_synthesized_from_ranked_runtime_evidence_hint": True,
                            "user_id": "wrong",
                        },
                    }
                ],
                "new_action_rows": [
                    {
                        "model_tool": "get_user_details",
                        "model_args_json": '{"user_id": "wrong"}',
                        "executed": True,
                        "bound_reference_event_id": "",
                    }
                ],
            }
        ]
    )

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["step_rows"][0]["has_exact_next_reference_candidate"] is True
    assert result["step_rows"][0]["top_candidate_correctness"] == "same_tool_wrong_args"
    assert result["step_rows"][0]["fallback_missed_exact_next_reference"] is True
    assert result["task_row"]["steps_with_correct_candidate_but_top_wrong"] == 1
    assert result["task_row"]["proof_complete_non_reference_or_wrong_arg_candidates"] == 1


def test_exact_future_and_already_executed_reference_labels():
    record = _base_record(
        [
            {
                "step": 1,
                "runtime_evidence_lease_hints": [
                    {
                        "tool": "get_user_details",
                        "arguments": {"user_id": "u1"},
                        "complete_arguments": True,
                        "rank_score": 70,
                    },
                    {
                        "tool": "modify_pending_order_items",
                        "arguments": {
                            "order_id": "#W1",
                            "item_ids": ["old"],
                            "new_item_ids": ["new"],
                        },
                        "complete_arguments": True,
                        "rank_score": 60,
                    },
                ],
                "model_calls": [],
                "new_action_rows": [],
            }
        ],
        action_rows=[
            {
                "round": "initial",
                "executed": True,
                "bound_reference_event_id": "retail:t:0",
            }
        ],
    )

    result = analyzer.analyze_task_record("RTEST", record)
    classes = {row["tool"]: row["candidate_correctness"] for row in result["candidate_rows"]}

    assert classes["get_user_details"] == "exact_already_executed_reference"
    assert classes["modify_pending_order_items"] == "exact_future_reference"
    assert result["step_rows"][0]["has_exact_next_reference_candidate"] is False
    assert result["step_rows"][0]["has_any_exact_reference_candidate"] is True


def test_underproven_value_and_proof_probe_statuses():
    record = _base_record(
        [
            {
                "step": 1,
                "runtime_evidence_lease_hints": [
                    {
                        "tool": "get_order_details",
                        "arguments": {"order_id": "#W1"},
                        "complete_arguments": True,
                        "rank_score": 80,
                        "proof_probe": True,
                    },
                    {
                        "tool": "modify_pending_order_items",
                        "arguments": {
                            "order_id": "#W1",
                            "item_ids": ["old"],
                            "new_item_ids": ["new"],
                        },
                        "complete_arguments": True,
                        "rank_score": 70,
                        "value_proof": {"required": True, "complete": False},
                    },
                ],
                "model_calls": [],
                "new_action_rows": [],
            }
        ],
        action_rows=[
            {
                "round": "initial",
                "executed": True,
                "bound_reference_event_id": "retail:t:0",
            }
        ],
    )

    result = analyzer.analyze_task_record("RTEST", record)
    by_tool = {row["tool"]: row for row in result["candidate_rows"]}

    assert by_tool["get_order_details"]["proof_status"] == "proof_probe_complete"
    assert by_tool["get_order_details"]["proof_complete"] is True
    assert by_tool["modify_pending_order_items"]["proof_status"] == "underproven_value"
    assert by_tool["modify_pending_order_items"]["proof_complete"] is False


def test_summary_precision_metrics_are_computed():
    record = _base_record(
        [
            {
                "step": 1,
                "runtime_evidence_lease_hints": [
                    {
                        "tool": "get_user_details",
                        "arguments": {"user_id": "u1"},
                        "complete_arguments": True,
                        "rank_score": 90,
                    }
                ],
                "model_calls": [
                    {
                        "tool": "get_user_details",
                        "arguments": {
                            "_intentcap_synthesized_from_ranked_runtime_evidence_hint": True,
                            "user_id": "u1",
                        },
                    }
                ],
                "new_action_rows": [
                    {
                        "model_tool": "get_user_details",
                        "model_args_json": '{"user_id": "u1"}',
                        "executed": True,
                        "bound_reference_event_id": "retail:t:0",
                    }
                ],
            }
        ]
    )

    result = analyzer._summary(
        run_id="RTEST",
        run_dir=analyzer.Path("unused"),
        source_run_id="RSRC",
        saved_summary={},
        candidate_rows=analyzer.analyze_task_record("RSRC", record)["candidate_rows"],
        step_rows=analyzer.analyze_task_record("RSRC", record)["step_rows"],
        task_rows=[analyzer.analyze_task_record("RSRC", record)["task_row"]],
    )

    assert result["top1_exact_next_reference_precision"] == 1.0
    assert result["ranked_fallback_exact_next_reference_precision"] == 1.0
    assert result["proof_complete_false_positive_rate"] == 0.0
