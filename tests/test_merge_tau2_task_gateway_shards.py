import csv
import json
from pathlib import Path

import scripts.merge_tau2_task_gateway_shards as merger


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = sorted({key for row in rows for key in row}) if rows else ["placeholder"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _make_shard(path: Path, *, domain: str, task_id: str, allowed: bool) -> None:
    path.mkdir()
    _write_csv(
        path / "task_results.csv",
        [
            {
                "domain": domain,
                "task_id": task_id,
                "tool_exposure": "all",
                "tool_oracle_pass": allowed,
                "all_reference_actions_executed": allowed,
                "action_reward": 1.0 if allowed else 0.0,
                "env_reward": 1.0,
            }
        ],
    )
    _write_csv(
        path / "action_results.csv",
        [
            {
                "domain": domain,
                "task_id": task_id,
                "gateway_allowed": allowed,
                "executed": allowed,
                "tool_error": False,
            }
        ],
    )
    _write_csv(path / "user_simulator_results.csv", [])
    _write_csv(path / "unsupported_tasks.csv", [])
    (path / "samples.jsonl").write_text(json.dumps({"domain": domain, "task_id": task_id}) + "\n")
    (path / "task_gateway_summary.json").write_text(
        json.dumps({"run_id": path.name, "stepwise_compact_json_prompts": True})
    )
    (path / "command.txt").write_text("python run.py\n")
    (path / "input_digests.csv").write_text("path,sha256,bytes\n")


def test_merge_tau2_task_gateway_shards_concatenates_rows(tmp_path):
    shard_a = tmp_path / "shard_a"
    shard_b = tmp_path / "shard_b"
    _make_shard(shard_a, domain="airline", task_id="1", allowed=True)
    _make_shard(shard_b, domain="retail", task_id="0", allowed=False)

    result = merger.merge_shards(run_id="RTEST", shard_dirs=(shard_a, shard_b))

    assert result["summary"]["tasks_evaluated"] == 2
    assert result["summary"]["model_calls"] == 2
    assert result["summary"]["gateway_allowed"] == 1
    assert result["summary"]["gateway_blocked"] == 1
    assert result["summary"]["tool_oracle_pass_tasks"] == 1
    assert result["sample_lines"] == [
        '{"domain": "airline", "task_id": "1"}',
        '{"domain": "retail", "task_id": "0"}',
    ]

    output_dir = tmp_path / "merged"
    merger.write_outputs(output_dir, result)
    with (output_dir / "task_results.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 2
