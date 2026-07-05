import json
from pathlib import Path

import scripts.analyze_tau2_residual_recovery_plan as analyzer


def context(tool_name="lookup", required=None, values=None):
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
        "compiler_hints": [],
        "previous_gateway_results_text": json.dumps({"values": values}),
        "task_text": json.dumps({"task": "use visible value"}),
    }


def actionability_row(**overrides):
    base = {
        "source_run_id": "RTEST",
        "domain": "demo",
        "task_id": "1",
        "reference_index": "0",
        "event_id": "demo:1:0",
        "tool": "lookup",
        "args_json": '{"id": "A"}',
        "db_feasible": "True",
        "actionability_class": "candidate_selection_or_planning_gap",
        "tool_visible_steps": "2",
        "all_arg_evidence_steps": "2",
        "runtime_exact_next_candidate_steps": "2",
        "complete_compiler_hint_steps": "",
    }
    base.update(overrides)
    return base


def candidate_row(**overrides):
    base = {
        "source_run_id": "R131",
        "domain": "demo",
        "task_id": "1",
        "step": "2",
        "rank_position": "3",
        "tool": "lookup",
        "args_json": '{"id": "A"}',
        "rank_score": "12",
        "candidate_correctness": "exact_next_reference",
        "exact_reference_event_id": "demo:1:0",
        "complete_arguments": "True",
        "proof_complete": "True",
        "proof_status": "proof_probe_complete",
        "lease_template_id": "template-1",
    }
    base.update(overrides)
    return base


def test_existing_exact_candidate_becomes_planner_recovery_candidate():
    row = actionability_row()

    original = analyzer.repair_analyzer.prompt_contexts_from_record
    analyzer.repair_analyzer.prompt_contexts_from_record = lambda record, run_dir=None: [context()]
    try:
        recovery = analyzer.classify_existing_exact_candidate_row(
            row=row,
            candidates=[candidate_row()],
            record={"stepwise": {"steps": []}},
            run_dir=Path("run"),
        )
    finally:
        analyzer.repair_analyzer.prompt_contexts_from_record = original

    assert recovery["eligible"] is True
    assert recovery["repair_class"] == "planner_select_existing_exact_candidate"
    assert recovery["recovery_kind"] == "planner_select_existing_exact_candidate"
    assert recovery["proof_status"] == "repair_candidate_ready"
    assert recovery["candidate_source"] == "saved_exact_next_runtime_candidate_label"
    assert recovery["planner_candidate_step"] == "2"
    assert recovery["planner_candidate_rank_position"] == "3"


def test_existing_exact_candidate_requires_visible_value_at_planner_step():
    row = actionability_row()

    original = analyzer.repair_analyzer.prompt_contexts_from_record
    analyzer.repair_analyzer.prompt_contexts_from_record = lambda record, run_dir=None: [
        context(values=["other"])
    ]
    try:
        recovery = analyzer.classify_existing_exact_candidate_row(
            row=row,
            candidates=[candidate_row()],
            record={"stepwise": {"steps": []}},
            run_dir=Path("run"),
        )
    finally:
        analyzer.repair_analyzer.prompt_contexts_from_record = original

    assert recovery["eligible"] is False
    assert recovery["proof_status"] == "missing_visible_argument_value"


def test_summary_counts_recovery_candidates_and_remaining_blockers():
    generated = analyzer.enrich_generated_row(
        {
            **actionability_row(event_id="demo:1:1", actionability_class="runtime_candidate_generation_gap"),
            "repair_class": "visible_tool_argument_candidate_generation",
            "eligible": True,
            "proof_status": "repair_candidate_ready",
            "tool": "lookup",
        }
    )
    planner = {
        **actionability_row(event_id="demo:1:0"),
        "repair_class": "planner_select_existing_exact_candidate",
        "eligible": True,
        "proof_status": "repair_candidate_ready",
        "recovery_kind": "planner_select_existing_exact_candidate",
        "tool": "lookup",
    }
    blocker = actionability_row(
        event_id="demo:1:2",
        actionability_class="tool_activation_gap",
    )

    summary = analyzer.build_summary(
        run_id="RTEST",
        actionability_csv=Path("a.csv"),
        task_residual_csv=Path("t.csv"),
        candidate_csv=Path("c.csv"),
        run_dir=Path("run"),
        output_dir=Path("out"),
        actionability_rows=[actionability_row(), generated, blocker],
        candidate_rows=[generated, planner],
        generated_rows=[generated],
        planner_rows=[planner],
        not_yet_candidate_rows=[blocker],
        task_rows=[],
        task_residual_rows=[
            {
                "domain": "demo",
                "task_id": "1",
                "reward_residual_not_missing_action": "True",
            }
        ],
    )

    assert summary["db_feasible_missing_actions_before_plan"] == 3
    assert summary["eligible_recovery_candidates"] == 2
    assert summary["eligible_generated_runtime_candidates"] == 1
    assert summary["eligible_existing_exact_candidate_recoveries"] == 1
    assert summary["not_yet_candidate_ready_db_feasible_missing_actions"] == 1
    assert summary["reward_residual_tasks_without_missing_action"] == 1
