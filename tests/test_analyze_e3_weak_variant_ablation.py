import csv
import importlib.util
from pathlib import Path


def _load_analyzer():
    path = Path(__file__).parents[1] / "scripts" / "analyze_e3_weak_variant_ablation.py"
    spec = importlib.util.spec_from_file_location("analyze_e3_weak_variant_ablation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_csv(path, fieldnames, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_e3_weak_variant_ablation_counts_false_accepts(tmp_path):
    analyzer = _load_analyzer()
    authority_events = tmp_path / "authority.csv"
    workflow_baseline = tmp_path / "workflow.csv"

    _write_csv(
        authority_events,
        ["source", "mode", "checker_allowed", "has_class_substitution_attempt", "substitution_edges"],
        [
            {
                "source": "tool_suite",
                "mode": "authorize",
                "checker_allowed": "false",
                "has_class_substitution_attempt": "true",
                "substitution_edges": "tool->agent",
            },
            {
                "source": "env_suite",
                "mode": "sink_select",
                "checker_allowed": "false",
                "has_class_substitution_attempt": "true",
                "substitution_edges": "env->agent|env->tool",
            },
            {
                "source": "instruction_suite",
                "mode": "instruct",
                "checker_allowed": "false",
                "has_class_substitution_attempt": "true",
                "substitution_edges": "instruction->agent",
            },
            {
                "source": "benign",
                "mode": "write",
                "checker_allowed": "true",
                "has_class_substitution_attempt": "false",
                "substitution_edges": "",
            },
        ],
    )
    _write_csv(
        workflow_baseline,
        ["checker_allowed", "checker_reason", "policy_dsl_false_accept"],
        [
            {
                "checker_allowed": "true",
                "checker_reason": "",
                "policy_dsl_false_accept": "false",
            },
            {
                "checker_allowed": "false",
                "checker_reason": "denied: temporal prerequisites are unsatisfied",
                "policy_dsl_false_accept": "true",
            },
            {
                "checker_allowed": "false",
                "checker_reason": "denied: delegated capability exceeds parent authority",
                "policy_dsl_false_accept": "true",
            },
            {
                "checker_allowed": "false",
                "checker_reason": "denied: object outside lease",
                "policy_dsl_false_accept": "false",
            },
        ],
    )

    result = analyzer.analyze(
        authority_events=authority_events,
        workflow_baseline=workflow_baseline,
        run_id="unit",
    )
    summary = result["summary"]

    assert summary["authority_events"] == 4
    assert summary["authority_checker_denied"] == 3
    assert summary["no_owner_collapsed_context_false_accepts"] == 3
    assert summary["collapse_edge_false_accepts"] == {
        "tool->agent": 1,
        "env->agent": 1,
        "env->tool": 1,
        "instruction->agent": 1,
    }
    assert summary["workflow_events"] == 4
    assert summary["workflow_checker_denied"] == 3
    assert summary["workflow_policy_dsl_false_accepts"] == 2
    assert summary["workflow_split_lifecycle_false_accepts"] == 2
    assert summary["workflow_lifecycle_classes"] == {
        "temporal_state": 1,
        "delegation_attenuation": 1,
    }

    variants = {(row["corpus"], row["variant"]): row for row in result["variant_rows"]}
    assert variants[("R220 authority traces", "full_intentcap")]["unsafe_false_accepts"] == 0
    assert variants[("R220 authority traces", "no_owner_collapsed_context")][
        "false_accept_rate_among_denied"
    ] == "1.000000"
    assert variants[("R217 workflow residuals", "post_hoc_policy_dsl")][
        "unsafe_false_accepts"
    ] == 2
