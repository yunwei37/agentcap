import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_scorer():
    path = Path(__file__).parents[1] / "scripts" / "score_expert_oracle_policy_distance.py"
    spec = importlib.util.spec_from_file_location("score_expert_oracle_policy_distance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scores_exact_and_overbroad_policies(tmp_path):
    scorer = _load_scorer()
    oracle = tmp_path / "oracle.csv"
    policies = tmp_path / "policies.csv"
    _write_csv(oracle, [_oracle_row("EO-001")])
    _write_csv(
        policies,
        [
            {
                **_policy_row("EO-001", "intentcap_exact"),
            },
            {
                **_policy_row("EO-001", "static_acl"),
                "lease_objects": "GmailReadEmail|GmailSendEmail",
                "lease_allowed_sinks": "github://org/repo|email://attacker",
                "influence_modes": "authorize|parameterize|delegate",
                "budget_invocations_total": "3",
            },
        ],
    )

    result = scorer.score_policy_distance(
        run_id="T202",
        oracle_path=oracle,
        policy_path=policies,
        output_dir=tmp_path / "R202",
    )

    assert result["summary"]["score_status"] == "ok"
    rows = list(csv.DictReader((tmp_path / "R202" / "expert_policy_oracle_distance.csv").open()))
    exact = next(row for row in rows if row["policy"] == "intentcap_exact")
    static = next(row for row in rows if row["policy"] == "static_acl")
    assert exact["oracle_distance_score"] == "0"
    assert static["extra_objects"] == "GmailSendEmail"
    assert static["extra_sinks"] == "email://attacker"
    assert static["extra_influence_modes"] == "delegate"
    assert static["budget_extra_invocations"] == "2"
    assert int(static["oracle_distance_score"]) > 0
    summary = list(csv.DictReader((tmp_path / "R202" / "expert_policy_oracle_summary.csv").open()))
    assert {row["policy"] for row in summary} == {"intentcap_exact", "static_acl"}


def test_scores_missing_coverage_and_argument_mismatch(tmp_path):
    scorer = _load_scorer()
    oracle = tmp_path / "oracle.csv"
    policies = tmp_path / "policies.csv"
    _write_csv(oracle, [_oracle_row("EO-001")])
    row = _policy_row("EO-001", "underfit_policy")
    row["lease_operations"] = ""
    row["lease_argument_constraints_json"] = json.dumps([{"mode": "prefix"}])
    row["decision_classes"] = "tool_arguments"
    _write_csv(policies, [row])

    result = scorer.score_policy_distance(
        run_id="T202",
        oracle_path=oracle,
        policy_path=policies,
        output_dir=tmp_path / "R202",
    )

    scored = result["distance_rows"][0]
    assert scored["status"] == "ok"
    assert scored["missing_operations"] == "tool.call"
    assert scored["missing_decision_classes"] == "tool_select"
    assert scored["argument_constraint_mismatch"] == 1
    assert scored["coverage_gap_units"] == 2
    assert scored["oracle_distance_score"] == 25


def test_missing_oracle_marks_summary_incomplete(tmp_path):
    scorer = _load_scorer()
    oracle = tmp_path / "oracle.csv"
    policies = tmp_path / "policies.csv"
    _write_csv(oracle, [_oracle_row("EO-001")])
    _write_csv(policies, [_policy_row("EO-MISSING", "some_policy")])

    result = scorer.score_policy_distance(
        run_id="T202",
        oracle_path=oracle,
        policy_path=policies,
        output_dir=tmp_path / "R202",
    )

    assert result["summary"]["score_status"] == "incomplete"
    assert result["summary"]["missing_oracle_rows"] == 1
    assert result["distance_rows"][0]["status"] == "missing_oracle"


def _oracle_row(sample_id):
    return {
        "sample_id": sample_id,
        "benchmark": "InjecAgent",
        "workload_family": "tool_response_injection",
        "lease_operations": "tool.call",
        "lease_objects": "GmailReadEmail",
        "lease_allowed_sinks": "github://org/repo",
        "influence_modes": "authorize|parameterize",
        "decision_classes": "tool_select|tool_arguments",
        "budget_invocations_total": "1",
        "lease_argument_constraints_json": json.dumps([{"mode": "exact"}]),
    }


def _policy_row(sample_id, policy):
    return {
        "sample_id": sample_id,
        "benchmark": "InjecAgent",
        "workload_family": "tool_response_injection",
        "policy": policy,
        "lease_operations": "tool.call",
        "lease_objects": "GmailReadEmail",
        "lease_allowed_sinks": "github://org/repo",
        "influence_modes": "authorize|parameterize",
        "decision_classes": "tool_select|tool_arguments",
        "budget_invocations_total": "1",
        "lease_argument_constraints_json": json.dumps([{"mode": "exact"}]),
    }


def _write_csv(path, rows):
    with path.open("w", newline="") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
