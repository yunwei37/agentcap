from types import SimpleNamespace

import scripts.analyze_tau2_tool_activation_gaps as analyzer


def row(**overrides):
    base = {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "event_id": "demo:1:0",
        "tool": "get_user_details",
        "args_json": '{"user_id": "u1"}',
        "actionability_class": "tool_activation_gap",
        "db_feasible": "True",
    }
    base.update(overrides)
    return base


def context(*, values="u1", tools=()):
    return {
        "step": "2",
        "available_tools": [{"name": tool, "parameters": {"required": ["user_id"]}} for tool in tools],
        "task_text": "",
        "previous_gateway_results_text": values,
    }


def test_read_tool_activation_candidate_requires_catalog_and_visible_args(monkeypatch):
    monkeypatch.setattr(
        analyzer.repair_analyzer,
        "prompt_contexts_from_record",
        lambda record, run_dir=None: [context(values='{"user_id":"u1"}')],
    )
    tool = SimpleNamespace(tool_type="read", arguments=("user_id",))

    result = analyzer.build_activation_row(
        row=row(),
        record={"stepwise": {"steps": []}},
        run_dir=None,
        tool_catalog={("demo", "get_user_details"): tool},
    )

    assert result["activation_eligible"] is True
    assert result["activation_kind"] == "read_only_tool_activation_from_visible_argument"
    assert result["proof_status"] == "activation_candidate_ready"
    assert result["earliest_arg_visible_step"] == "2"


def test_write_tool_activation_is_blocked_even_when_values_are_visible(monkeypatch):
    monkeypatch.setattr(
        analyzer.repair_analyzer,
        "prompt_contexts_from_record",
        lambda record, run_dir=None: [context(values='{"order_id":"#O"}')],
    )
    tool = SimpleNamespace(tool_type="write", arguments=("order_id",))

    result = analyzer.build_activation_row(
        row=row(tool="return_delivered_order_items", args_json='{"order_id": "#O"}'),
        record={"stepwise": {"steps": []}},
        run_dir=None,
        tool_catalog={("demo", "return_delivered_order_items"): tool},
    )

    assert result["activation_eligible"] is False
    assert result["activation_kind"] == "write_or_high_impact_tool_activation_requires_value_proof"
    assert result["proof_status"] == "write_activation_requires_structured_value_proof"


def test_activation_candidate_requires_visible_argument_values(monkeypatch):
    monkeypatch.setattr(
        analyzer.repair_analyzer,
        "prompt_contexts_from_record",
        lambda record, run_dir=None: [context(values='{"user_id":"other"}')],
    )
    tool = SimpleNamespace(tool_type="read", arguments=("user_id",))

    result = analyzer.build_activation_row(
        row=row(),
        record={"stepwise": {"steps": []}},
        run_dir=None,
        tool_catalog={("demo", "get_user_details"): tool},
    )

    assert result["activation_eligible"] is False
    assert result["activation_kind"] == "missing_visible_argument_evidence"
    assert result["proof_status"] == "missing_visible_argument_value"


def test_summary_reports_potential_adjusted_missing_after_read_activation():
    eligible = {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "event_id": "demo:1:0",
        "actionability_class": "tool_activation_gap",
        "activation_eligible": True,
        "activation_kind": "read_only_tool_activation_from_visible_argument",
        "proof_status": "activation_candidate_ready",
    }
    blocked = {
        **eligible,
        "event_id": "demo:1:1",
        "activation_eligible": False,
        "activation_kind": "write_or_high_impact_tool_activation_requires_value_proof",
        "proof_status": "write_activation_requires_structured_value_proof",
    }

    summary = analyzer.build_summary(
        run_id="RTEST",
        actionability_csv="a.csv",
        run_dir="run",
        benchmark_dir="bench",
        output_dir="out",
        prior_adjusted_missing=17,
        actionability_rows=[eligible, blocked],
        activation_rows=[eligible, blocked],
        task_rows=[],
    )

    assert summary["input_tool_activation_gaps"] == 2
    assert summary["eligible_read_only_activation_candidates"] == 1
    assert summary["write_or_high_impact_activation_blockers"] == 1
    assert summary["potential_adjusted_missing_after_read_activation_candidates"] == 16
