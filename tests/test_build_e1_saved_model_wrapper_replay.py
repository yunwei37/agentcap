import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_e1_saved_model_wrapper_replay.py"
    spec = importlib.util.spec_from_file_location("build_e1_saved_model_wrapper_replay", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_saved_model_replay_policy_semantics_and_dedup(tmp_path):
    builder = _load_builder()
    first = tmp_path / "RTEST_A" / "model_call_mismatches.csv"
    second = tmp_path / "RTEST_B" / "model_call_mismatches.csv"
    _write_mismatch_csv(first, _rows())
    _write_mismatch_csv(second, [_rows()[0]])

    result = builder.build_replay(run_id="T206E1M", mismatch_csvs=(first, second))

    summary = result["summary"]
    assert summary["run_id"] == "T206E1M"
    assert summary["input_rows"] == 5
    assert summary["deduplicated_model_calls"] == 4
    assert summary["duplicate_rows_removed"] == 1
    assert summary["category_counts"] == {
        "exact_executed": 1,
        "off_lease_repeated_or_consumed_exact_args": 1,
        "off_lease_same_tool_wrong_args": 1,
        "off_lease_wrong_or_hallucinated_tool": 1,
    }

    policy_rows = {row["policy"]: row for row in result["policy_summary_rows"]}
    saved_gateway = policy_rows["intentcap_saved_gateway"]
    exact_lease = policy_rows["intentcap_exact_lease"]
    task_acl = policy_rows["task_reference_tool_acl"]
    broad_acl = policy_rows["broad_proposed_tool_acl"]

    assert saved_gateway["allowed_calls"] == 1
    assert saved_gateway["exact_reference_accepted"] == 1
    assert saved_gateway["off_reference_accepted"] == 0
    assert saved_gateway["exact_proposal_preservation_rate"] == 1.0

    assert exact_lease["allowed_calls"] == 1
    assert exact_lease["exact_reference_accepted"] == 1
    assert exact_lease["off_reference_accepted"] == 0

    assert task_acl["allowed_calls"] == 3
    assert task_acl["exact_reference_accepted"] == 1
    assert task_acl["off_reference_accepted"] == 2
    assert task_acl["same_tool_wrong_args_accepted"] == 1
    assert task_acl["repeated_or_consumed_exact_args_accepted"] == 1
    assert task_acl["wrong_or_hallucinated_tool_accepted"] == 0

    assert broad_acl["allowed_calls"] == 4
    assert broad_acl["exact_reference_accepted"] == 1
    assert broad_acl["off_reference_accepted"] == 3
    assert broad_acl["wrong_or_hallucinated_tool_accepted"] == 1
    assert broad_acl["false_accept_ratio_among_allowed"] == 0.75


def test_saved_model_replay_writes_outputs(tmp_path):
    builder = _load_builder()
    mismatch = tmp_path / "RTEST" / "model_call_mismatches.csv"
    _write_mismatch_csv(mismatch, _rows())
    result = builder.build_replay(run_id="T206E1M", mismatch_csvs=(mismatch,))

    output_dir = tmp_path / "out"
    builder.write_outputs(output_dir, result)

    replay = list(csv.DictReader((output_dir / "e1_saved_model_wrapper_replay.csv").open()))
    assert len(replay) == 16
    policy_summary = list(
        csv.DictReader((output_dir / "e1_saved_model_wrapper_policy_summary.csv").open())
    )
    assert {row["policy"] for row in policy_summary} == {
        "intentcap_saved_gateway",
        "intentcap_exact_lease",
        "task_reference_tool_acl",
        "broad_proposed_tool_acl",
    }
    run_summary = list(
        csv.DictReader((output_dir / "e1_saved_model_wrapper_run_policy_summary.csv").open())
    )
    assert len(run_summary) == 4
    summary = json.loads((output_dir / "e1_saved_model_wrapper_summary.json").read_text())
    assert summary["not_a_fresh_online_run"] is True
    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))
    assert len(digests) == 1
    assert (output_dir / "command.txt").exists()


def _write_mismatch_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_id",
        "domain",
        "task_id",
        "round",
        "index",
        "model_tool",
        "model_args_json",
        "category",
        "gateway_allowed",
        "executed",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _rows():
    return [
        {
            "run_id": "R1",
            "domain": "mock",
            "task_id": "t1",
            "round": "initial",
            "index": "0",
            "model_tool": "create_task",
            "model_args_json": '{"title":"Expected"}',
            "category": "exact_executed",
            "gateway_allowed": "True",
            "executed": "True",
        },
        {
            "run_id": "R1",
            "domain": "mock",
            "task_id": "t1",
            "round": "step_1",
            "index": "1",
            "model_tool": "create_task",
            "model_args_json": '{"title":"Wrong"}',
            "category": "off_lease_same_tool_wrong_args",
            "gateway_allowed": "False",
            "executed": "False",
        },
        {
            "run_id": "R1",
            "domain": "mock",
            "task_id": "t1",
            "round": "step_2",
            "index": "2",
            "model_tool": "delete_task",
            "model_args_json": '{"title":"Expected"}',
            "category": "off_lease_wrong_or_hallucinated_tool",
            "gateway_allowed": "False",
            "executed": "False",
        },
        {
            "run_id": "R1",
            "domain": "mock",
            "task_id": "t1",
            "round": "step_3",
            "index": "3",
            "model_tool": "create_task",
            "model_args_json": '{"title":"Expected"}',
            "category": "off_lease_repeated_or_consumed_exact_args",
            "gateway_allowed": "False",
            "executed": "False",
        },
    ]
