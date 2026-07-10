"""Audit feasibility of missing tau2 reference actions.

R060 is a saved-result audit over residual task-gateway failures. Unlike
analyze_tau2_residual_completion.py, this script is allowed to inspect the
benchmark DB and hidden reference actions to determine whether a missing
reference is valid, hidden-but-possibly-recoverable, or invalid/schema-example
only. It does not run a model, execute tools, clone benchmarks, or sync data.
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

try:  # Import works both as `python scripts/foo.py` and from pytest.
    from scripts import analyze_tau2_residual_completion as residual
except ModuleNotFoundError:  # pragma: no cover - script execution path
    import analyze_tau2_residual_completion as residual  # type: ignore


DEFAULT_RUN_DIR = Path("results/eval/R057")
DEFAULT_BENCHMARK_DIR = Path("benchmarks/tau2-bench")

FEASIBILITY_FIELDS = [
    "run_id",
    "source_run_id",
    "domain",
    "task_id",
    "reference_index",
    "event_id",
    "tool",
    "args_json",
    "visibility",
    "feasibility",
    "invalid_reason",
    "db_entity_exists",
    "schema_example_present",
    "db_checked",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit missing tau2 reference-action feasibility"
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Analysis run id to record in the summary; defaults to the output directory name.",
    )
    args = parser.parse_args()

    run_id = args.run_id or args.output_dir.name
    result = analyze_run(args.run_dir, args.benchmark_dir, run_id=run_id)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(
        args.output_dir / "reference_feasibility.csv",
        result["feasibility_rows"],
        FEASIBILITY_FIELDS,
    )
    (args.output_dir / "tau2_reference_feasibility_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (args.output_dir / "input_digests.csv").write_text(
        _input_digest_csv(args.run_dir, args.benchmark_dir)
    )
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze_run(run_dir: Path, benchmark_dir: Path, *, run_id: str = "R060") -> dict[str, Any]:
    residual_result = residual.analyze_run(run_dir, run_id=run_id)
    records = residual._load_jsonl(run_dir / "samples.jsonl")
    records_by_task = {
        (str(record.get("domain", "")), str(record.get("task_id", ""))): record
        for record in records
    }
    domain_dbs = _load_domain_dbs(benchmark_dir)

    feasibility_rows: list[dict[str, Any]] = []
    for missing in residual_result["missing_rows"]:
        record = records_by_task.get((missing["domain"], missing["task_id"]), {})
        prompt_text = _task_prompt_text(record)
        feasibility_rows.append(
            classify_missing_reference(
                run_id=run_id,
                missing_row=missing,
                domain_db=domain_dbs.get(str(missing["domain"]), {}),
                prompt_text=prompt_text,
            )
        )

    summary = _summary(
        run_id=run_id,
        run_dir=run_dir,
        benchmark_dir=benchmark_dir,
        residual_summary=residual_result["summary"],
        feasibility_rows=feasibility_rows,
    )
    return {"summary": summary, "feasibility_rows": feasibility_rows}


def classify_missing_reference(
    *,
    run_id: str,
    missing_row: dict[str, Any],
    domain_db: dict[str, Any],
    prompt_text: str,
) -> dict[str, Any]:
    domain = str(missing_row.get("domain", ""))
    tool = str(missing_row.get("tool", ""))
    args = json.loads(str(missing_row.get("args_json") or "{}"))
    visibility = str(missing_row.get("visibility", ""))
    db_checked = domain == "retail"
    schema_example_present = _schema_example_present(args, prompt_text)

    db_entity_exists = False
    invalid_reason = ""
    if domain == "retail":
        db_entity_exists, invalid_reason = _retail_reference_exists(tool, args, domain_db)
        if db_entity_exists:
            feasibility = (
                "valid_visible_reference"
                if visibility in {"complete_visible", "partial_visible"}
                else "valid_hidden_reference"
            )
        elif schema_example_present and visibility == "hidden":
            feasibility = "invalid_schema_example_reference"
        else:
            feasibility = "invalid_reference_argument"
    else:
        feasibility = "unchecked_tool_or_domain"
        invalid_reason = "no_static_feasibility_checker_for_domain"

    return {
        "run_id": run_id,
        "source_run_id": str(missing_row.get("source_run_id", "")),
        "domain": domain,
        "task_id": str(missing_row.get("task_id", "")),
        "reference_index": int(missing_row.get("reference_index", 0)),
        "event_id": str(missing_row.get("event_id", "")),
        "tool": tool,
        "args_json": json.dumps(args, sort_keys=True),
        "visibility": visibility,
        "feasibility": feasibility,
        "invalid_reason": invalid_reason,
        "db_entity_exists": db_entity_exists,
        "schema_example_present": schema_example_present,
        "db_checked": db_checked,
    }


def _retail_reference_exists(tool: str, args: dict[str, Any], db: dict[str, Any]) -> tuple[bool, str]:
    products = dict(db.get("products") or {})
    orders = dict(db.get("orders") or {})
    users = dict(db.get("users") or {})

    if tool == "get_product_details":
        product_id = str(args.get("product_id", ""))
        return (product_id in products, "" if product_id in products else "product_id_not_in_retail_db")
    if tool == "get_order_details":
        order_id = str(args.get("order_id", ""))
        return (order_id in orders, "" if order_id in orders else "order_id_not_in_retail_db")
    if tool == "get_user_details":
        user_id = str(args.get("user_id", ""))
        return (user_id in users, "" if user_id in users else "user_id_not_in_retail_db")
    if tool == "find_user_id_by_name_zip":
        target = (
            str(args.get("first_name", "")),
            str(args.get("last_name", "")),
            str(args.get("zip", "")),
        )
        for user in users.values():
            name = dict(user.get("name") or {})
            address = dict(user.get("address") or {})
            candidate = (
                str(name.get("first_name", "")),
                str(name.get("last_name", "")),
                str(address.get("zip", "")),
            )
            if candidate == target:
                return True, ""
        return False, "user_name_zip_not_in_retail_db"
    if tool == "return_delivered_order_items":
        return _retail_return_reference_exists(args, orders, users)
    return False, f"unsupported_retail_tool:{tool}"


def _retail_return_reference_exists(
    args: dict[str, Any],
    orders: dict[str, Any],
    users: dict[str, Any],
) -> tuple[bool, str]:
    order_id = str(args.get("order_id", ""))
    order = orders.get(order_id)
    if not isinstance(order, dict):
        return False, "order_id_not_in_retail_db"
    if str(order.get("status", "")) != "delivered":
        return False, "order_not_delivered"
    requested_items = [str(item) for item in args.get("item_ids") or []]
    order_items = [
        str(item.get("item_id", ""))
        for item in order.get("items") or []
        if isinstance(item, dict)
    ]
    if Counter(requested_items) - Counter(order_items):
        return False, "return_item_ids_not_in_order"
    user = users.get(str(order.get("user_id", "")))
    payment_methods = dict((user or {}).get("payment_methods") or {})
    payment_method_id = str(args.get("payment_method_id", ""))
    if payment_method_id not in payment_methods:
        return False, "payment_method_id_not_in_user_record"
    return True, ""


def _schema_example_present(args: dict[str, Any], prompt_text: str) -> bool:
    if not prompt_text:
        return False
    return any(value in prompt_text for value in _string_values(args))


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_string_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_string_values(item))
        return values
    return []


def _task_prompt_text(record: dict[str, Any]) -> str:
    paths = str((record.get("task_row") or {}).get("step_prompt_paths", "")).split("|")
    parts: list[str] = []
    for path_text in paths:
        if not path_text:
            continue
        path = Path(path_text)
        if path.exists():
            parts.append(path.read_text(errors="replace"))
    return "\n".join(parts)


def _load_domain_dbs(benchmark_dir: Path) -> dict[str, dict[str, Any]]:
    dbs: dict[str, dict[str, Any]] = {}
    domain_root = benchmark_dir / "data" / "tau2" / "domains"
    for path in domain_root.glob("*/db.json"):
        try:
            dbs[path.parent.name] = json.loads(path.read_text())
        except json.JSONDecodeError:
            dbs[path.parent.name] = {}
    return dbs


def _summary(
    *,
    run_id: str,
    run_dir: Path,
    benchmark_dir: Path,
    residual_summary: dict[str, Any],
    feasibility_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    feasibility_counts = Counter(str(row["feasibility"]) for row in feasibility_rows)
    invalid_rows = [
        row
        for row in feasibility_rows
        if str(row["feasibility"]).startswith("invalid_")
    ]
    return {
        "run_id": run_id,
        "analysis": "saved tau2 missing-reference feasibility audit",
        "source_run": residual_summary.get("source_run"),
        "run_dir": str(run_dir),
        "benchmark_dir": str(benchmark_dir),
        "no_dataset_sync": True,
        "no_model_execution": True,
        "no_tool_execution": True,
        "inspects_benchmark_db_and_hidden_references": True,
        "missing_reference_actions": len(feasibility_rows),
        "feasibility_counts": dict(sorted(feasibility_counts.items())),
        "invalid_reference_actions": len(invalid_rows),
        "schema_example_only_reference_actions": feasibility_counts[
            "invalid_schema_example_reference"
        ],
        "valid_hidden_reference_actions": feasibility_counts["valid_hidden_reference"],
        "residual_input_summary": residual_summary,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "This audit reads saved task-gateway artifacts plus the local tau2 benchmark DB.",
            "It is intentionally not a prompt input: hidden reference values and DB-only checks are used only to classify residual failures after the run.",
            "A schema-example-only reference must not be converted into a state-grounded hint or model authority source.",
        ],
    }


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(run_dir: Path, benchmark_dir: Path) -> str:
    lines = ["path,sha256,bytes"]
    for child in (
        run_dir / "samples.jsonl",
        run_dir / "task_gateway_summary.json",
        benchmark_dir / "data" / "tau2" / "domains" / "retail" / "db.json",
        benchmark_dir / "data" / "tau2" / "domains" / "retail" / "tasks.json",
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


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
