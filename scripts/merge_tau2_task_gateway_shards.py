"""Merge tau2 task-gateway task-id shards into one paper-facing run.

The local Qwen task-loop runner writes complete CSV/JSONL artifacts only after a
run finishes. Long multi-task runs can exceed interactive session limits, so
fresh online experiments are often executed as one-task shards. This merger is
purely mechanical: it concatenates completed shard artifacts and records input
digests. It does not run a model, execute tools, sync datasets, or relabel calls.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_tau2_local_llm_task_gateway import (  # noqa: E402
    ACTION_ROW_FIELDS,
    ROW_FIELDS,
    UNSUPPORTED_ROW_FIELDS,
    USER_SIMULATOR_ROW_FIELDS,
)

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge tau2 task-gateway shards")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--shard-dir",
        dest="shard_dirs",
        action="append",
        type=Path,
        required=True,
        help="Completed task-id shard directory. May be repeated in desired order.",
    )
    args = parser.parse_args()

    result = merge_shards(run_id=args.run_id, shard_dirs=tuple(args.shard_dirs))
    write_outputs(args.output_dir, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def merge_shards(*, run_id: str, shard_dirs: tuple[Path, ...]) -> dict[str, Any]:
    task_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    user_rows: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []
    sample_lines: list[str] = []
    shard_summaries: list[dict[str, Any]] = []

    for shard_dir in shard_dirs:
        task_rows.extend(_read_csv(shard_dir / "task_results.csv"))
        action_rows.extend(_read_csv(shard_dir / "action_results.csv"))
        user_rows.extend(_read_csv(shard_dir / "user_simulator_results.csv"))
        unsupported_rows.extend(_read_csv(shard_dir / "unsupported_tasks.csv"))
        sample_path = shard_dir / "samples.jsonl"
        if sample_path.exists():
            sample_lines.extend(line for line in sample_path.read_text().splitlines() if line)
        summary_path = shard_dir / "task_gateway_summary.json"
        shard_summaries.append(json.loads(summary_path.read_text()) if summary_path.exists() else {})

    input_paths = _input_paths(shard_dirs)
    summary = _summary(
        run_id=run_id,
        shard_dirs=shard_dirs,
        task_rows=task_rows,
        action_rows=action_rows,
        user_rows=user_rows,
        unsupported_rows=unsupported_rows,
        shard_summaries=shard_summaries,
        input_paths=input_paths,
    )
    return {
        "summary": summary,
        "task_rows": task_rows,
        "action_rows": action_rows,
        "user_rows": user_rows,
        "unsupported_rows": unsupported_rows,
        "sample_lines": sample_lines,
        "input_digests": [_file_digest(path) for path in input_paths],
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "task_results.csv", result["task_rows"], ROW_FIELDS)
    _write_rows(output_dir / "action_results.csv", result["action_rows"], ACTION_ROW_FIELDS)
    _write_rows(
        output_dir / "user_simulator_results.csv",
        result["user_rows"],
        USER_SIMULATOR_ROW_FIELDS,
    )
    _write_rows(
        output_dir / "unsupported_tasks.csv",
        result["unsupported_rows"],
        UNSUPPORTED_ROW_FIELDS,
    )
    (output_dir / "samples.jsonl").write_text(
        "".join(f"{line}\n" for line in result["sample_lines"])
    )
    _write_rows(output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "task_gateway_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())


def _summary(
    *,
    run_id: str,
    shard_dirs: tuple[Path, ...],
    task_rows: list[dict[str, Any]],
    action_rows: list[dict[str, Any]],
    user_rows: list[dict[str, Any]],
    unsupported_rows: list[dict[str, Any]],
    shard_summaries: list[dict[str, Any]],
    input_paths: list[Path],
) -> dict[str, Any]:
    tool_exposures = sorted({str(row.get("tool_exposure", "")) for row in task_rows if row.get("tool_exposure")})
    compact_values = sorted(
        {
            str(summary.get("stepwise_compact_json_prompts", ""))
            for summary in shard_summaries
            if "stepwise_compact_json_prompts" in summary
        }
    )
    unsupported_reasons = Counter(str(row.get("reason", "")) for row in unsupported_rows)
    return {
        "run_id": run_id,
        "analysis": "merged fresh local-Qwen tau2 task-gateway shards",
        "merged_from_task_id_shards": True,
        "source_shards": [str(path) for path in shard_dirs],
        "source_shard_count": len(shard_dirs),
        "tasks_evaluated": len(task_rows),
        "task_ids": [f"{row.get('domain', '')}:{row.get('task_id', '')}" for row in task_rows],
        "unsupported_tasks": len(unsupported_rows),
        "unsupported_reason_counts": dict(sorted(unsupported_reasons.items())),
        "model_calls": len(action_rows),
        "gateway_allowed": sum(1 for row in action_rows if _bool(row.get("gateway_allowed"))),
        "gateway_blocked": sum(1 for row in action_rows if not _bool(row.get("gateway_allowed"))),
        "executed_calls": sum(1 for row in action_rows if _bool(row.get("executed"))),
        "tool_error_calls": sum(1 for row in action_rows if _bool(row.get("tool_error"))),
        "tool_oracle_pass_tasks": sum(1 for row in task_rows if _bool(row.get("tool_oracle_pass"))),
        "all_reference_actions_executed_tasks": sum(
            1 for row in task_rows if _bool(row.get("all_reference_actions_executed"))
        ),
        "action_reward_pass_tasks": sum(
            1 for row in task_rows if _float(row.get("action_reward")) >= 1.0
        ),
        "env_reward_pass_tasks": sum(
            1 for row in task_rows if _float(row.get("env_reward")) >= 1.0
        ),
        "tool_exposure": "|".join(tool_exposures),
        "stepwise_compact_json_prompts": "|".join(compact_values),
        "user_simulator_rows": len(user_rows),
        "notes": [
            "Merged artifact is a mechanical concatenation of completed task-id shards.",
            "Shard runs use existing local tau2 artifacts only; they do not clone, sync, or download datasets.",
            "The merger does not run a model, execute tools, relabel calls, or change gateway decisions.",
        ],
        "input_digests": [_file_digest(path) for path in input_paths],
        "machine": platform.platform(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
    }


def _input_paths(shard_dirs: tuple[Path, ...]) -> list[Path]:
    names = (
        "command.txt",
        "task_gateway_summary.json",
        "task_results.csv",
        "action_results.csv",
        "user_simulator_results.csv",
        "unsupported_tasks.csv",
        "samples.jsonl",
        "input_digests.csv",
    )
    paths: list[Path] = []
    for shard_dir in shard_dirs:
        paths.extend(path for name in names if (path := shard_dir / name).exists())
    return paths


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(os.path.basename(sys.executable))
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
