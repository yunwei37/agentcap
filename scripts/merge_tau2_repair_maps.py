"""Merge tau2 repair-map CSVs into one cumulative fallback input.

Repair maps are post-hoc diagnostic inputs for bounded task-loop experiments.
This script only combines saved CSV rows; it does not run a model, execute
tools, sync datasets, or mint authority.
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
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge tau2 repair-map CSVs")
    parser.add_argument("--run-id", default="R141")
    parser.add_argument("--output-dir", type=Path, default=Path("results/eval/R141"))
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("results/eval/R141/cumulative_repair_map.csv"),
    )
    parser.add_argument("repair_maps", type=Path, nargs="+")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = merge_repair_maps(
        run_id=args.run_id,
        repair_maps=args.repair_maps,
        output_dir=args.output_dir,
        output_csv=args.output_csv,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def merge_repair_maps(
    *,
    run_id: str,
    repair_maps: list[Path],
    output_dir: Path,
    output_csv: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows_by_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    fields: list[str] = []
    per_input_counts: list[dict[str, Any]] = []
    duplicate_rows = 0

    for index, path in enumerate(repair_maps):
        rows, path_fields = read_csv_with_fields(path)
        per_input_counts.append(
            {
                "path": str(path),
                "rows": len(rows),
                "eligible_repair_ready_rows": sum(1 for row in rows if is_ready(row)),
            }
        )
        for field in path_fields:
            if field not in fields:
                fields.append(field)
        for row_index, row in enumerate(rows):
            normalized = {field: row.get(field, "") for field in path_fields}
            normalized.setdefault("merge_source_csv", str(path))
            normalized.setdefault("merge_source_index", str(index))
            normalized.setdefault("merge_source_row", str(row_index + 2))
            key = row_key(normalized)
            if key in rows_by_key:
                duplicate_rows += 1
                continue
            rows_by_key[key] = normalized

    for field in ["merge_source_csv", "merge_source_index", "merge_source_row"]:
        if field not in fields:
            fields.append(field)

    rows = sorted(
        rows_by_key.values(),
        key=lambda row: (
            str(row.get("domain", "")),
            natural_int(row.get("task_id", "")),
            natural_int(row.get("earliest_synthesis_step", "")),
            str(row.get("event_id", "")),
            str(row.get("tool", "")),
            str(row.get("args_json", "")),
        ),
    )
    write_csv(output_csv, rows, fields)

    summary = {
        "run_id": run_id,
        "analysis": "saved tau2 cumulative repair-map merge",
        "repair_maps": [str(path) for path in repair_maps],
        "output_csv": str(output_csv),
        "input_rows": sum(item["rows"] for item in per_input_counts),
        "output_rows": len(rows),
        "duplicate_rows_dropped": duplicate_rows,
        "eligible_repair_ready_rows": sum(1 for row in rows if is_ready(row)),
        "input_counts": per_input_counts,
        "no_dataset_sync": True,
        "no_model_execution": True,
        "no_tool_execution": True,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": sha256_path(Path(__file__)),
        "project_head": git_output(["git", "rev-parse", "HEAD"]),
        "git_status": git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This is a deterministic saved-CSV merge for a bounded repair-map fallback experiment.",
            "Rows are deduplicated by domain, task, event id, tool, and args_json.",
            "The runner will still recheck visible values and route synthesized calls through the normal binder/gateway.",
        ],
    }
    write_json(output_dir / "cumulative_repair_map_summary.json", summary)
    write_csv(
        output_dir / "merge_input_digests.csv",
        input_digest_rows([*repair_maps, Path(__file__)]),
        ["path", "sha256", "bytes"],
    )
    (output_dir / "merge_command.txt").write_text(command_text(), encoding="utf-8")
    return {"rows": rows, "summary": summary}


def row_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("domain", "")),
        str(row.get("task_id", "")),
        str(row.get("event_id", "")),
        str(row.get("tool", "")),
        canonical_args(row),
    )


def canonical_args(row: dict[str, Any]) -> str:
    candidate = parse_json_dict(row.get("candidate_json", ""))
    args = candidate.get("arguments")
    if not isinstance(args, dict):
        args = parse_json_dict(row.get("args_json", ""))
    return json.dumps(args if isinstance(args, dict) else {}, sort_keys=True)


def is_ready(row: dict[str, Any]) -> bool:
    return truthy(row.get("eligible", "")) and str(row.get("proof_status", "")) == "repair_candidate_ready"


def read_csv_with_fields(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_json_dict(raw: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def natural_int(value: Any) -> int:
    try:
        return int(str(value))
    except ValueError:
        return 0


def input_digest_rows(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {"path": str(path), "sha256": sha256_path(path), "bytes": path_size(path)}
        for path in paths
        if path.exists()
    ]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    return digest.hexdigest()


def path_size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else 0


def command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv]) + "\n"


def git_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
