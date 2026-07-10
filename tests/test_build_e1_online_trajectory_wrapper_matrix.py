import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "scripts" / "build_e1_online_trajectory_wrapper_matrix.py"
    spec = importlib.util.spec_from_file_location("build_e1_online_trajectory_wrapper_matrix", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_online_trajectory_matrix_compares_saved_runs(tmp_path):
    builder = _load_builder()
    all_run = tmp_path / "RALL"
    leased_run = tmp_path / "RLEASED"
    mismatch = tmp_path / "model_call_mismatches.csv"
    _write_run(
        all_run,
        command="python runner.py --stepwise-max-steps 3",
        tool_exposure="",
        actions=[
            _action("mock", "t1", "create_task", allowed=True, executed=True),
            _action("mock", "t1", "delete_task", allowed=False, executed=False),
        ],
        tasks=[
            _task("mock", "t1", model_calls=2, allowed=1, blocked=1, executed=1, oracle=True)
        ],
    )
    _write_run(
        leased_run,
        command="python runner.py --stepwise-max-steps 3 --tool-exposure leased",
        tool_exposure="leased",
        actions=[
            _action("mock", "t1", "create_task", allowed=True, executed=True),
            _action("mock", "t1", "create_task", allowed=False, executed=False),
        ],
        tasks=[
            _task(
                "mock",
                "t1",
                model_calls=2,
                allowed=1,
                blocked=1,
                executed=1,
                oracle=False,
                tool_schema_count=1,
            )
        ],
    )
    _write_mismatch_csv(
        mismatch,
        [
            _mismatch("RALL", "mock", "t1", "create_task", "exact_executed"),
            _mismatch("RALL", "mock", "t1", "delete_task", "off_lease_wrong_or_hallucinated_tool"),
            _mismatch("RLEASED", "mock", "t1", "create_task", "exact_executed"),
            _mismatch("RLEASED", "mock", "t1", "create_task", "off_lease_same_tool_wrong_args"),
        ],
    )

    result = builder.build_matrix(
        run_id="T208E1T",
        run_dirs=(all_run, leased_run),
        mismatch_csvs=(mismatch,),
    )

    summary = result["summary"]
    assert summary["run_id"] == "T208E1T"
    assert summary["uses_saved_online_model_trajectories"] is True
    assert summary["not_a_fresh_online_run"] is True
    assert summary["primary_pair_delta"] == {
        "leased_minus_all_action_reward_pass_tasks": -1,
        "leased_minus_all_exact_executed_calls": 0,
        "leased_minus_all_gateway_blocked_calls": 0,
        "leased_minus_all_tool_oracle_pass_tasks": -1,
        "leased_minus_all_wrong_or_hallucinated_tool_calls": -1,
    }

    rows = {row["trajectory_family"]: row for row in result["run_rows"]}
    assert rows["all_tools_exact_gateway"]["tool_exposure"] == "all"
    assert rows["all_tools_exact_gateway"]["wrong_or_hallucinated_tool_calls"] == 1
    assert rows["intentcap_leased_tools_exact_gateway"]["tool_exposure"] == "leased"
    assert rows["intentcap_leased_tools_exact_gateway"]["same_tool_wrong_args_calls"] == 1
    assert rows["intentcap_leased_tools_exact_gateway"]["mean_tool_schema_count"] == 1.0


def test_online_trajectory_matrix_writes_outputs(tmp_path):
    builder = _load_builder()
    all_run = tmp_path / "RALL"
    leased_run = tmp_path / "RLEASED"
    mismatch = tmp_path / "model_call_mismatches.csv"
    _write_run(
        all_run,
        command="python runner.py",
        tool_exposure="",
        actions=[_action("mock", "t1", "create_task", allowed=True, executed=True)],
        tasks=[_task("mock", "t1", model_calls=1, allowed=1, blocked=0, executed=1, oracle=True)],
    )
    _write_run(
        leased_run,
        command="python runner.py --tool-exposure leased",
        tool_exposure="leased",
        actions=[_action("mock", "t1", "create_task", allowed=True, executed=True)],
        tasks=[
            _task(
                "mock",
                "t1",
                model_calls=1,
                allowed=1,
                blocked=0,
                executed=1,
                oracle=True,
                tool_schema_count=1,
            )
        ],
    )
    _write_mismatch_csv(
        mismatch,
        [
            _mismatch("RALL", "mock", "t1", "create_task", "exact_executed"),
            _mismatch("RLEASED", "mock", "t1", "create_task", "exact_executed"),
        ],
    )
    result = builder.build_matrix(
        run_id="T208E1T",
        run_dirs=(all_run, leased_run),
        mismatch_csvs=(mismatch,),
    )

    output_dir = tmp_path / "out"
    builder.write_outputs(output_dir, result)

    run_rows = list(csv.DictReader((output_dir / "e1_online_trajectory_wrapper_matrix.csv").open()))
    task_rows = list(csv.DictReader((output_dir / "e1_online_trajectory_task_matrix.csv").open()))
    summary = json.loads((output_dir / "e1_online_trajectory_wrapper_summary.json").read_text())
    digests = list(csv.DictReader((output_dir / "input_digests.csv").open()))

    assert len(run_rows) == 2
    assert len(task_rows) == 2
    assert summary["run_rows"] == 2
    assert len(digests) == 9
    assert (output_dir / "command.txt").exists()


def _write_run(path, *, command, tool_exposure, actions, tasks):
    path.mkdir(parents=True)
    (path / "command.txt").write_text(command + "\n")
    (path / "task_gateway_summary.json").write_text(json.dumps({"run_id": path.name}))
    _write_rows(path / "action_results.csv", actions, list(actions[0]))
    if tool_exposure:
        for task in tasks:
            task["tool_exposure"] = tool_exposure
    _write_rows(path / "task_results.csv", tasks, list(tasks[0]))


def _write_rows(path, rows, fields):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_mismatch_csv(path, rows):
    fields = ["run_id", "domain", "task_id", "model_tool", "model_args_json", "category"]
    _write_rows(path, rows, fields)


def _action(domain, task_id, tool, *, allowed, executed):
    return {
        "domain": domain,
        "task_id": task_id,
        "round": "step_1",
        "index": "0",
        "model_tool": tool,
        "model_args_json": "{}",
        "bound_reference_event_id": "ref" if allowed else "",
        "event_id": "",
        "object": tool,
        "gateway_allowed": str(allowed),
        "gateway_action": "allow" if allowed else "block",
        "gateway_reason": "allowed" if allowed else "no matching lease",
        "executed": str(executed),
        "tool_error": "False",
        "tool_result_preview": "",
    }


def _task(
    domain,
    task_id,
    *,
    model_calls,
    allowed,
    blocked,
    executed,
    oracle,
    tool_schema_count="",
):
    return {
        "domain": domain,
        "task_id": task_id,
        "tool_schema_count": tool_schema_count,
        "model_calls": str(model_calls),
        "bound_reference_calls": str(executed),
        "gateway_allowed": str(allowed),
        "gateway_blocked": str(blocked),
        "executed_calls": str(executed),
        "tool_error_calls": "0",
        "off_lease_calls_blocked": str(blocked),
        "all_reference_actions_executed": str(oracle),
        "action_reward": "1.0" if oracle else "0.0",
        "env_reward": "1.0",
        "tool_oracle_pass": str(oracle),
    }


def _mismatch(run_id, domain, task_id, tool, category):
    return {
        "run_id": run_id,
        "domain": domain,
        "task_id": task_id,
        "model_tool": tool,
        "model_args_json": "{}",
        "category": category,
    }
