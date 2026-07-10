import scripts.analyze_tau2_write_activation_proof as analyzer


def test_write_intent_evidence_extracts_return_clause():
    evidence = analyzer.write_intent_evidence(
        tool="return_delivered_order_items",
        task_text=(
            "You want to know exactly how many tshirt options are available. "
            "You want to also return the cleaner, headphone, and smart watch."
        ),
    )

    assert evidence == "return the cleaner, headphone, and smart watch"


def test_gap_class_separates_collective_list_proof_from_missing_context():
    assert (
        analyzer.proof_gap_class(
            proof_complete=False,
            value_context_complete=True,
            collective_covered=True,
        )
        == "collective_tokens_present_but_leaf_threshold_missing"
    )
    assert (
        analyzer.proof_gap_class(
            proof_complete=False,
            value_context_complete=False,
            collective_covered=True,
        )
        == "missing_structured_value_context"
    )


def test_build_proof_row_reports_grouped_list_proof_ready(monkeypatch):
    monkeypatch.setattr(
        analyzer,
        "task_text_from_record",
        lambda record: "You want to also return the cleaner, headphone, and smart watch.",
    )
    activation_row = {
        "source_run_id": "RTEST",
        "domain": "retail",
        "task_id": "2",
        "event_id": "retail:2:2_11",
        "tool": "return_delivered_order_items",
        "tool_type": "write",
        "args_json": (
            '{"item_ids":["cleaner_item","headphone_item","watch_item"],'
            '"order_id":"#O","payment_method_id":"card"}'
        ),
    }
    action_rows = [
        {
            "executed": True,
            "tool_result_evidence": (
                '{"content":"{\\"items\\":[{\\"name\\":\\"Vacuum Cleaner\\",'
                '\\"item_id\\":\\"cleaner_item\\"},{\\"name\\":\\"Headphones\\",'
                '\\"item_id\\":\\"headphone_item\\"},{\\"name\\":\\"Smart Watch\\",'
                '\\"item_id\\":\\"watch_item\\"}],\\"order_id\\":\\"#O\\",'
                '\\"payment_history\\":[{\\"payment_method_id\\":\\"card\\"}]}"}'
            ),
        }
    ]

    row = analyzer.build_proof_row(
        activation_row=activation_row,
        action_rows=action_rows,
        record={},
    )

    assert row["semantic_tokens"] == "cleaner|headphone|smart|watch"
    assert row["value_context_complete"] is True
    assert row["collective_intent_tokens_covered"] is True
    assert row["value_proof_complete"] is True
    assert row["proof_gap_class"] == "write_activation_value_proof_complete"
    assert row["write_activation_candidate_ready"] is True
