import scripts.analyze_tau2_compiler_recall_gap as analyzer


def _base_record(step_payloads):
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
        ],
        "action_rows": [
            {
                "executed": True,
                "bound_reference_event_id": "retail:t:0",
            }
        ],
        "task_row": {
            "tool_oracle_pass": False,
            "all_reference_actions_executed": False,
            "action_reward": 0.0,
            "env_reward": 0.0,
        },
        "stepwise": {
            "steps": [
                {"step": index + 1, "prompt_payload": payload}
                for index, payload in enumerate(step_payloads)
            ]
        },
    }


def test_complete_compiler_hint_missing_call_has_priority():
    record = _base_record(
        [
            {
                "available_tools": [{"name": "get_order_details"}],
                "previous_gateway_results": [],
                "active_compiler_lease_hints": [
                    {
                        "tool": "get_order_details",
                        "arguments": {"order_id": "#W1"},
                        "complete_arguments": True,
                    }
                ],
            }
        ]
    )

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["missing_rows"][0]["gap_class"] == "complete_compiler_hint_not_called"
    assert result["task_row"]["missing_complete_compiler_hint_not_called"] == 1


def test_tool_visible_with_arg_evidence_but_no_complete_hint():
    record = _base_record(
        [
            {
                "available_tools": [{"name": "get_order_details"}],
                "previous_gateway_results": [
                    {
                        "tool": "get_user_details",
                        "tool_result_preview": '{"orders":["#W1"]}',
                    }
                ],
                "active_compiler_lease_hints": [],
            }
        ]
    )

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["missing_rows"][0]["gap_class"] == "tool_visible_arg_evidence_not_called"
    assert result["task_row"]["missing_with_all_arg_evidence"] == 1
    assert result["task_row"]["missing_with_tool_visible"] == 1


def test_arg_evidence_without_tool_visibility_is_compiler_activation_gap():
    record = _base_record(
        [
            {
                "available_tools": [{"name": "get_user_details"}],
                "previous_gateway_results": [
                    {
                        "tool": "get_user_details",
                        "tool_result_preview": '{"orders":["#W1"]}',
                    }
                ],
                "active_compiler_lease_hints": [],
            }
        ]
    )

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["missing_rows"][0]["gap_class"] == "tool_not_visible_arg_evidence"
    assert result["task_row"]["missing_tool_not_visible_arg_evidence"] == 1


def test_tool_visible_without_arg_evidence_is_inference_or_exploration_gap():
    record = _base_record(
        [
            {
                "available_tools": [{"name": "get_order_details"}],
                "previous_gateway_results": [],
                "active_compiler_lease_hints": [],
            }
        ]
    )

    result = analyzer.analyze_task_record("RTEST", record)

    assert result["missing_rows"][0]["gap_class"] == "tool_visible_no_arg_evidence"
    assert result["task_row"]["task_gap_category"] == "tool_visible_no_arg_evidence"


def test_prompt_path_resolves_from_absolute_run_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    run_dir = repo / "results" / "eval" / "R099"
    prompt_path = run_dir / "step_prompts" / "retail_t_step_1.txt"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text(
        'Input JSON:\n'
        '{"available_tools":[{"name":"get_order_details"}],'
        '"previous_gateway_results":[{"tool_result_preview":"{\\"orders\\":[\\"#W1\\"]}"}],'
        '"active_compiler_lease_hints":[]}\n'
        "Output JSON:"
    )
    record = _base_record([])
    record["stepwise"]["steps"] = [
        {
            "step": 1,
            "prompt_path": "results/eval/R099/step_prompts/retail_t_step_1.txt",
        }
    ]
    monkeypatch.chdir(tmp_path)

    result = analyzer.analyze_task_record("RTEST", record, run_dir=run_dir)

    assert result["missing_rows"][0]["gap_class"] == "tool_visible_arg_evidence_not_called"
