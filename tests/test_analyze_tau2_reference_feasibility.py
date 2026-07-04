import json

import scripts.analyze_tau2_reference_feasibility as analyzer


def test_invalid_hidden_product_id_from_schema_example_is_not_feasible():
    row = {
        "source_run_id": "R057",
        "domain": "retail",
        "task_id": "2",
        "reference_index": 1,
        "event_id": "retail:2:2_1",
        "tool": "get_product_details",
        "args_json": json.dumps({"product_id": "6086499569"}),
        "visibility": "hidden",
    }
    db = {
        "products": {
            "9523456873": {"product_id": "9523456873", "name": "T-Shirt"}
        },
        "orders": {},
        "users": {},
    }
    prompt_text = "product_id description: such as '6086499569'"

    result = analyzer.classify_missing_reference(
        run_id="RTEST",
        missing_row=row,
        domain_db=db,
        prompt_text=prompt_text,
    )

    assert result["feasibility"] == "invalid_schema_example_reference"
    assert result["invalid_reason"] == "product_id_not_in_retail_db"
    assert result["db_entity_exists"] is False
    assert result["schema_example_present"] is True


def test_valid_hidden_product_id_is_recoverable_only_with_nonprompt_grounding():
    row = {
        "source_run_id": "R057",
        "domain": "retail",
        "task_id": "2",
        "reference_index": 2,
        "event_id": "retail:2:2_3",
        "tool": "get_product_details",
        "args_json": json.dumps({"product_id": "9523456873"}),
        "visibility": "hidden",
    }
    db = {
        "products": {
            "9523456873": {"product_id": "9523456873", "name": "T-Shirt"}
        },
        "orders": {},
        "users": {},
    }

    result = analyzer.classify_missing_reference(
        run_id="RTEST",
        missing_row=row,
        domain_db=db,
        prompt_text="",
    )

    assert result["feasibility"] == "valid_hidden_reference"
    assert result["invalid_reason"] == ""
    assert result["db_entity_exists"] is True
    assert result["schema_example_present"] is False


def test_retail_return_reference_checks_static_order_and_payment_constraints():
    args = {
        "order_id": "#W1",
        "item_ids": ["i1", "i2"],
        "payment_method_id": "credit_card_1",
    }
    orders = {
        "#W1": {
            "status": "delivered",
            "user_id": "u1",
            "items": [{"item_id": "i1"}, {"item_id": "i2"}],
        }
    }
    users = {"u1": {"payment_methods": {"credit_card_1": {}}}}

    assert analyzer._retail_return_reference_exists(args, orders, users) == (True, "")

    bad_args = dict(args, item_ids=["i3"])
    assert analyzer._retail_return_reference_exists(bad_args, orders, users) == (
        False,
        "return_item_ids_not_in_order",
    )
