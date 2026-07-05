import json

import scripts.analyze_tau2_candidate_generation_repair as analyzer


def context(tool_name="lookup", required=None, values=None, compiler_hints=None):
    required = required or ["id"]
    values = values or ["A"]
    return {
        "step": "2",
        "available_tools": [
            {
                "name": tool_name,
                "parameters": {
                    "required": required,
                    "properties": {key: {"type": "string"} for key in required},
                },
            }
        ],
        "compiler_hints": compiler_hints or [],
        "previous_gateway_results_text": json.dumps({"values": values}),
        "task_text": json.dumps({"task": "use the value from prior gateway output"}),
    }


def row(**overrides):
    base = {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "event_id": "demo:1:0",
        "tool": "lookup",
        "args_json": '{"id": "A"}',
        "actionability_class": "runtime_candidate_generation_gap",
        "tool_visible_steps": "2",
        "all_arg_evidence_steps": "2",
        "complete_compiler_hint_steps": "",
        "db_feasible": "True",
    }
    base.update(overrides)
    return base


def test_visible_tool_argument_gap_becomes_repair_candidate():
    record = {"stepwise": {"steps": []}}
    records = {("demo", "1"): record}

    def fake_contexts(_record, run_dir=None):
        return [context()]

    original = analyzer.prompt_contexts_from_record
    analyzer.prompt_contexts_from_record = fake_contexts
    try:
        repair = analyzer.classify_repair_row(row(), records)
    finally:
        analyzer.prompt_contexts_from_record = original

    assert repair["eligible"] is True
    assert repair["repair_class"] == "visible_tool_argument_candidate_generation"
    assert repair["earliest_synthesis_step"] == "2"
    assert repair["candidate_exact_reference_match"] is True
    assert repair["proof_status"] == "repair_candidate_ready"


def test_visible_gap_requires_argument_values_in_synthesis_step():
    record = {"stepwise": {"steps": []}}
    records = {("demo", "1"): record}

    def fake_contexts(_record, run_dir=None):
        return [context(values=["other"])]

    original = analyzer.prompt_contexts_from_record
    analyzer.prompt_contexts_from_record = fake_contexts
    try:
        repair = analyzer.classify_repair_row(row(), records)
    finally:
        analyzer.prompt_contexts_from_record = original

    assert repair["eligible"] is False
    assert repair["proof_status"] == "missing_visible_argument_value"


def test_complete_hint_candidate_is_recovered_from_prompt_hint():
    hint = {
        "tool": "lookup",
        "arguments": {"id": "A"},
        "complete_arguments": True,
    }
    record = {"stepwise": {"steps": []}}
    records = {("demo", "1"): record}

    def fake_contexts(_record, run_dir=None):
        return [context(compiler_hints=[hint])]

    original = analyzer.prompt_contexts_from_record
    analyzer.prompt_contexts_from_record = fake_contexts
    try:
        repair = analyzer.classify_repair_row(
            row(
                actionability_class="complete_compiler_hint_not_called",
                tool_visible_steps="",
                all_arg_evidence_steps="",
                complete_compiler_hint_steps="2",
            ),
            records,
        )
    finally:
        analyzer.prompt_contexts_from_record = original

    assert repair["eligible"] is True
    assert repair["repair_class"] == "existing_complete_compiler_hint_replay"
    assert repair["candidate_source"] == "saved_complete_compiler_hint"


def test_summary_counts_potential_repair_gain():
    repair_rows = [
        {
            **row(),
            "repair_class": "visible_tool_argument_candidate_generation",
            "eligible": True,
            "tool": "lookup",
            "candidate_source": "posthoc_reference_args_verified_visible_in_prompt",
        },
        {
            **row(event_id="demo:1:1", actionability_class="argument_evidence_gap"),
            "repair_class": "",
            "eligible": False,
            "tool": "lookup",
        },
    ]
    summary = analyzer.build_summary(
        run_id="RTEST",
        actionability_csv=__import__("pathlib").Path("missing.csv"),
        run_dir=__import__("pathlib").Path("run"),
        actionability_rows=[
            row(db_feasible="True"),
            row(event_id="demo:1:1", db_feasible="True"),
        ],
        repair_rows=repair_rows,
        task_rows=[],
    )

    assert summary["eligible_exact_candidate_repairs"] == 1
    assert summary["potential_db_feasible_missing_after_immediate_repairs"] == 1
