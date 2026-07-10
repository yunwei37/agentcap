"""Score tau2 task results after excluding invalid reference actions.

R061 is a saved-result accounting pass. It combines R059 residual rows with
R060 reference-feasibility rows to separate official tool-oracle failures from
benchmark reference-quality issues. It does not run models, execute tools,
inspect prompts, clone benchmarks, or sync datasets.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_RESIDUAL_DIR = Path("results/eval/R059")
DEFAULT_FEASIBILITY_DIR = Path("results/eval/R060")
DEFAULT_SOURCE_RUN_DIR = Path("results/eval/R057")

TASK_FIELDS = [
    "run_id",
    "source_run_id",
    "domain",
    "task_id",
    "official_reference_actions",
    "invalid_reference_actions",
    "db_feasible_reference_actions",
    "official_executed_reference_actions",
    "executed_db_feasible_reference_actions",
    "official_missing_reference_actions",
    "missing_db_feasible_reference_actions",
    "official_tool_oracle_pass",
    "official_all_reference_actions_executed",
    "db_feasible_reference_complete",
    "official_action_reward",
    "official_env_reward",
    "adjusted_action_env_pass",
    "adjusted_category",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score tau2 residuals after excluding invalid reference actions"
    )
    parser.add_argument("--residual-dir", type=Path, default=DEFAULT_RESIDUAL_DIR)
    parser.add_argument("--feasibility-dir", type=Path, default=DEFAULT_FEASIBILITY_DIR)
    parser.add_argument("--source-run-dir", type=Path, default=DEFAULT_SOURCE_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Analysis run id to record in the summary; defaults to the output directory name.",
    )
    args = parser.parse_args()

    run_id = args.run_id or args.output_dir.name
    result = analyze_run(
        residual_dir=args.residual_dir,
        feasibility_dir=args.feasibility_dir,
        source_run_dir=args.source_run_dir,
        run_id=run_id,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        args.output_dir / "invalid_reference_adjusted_tasks.csv",
        result["task_rows"],
        TASK_FIELDS,
    )
    (args.output_dir / "tau2_invalid_reference_oracle_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (args.output_dir / "input_digests.csv").write_text(
        _input_digest_csv(args.residual_dir, args.feasibility_dir, args.source_run_dir)
    )
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_run(
    *,
    residual_dir: Path,
    feasibility_dir: Path,
    source_run_dir: Path,
    run_id: str = "R061",
) -> dict[str, Any]:
    task_rows = score_task_rows(
        run_id=run_id,
        residual_rows=_read_csv(residual_dir / "task_residual_completion.csv"),
        feasibility_rows=_read_csv(feasibility_dir / "reference_feasibility.csv"),
    )
    summary = _summary(
        run_id=run_id,
        residual_dir=residual_dir,
        feasibility_dir=feasibility_dir,
        source_run_dir=source_run_dir,
        task_rows=task_rows,
    )
    return {"task_rows": task_rows, "summary": summary}


def score_task_rows(
    *,
    run_id: str,
    residual_rows: list[dict[str, str]],
    feasibility_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    invalid_by_task: dict[tuple[str, str], int] = defaultdict(int)
    for row in feasibility_rows:
        if str(row.get("feasibility", "")).startswith("invalid_"):
            invalid_by_task[(str(row.get("domain", "")), str(row.get("task_id", "")))] += 1

    scored: list[dict[str, Any]] = []
    for row in residual_rows:
        domain = str(row.get("domain", ""))
        task_id = str(row.get("task_id", ""))
        invalid_refs = invalid_by_task[(domain, task_id)]
        official_refs = _int(row.get("reference_actions"))
        official_executed = _int(row.get("executed_reference_actions"))
        official_missing = _int(row.get("missing_reference_actions"))
        db_feasible_refs = official_refs - invalid_refs
        missing_db_feasible = max(official_missing - invalid_refs, 0)
        executed_db_feasible = db_feasible_refs - missing_db_feasible
        db_feasible_complete = missing_db_feasible == 0
        env_reward = _float(row.get("env_reward"))
        action_reward = _float(row.get("action_reward"))
        official_pass = _bool(row.get("tool_oracle_pass"))
        official_all_refs = _bool(row.get("all_reference_actions_executed"))
        adjusted_action_env_pass = db_feasible_complete and env_reward == 1.0

        scored.append(
            {
                "run_id": run_id,
                "source_run_id": str(row.get("source_run_id", "")),
                "domain": domain,
                "task_id": task_id,
                "official_reference_actions": official_refs,
                "invalid_reference_actions": invalid_refs,
                "db_feasible_reference_actions": db_feasible_refs,
                "official_executed_reference_actions": official_executed,
                "executed_db_feasible_reference_actions": executed_db_feasible,
                "official_missing_reference_actions": official_missing,
                "missing_db_feasible_reference_actions": missing_db_feasible,
                "official_tool_oracle_pass": official_pass,
                "official_all_reference_actions_executed": official_all_refs,
                "db_feasible_reference_complete": db_feasible_complete,
                "official_action_reward": action_reward,
                "official_env_reward": env_reward,
                "adjusted_action_env_pass": adjusted_action_env_pass,
                "adjusted_category": _adjusted_category(
                    official_pass=official_pass,
                    invalid_refs=invalid_refs,
                    missing_db_feasible=missing_db_feasible,
                    env_reward=env_reward,
                ),
            }
        )
    return scored


def _adjusted_category(
    *,
    official_pass: bool,
    invalid_refs: int,
    missing_db_feasible: int,
    env_reward: float,
) -> str:
    if official_pass:
        return "official_pass"
    if invalid_refs > 0 and missing_db_feasible == 0 and env_reward == 1.0:
        return "invalid_reference_only"
    if missing_db_feasible == 0 and env_reward != 1.0:
        return "feasible_refs_complete_but_reward_failed"
    if missing_db_feasible > 0:
        return "missing_db_feasible_reference_actions"
    return "unclassified_failure"


def _summary(
    *,
    run_id: str,
    residual_dir: Path,
    feasibility_dir: Path,
    source_run_dir: Path,
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    categories = Counter(str(row["adjusted_category"]) for row in task_rows)
    official_pass_tasks = sum(1 for row in task_rows if row["official_tool_oracle_pass"])
    feasible_complete_tasks = sum(
        1 for row in task_rows if row["db_feasible_reference_complete"]
    )
    adjusted_action_env_pass_tasks = sum(
        1 for row in task_rows if row["adjusted_action_env_pass"]
    )
    invalid_refs = sum(int(row["invalid_reference_actions"]) for row in task_rows)
    return {
        "run_id": run_id,
        "analysis": "saved tau2 invalid-reference-aware oracle accounting",
        "source_run": _source_run(task_rows),
        "source_run_dir": str(source_run_dir),
        "residual_dir": str(residual_dir),
        "feasibility_dir": str(feasibility_dir),
        "no_dataset_sync": True,
        "no_model_execution": True,
        "no_tool_execution": True,
        "inspects_hidden_references": False,
        "tasks": len(task_rows),
        "official_tool_oracle_pass_tasks": official_pass_tasks,
        "official_tool_oracle_pass_rate": _rate(official_pass_tasks, len(task_rows)),
        "db_feasible_reference_complete_tasks": feasible_complete_tasks,
        "db_feasible_reference_complete_rate": _rate(feasible_complete_tasks, len(task_rows)),
        "adjusted_action_env_pass_tasks": adjusted_action_env_pass_tasks,
        "adjusted_action_env_pass_rate": _rate(adjusted_action_env_pass_tasks, len(task_rows)),
        "official_reference_actions": sum(
            int(row["official_reference_actions"]) for row in task_rows
        ),
        "invalid_reference_actions": invalid_refs,
        "db_feasible_reference_actions": sum(
            int(row["db_feasible_reference_actions"]) for row in task_rows
        ),
        "executed_db_feasible_reference_actions": sum(
            int(row["executed_db_feasible_reference_actions"]) for row in task_rows
        ),
        "missing_db_feasible_reference_actions": sum(
            int(row["missing_db_feasible_reference_actions"]) for row in task_rows
        ),
        "adjusted_category_counts": dict(sorted(categories.items())),
        "invalid_reference_only_tasks": categories["invalid_reference_only"],
        "feasible_refs_complete_but_reward_failed_tasks": categories[
            "feasible_refs_complete_but_reward_failed"
        ],
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This pass combines saved residual-completion rows with reference-feasibility rows only.",
            "It does not change the official tau2 tool-oracle score.",
            "Adjusted action/env pass excludes references already classified as invalid by the provided reference-feasibility audit, then still requires env_reward == 1.0.",
            "It is an oracle-quality/accounting audit, not a fresh model run or utility improvement.",
        ],
    }


def _source_run(task_rows: list[dict[str, Any]]) -> str:
    runs = sorted({str(row.get("source_run_id", "")) for row in task_rows if row.get("source_run_id")})
    return "|".join(runs)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(residual_dir: Path, feasibility_dir: Path, source_run_dir: Path) -> str:
    lines = ["path,sha256,bytes"]
    for child in (
        residual_dir / "task_residual_completion.csv",
        residual_dir / "missing_reference_actions.csv",
        feasibility_dir / "reference_feasibility.csv",
        feasibility_dir / "tau2_reference_feasibility_summary.json",
        source_run_dir / "task_gateway_summary.json",
    ):
        lines.append(_digest_line(child))
    return "\n".join(lines) + "\n"


def _digest_line(path: Path) -> str:
    data = path.read_bytes()
    return f"{path},{_sha256(data)},{len(data)}"


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    ) or "unavailable"


def _int(value: Any) -> int:
    return int(str(value or 0))


def _float(value: Any) -> float:
    return float(str(value or 0.0))


def _bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
