import json

import scripts.analyze_tau2_write_proof_residuals as analyzer


def preview(content):
    return json.dumps(
        {
            "content": json.dumps(content),
            "error": False,
            "role": "tool",
        }
    )


def test_write_proof_residual_detects_list_and_alias_gap():
    prior_order = {
        "domain": "retail",
        "task_id": "1",
        "round": "step_1",
        "index": "0",
        "model_tool": "get_order_details",
        "model_args_json": '{"order_id": "#O"}',
        "event_id": "retail:1:0",
        "bound_reference_event_id": "retail:1:0",
        "executed": "True",
        "tool_result_preview": preview(
            {
                "order_id": "#O",
                "items": [
                    {
                        "name": "T-Shirt",
                        "item_id": "old",
                        "options": {
                            "color": "blue",
                            "size": "S",
                            "material": "cotton",
                            "style": "v-neck",
                        },
                    }
                ],
                "payment_history": [{"payment_method_id": "card"}],
            }
        ),
    }
    prior_product = {
        **prior_order,
        "round": "step_2",
        "index": "1",
        "model_tool": "get_product_details",
        "model_args_json": '{"product_id": "p"}',
        "event_id": "retail:1:1",
        "bound_reference_event_id": "retail:1:1",
        "tool_result_preview": preview(
            {
                "name": "T-Shirt",
                "variants": {
                    "new": {
                        "item_id": "new",
                        "options": {
                            "color": "purple",
                            "size": "S",
                            "material": "polyester",
                            "style": "v-neck",
                        },
                    }
                },
            }
        ),
    }
    blocked = {
        **prior_order,
        "round": "step_3",
        "index": "2",
        "model_tool": "modify_pending_order_items",
        "model_args_json": json.dumps(
            {
                "order_id": "#O",
                "item_ids": ["old"],
                "new_item_ids": ["new"],
                "payment_method_id": "card",
            }
        ),
        "event_id": "retail:1:2",
        "gateway_reason": "no matching lease",
        "runtime_binding_reason": (
            "missing runtime value proof for "
            "compiler-runtime-template:retail:1:0:modify_pending_order_items: "
            "runtime value context lacks intent discriminator tokens"
        ),
        "executed": "False",
        "tool_result_preview": "",
    }
    compiler_row = {
        "run_id": "RTEST",
        "domain": "retail",
        "task_id": "1",
        "tool": "modify_pending_order_items",
        "valid_tool": "True",
        "runtime_policy_args": "item_ids|new_item_ids|order_id|payment_method_id",
        "equals_any_policy_args": "",
        "intent_evidence": (
            "User wants to modify pending small tshirt items to purple, polyester, v-neck."
        ),
    }
    action_rows = [prior_order, prior_product, blocked]

    rows = analyzer.build_write_proof_rows(
        source_run_id="RTEST",
        action_rows=action_rows,
        action_rows_by_task={("retail", "1"): action_rows},
        compiler_rows=[compiler_row],
        repair_by_event={},
        recovery_by_event={"retail:1:2": {"eligible": "True"}},
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["missing_proof_args"] == "item_ids|new_item_ids|order_id|payment_method_id"
    assert row["list_argument_context_gap"] is True
    assert "tshirt" in row["alias_gap_tokens"]
    assert row["repair_map_candidate_ready"] is True
    assert row["next_mechanism_target"] == "add_intent_discriminator_aliases_or_structured_value_proof"


def test_repeated_state_residual_reports_same_call_bound_to_other_event():
    recovery_row = {
        "domain": "retail",
        "task_id": "1",
        "event_id": "retail:1:missing",
        "tool": "get_product_details",
        "args_json": '{"product_id": "p"}',
        "actionability_class": "candidate_selection_or_planning_gap",
        "proof_status": "missing_existing_exact_next_candidate",
    }
    action_row = {
        "domain": "retail",
        "task_id": "1",
        "round": "step_5",
        "event_id": "retail:1:future",
        "bound_reference_event_id": "retail:1:future",
        "model_tool": "get_product_details",
        "model_args_json": '{"product_id": "p"}',
        "executed": "True",
    }

    rows = analyzer.build_repeated_state_rows(
        source_run_id="RTEST",
        recovery_rows=[recovery_row],
        action_rows_by_task={("retail", "1"): [action_row]},
    )

    assert len(rows) == 1
    assert rows[0]["executed_same_call_event_ids"] == "retail:1:future"
    assert rows[0]["diagnosis"] == "same_tool_args_already_executed_for_different_reference"
    assert rows[0]["next_mechanism_target"] == "repeated_event_selection_or_reference_accounting"
