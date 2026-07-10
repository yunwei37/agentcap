import importlib.util
import json
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_three_class_merge_coverage.py"
    spec = importlib.util.spec_from_file_location("analyze_three_class_merge_coverage", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_three_class_merge_coverage_counts_all_pairwise_merges(tmp_path):
    analyzer = _load_analyzer()
    weak_summary = tmp_path / "weak.json"
    skill_summary = tmp_path / "skill.json"
    suite = tmp_path / "suite.json"

    weak_summary.write_text(
        json.dumps(
            {
                "authority_checker_denied": 10,
                "collapse_edge_false_accepts": {
                    "tool->agent": 4,
                    "env->agent": 3,
                    "env->tool": 2,
                    "instruction->agent": 1,
                },
            }
        )
    )
    skill_summary.write_text(json.dumps({"blocked_instruction_substitutions": 2}))
    suite.write_text(
        json.dumps(
            {
                "labels": {
                    "instruction_source": {"allowed": {"instruct": ["workflow"]}},
                    "tool_source": {"allowed": {"tool_select": ["interface"]}},
                },
                "leases": [
                    {
                        "id": "interface",
                        "op": "exec.run",
                        "object": "/tool.py",
                        "args": {},
                        "control_may_depend_on": ["instruction_source"],
                        "data_may_depend_on": [],
                    },
                    {
                        "id": "instruction",
                        "op": "ctx.use",
                        "object": "workflow.instructions",
                        "args": {},
                        "control_may_depend_on": ["tool_source"],
                        "data_may_depend_on": [],
                    },
                ],
                "cases": [
                    {
                        "id": "instruction_to_tool",
                        "merge_pair": "instruction+tool",
                        "direction": "instruction->tool",
                        "artifact_family": "unit",
                        "unsafe_substitution": "instruction as tool",
                        "weak_variant_accepts": True,
                        "event": {
                            "id": "instruction_to_tool",
                            "op": "exec.run",
                            "object": "/tool.py",
                            "args": {},
                            "mode": "tool_select",
                            "decision": "interface",
                            "control_provenance": ["instruction_source"],
                            "data_provenance": [],
                        },
                    },
                    {
                        "id": "tool_to_instruction",
                        "merge_pair": "instruction+tool",
                        "direction": "tool->instruction",
                        "artifact_family": "unit",
                        "unsafe_substitution": "tool as instruction",
                        "weak_variant_accepts": True,
                        "event": {
                            "id": "tool_to_instruction",
                            "op": "ctx.use",
                            "object": "workflow.instructions",
                            "args": {},
                            "mode": "instruct",
                            "decision": "workflow",
                            "control_provenance": ["tool_source"],
                            "data_provenance": [],
                        },
                    },
                ],
            }
        )
    )

    result = analyzer.analyze(
        weak_summary_path=weak_summary,
        skill_summary_path=skill_summary,
        controlled_suite_path=suite,
        run_id="unit",
    )
    summary = result["summary"]

    assert summary["pairwise_merges"] == 6
    assert summary["pairwise_merges_with_counterexamples"] == 6
    assert summary["all_pairwise_merges_have_counterexample"] is True
    assert summary["controlled_cases"] == 2
    assert summary["controlled_instruction_tool_false_accepts"] == 2
    assert summary["full_checker_unsafe_accepts_on_controlled_cases"] == 0

    rows = {row["merged_pair"]: row for row in result["merge_rows"]}
    assert rows["agent+tool"]["false_accept_counterexamples"] == 4
    assert rows["instruction+env"]["false_accept_counterexamples"] == 2
    assert rows["instruction+tool"]["false_accept_counterexamples"] == 2

    case_rows = {row["case_id"]: row for row in result["case_rows"]}
    assert case_rows["instruction_to_tool"]["weak_false_accept"] is True
    assert case_rows["tool_to_instruction"]["weak_false_accept"] is True
