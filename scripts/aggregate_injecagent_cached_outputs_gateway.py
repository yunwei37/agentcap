"""Aggregate IntentCap gateway results over InjecAgent cached model outputs.

This script broadens the single-output R017 experiment. It discovers released
InjecAgent result directories inside the official archive, runs each complete
directory/setting through the cached-output LiveToolGateway adapter, and writes
compact per-result summaries instead of per-event traces.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.live_gateway import LiveToolGateway

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_injecagent_cached_outputs_gateway as cached_runner


REQUIRED_BY_SETTING = {
    "base": {
        "test_cases_dh_base.json",
        "test_cases_ds_base.json",
    },
    "enhanced": {
        "test_cases_dh_enhanced.json",
        "test_cases_ds_enhanced.json",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate cached InjecAgent outputs through LiveToolGateway")
    parser.add_argument("--results-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--setting", choices=["base", "enhanced", "all"], default="all")
    parser.add_argument("--limit-result-dirs", type=int, default=None)
    parser.add_argument(
        "--include-counterfactual-stage2",
        action="store_true",
        help="Include cached data-stealing stage-2 outputs as counterfactual blocked events.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    settings = ["base", "enhanced"] if args.setting == "all" else [args.setting]
    discovered = discover_result_dirs(args.results_zip)
    selected_dirs = discovered["complete_result_dirs"][args.start_index:]
    if args.limit_result_dirs is not None:
        selected_dirs = selected_dirs[: args.limit_result_dirs]

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for model_result_dir in selected_dirs:
        for setting in settings:
            try:
                rows.append(
                    run_one(
                        args.results_zip,
                        model_result_dir,
                        setting=setting,
                        include_counterfactual_stage2=args.include_counterfactual_stage2,
                    )
                )
                gc.collect()
            except Exception as exc:  # pragma: no cover - for artifact drift, not unit path
                errors.append(
                    {
                        "model_result_dir": model_result_dir,
                        "setting": setting,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    aggregate = aggregate_rows(
        rows,
        discovered=discovered,
        results_zip=args.results_zip,
        settings=settings,
        include_counterfactual_stage2=args.include_counterfactual_stage2,
        limit_result_dirs=args.limit_result_dirs,
        start_index=args.start_index,
        errors=errors,
    )

    (args.output_dir / "aggregate_summary.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    (args.output_dir / "per_result_summary.json").write_text(json.dumps(rows, indent=2, sort_keys=True))
    (args.output_dir / "discovered_result_dirs.json").write_text(json.dumps(discovered, indent=2, sort_keys=True))
    (args.output_dir / "errors.json").write_text(json.dumps(errors, indent=2, sort_keys=True))
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


def discover_result_dirs(results_zip: Path) -> dict[str, Any]:
    by_dir: dict[str, set[str]] = {}
    with zipfile.ZipFile(results_zip) as zf:
        for name in zf.namelist():
            if "/test_cases_" not in name or not name.endswith(".json"):
                continue
            model_result_dir, filename = name.rsplit("/", 1)
            by_dir.setdefault(model_result_dir, set()).add(filename)

    complete: list[str] = []
    incomplete: list[dict[str, Any]] = []
    for model_result_dir, filenames in sorted(by_dir.items()):
        missing = sorted(
            filename
            for required in REQUIRED_BY_SETTING.values()
            for filename in required
            if filename not in filenames
        )
        if missing:
            incomplete.append(
                {
                    "model_result_dir": model_result_dir,
                    "missing": missing,
                    "present": sorted(filenames),
                }
            )
        else:
            complete.append(model_result_dir)

    return {
        "result_dir_count": len(by_dir),
        "complete_result_dir_count": len(complete),
        "incomplete_result_dir_count": len(incomplete),
        "complete_result_dirs": complete,
        "incomplete_result_dirs": incomplete,
    }


def run_one(
    results_zip: Path,
    model_result_dir: str,
    *,
    setting: str,
    include_counterfactual_stage2: bool,
) -> dict[str, Any]:
    loaded = cached_runner._load_cached_outputs(
        results_zip,
        model_result_dir,
        setting=setting,
        attack_family="all",
    )
    trace = cached_runner._trace_from_cached_outputs(
        loaded,
        include_counterfactual_stage2=include_counterfactual_stage2,
    )
    callable_invocations: list[dict[str, Any]] = []
    tools = cached_runner._tool_registry(trace, callable_invocations)
    gateway = LiveToolGateway(trace, tools)
    records = gateway.run_events()
    return summarize_one(
        loaded,
        trace,
        records,
        callable_invocations,
        gateway.summary(records),
        tools,
        model_result_dir=model_result_dir,
        setting=setting,
        include_counterfactual_stage2=include_counterfactual_stage2,
    )


def summarize_one(
    loaded: list[dict[str, Any]],
    trace: dict[str, Any],
    records: list[dict[str, Any]],
    callable_invocations: list[dict[str, Any]],
    gateway_summary: dict[str, Any],
    tools: dict[str, Any],
    *,
    model_result_dir: str,
    setting: str,
    include_counterfactual_stage2: bool,
) -> dict[str, Any]:
    event_by_id = {str(event.get("id", "")): event for event in trace.get("events", [])}
    case_family_counts = Counter()
    stage1_eval_counts = Counter()
    stage2_eval_counts = Counter()
    attempted_event_type_counts = Counter()
    executed_event_type_counts = Counter()
    blocked_event_type_counts = Counter()
    blocked_mode_counts = Counter()
    executed_mode_counts = Counter()
    counterfactual_attempts = 0
    registered_executed = 0
    registered_blocked = 0

    for loaded_record in loaded:
        item = loaded_record["item"]
        family = str(loaded_record["family"])
        case_family_counts[family] += 1
        stage1_eval_counts[str(item.get("eval", "missing"))] += 1
        if family == "data_stealing":
            stage2_eval_counts[str(item.get("eval Step 2", "missing"))] += 1

    for record in records:
        decision = record.get("decision", {})
        event = event_by_id.get(str(decision.get("event_id", "")), {})
        event_type = str(event.get("intentcap_event_type", "unknown"))
        mode = str(event.get("mode", "unknown"))
        obj = str(decision.get("object", ""))
        attempted_event_type_counts[event_type] += 1
        counterfactual_attempts += int(bool(event.get("counterfactual")))
        if record.get("executed"):
            executed_event_type_counts[event_type] += 1
            executed_mode_counts[mode] += 1
            registered_executed += int(obj in tools)
        else:
            blocked_event_type_counts[event_type] += 1
            blocked_mode_counts[mode] += 1
            registered_blocked += int(obj in tools)

    return {
        "model_result_dir": model_result_dir,
        "setting": setting,
        "include_counterfactual_stage2": include_counterfactual_stage2,
        "full_case_coverage": len(loaded) == 1054,
        "cases": len(loaded),
        "case_family_counts": dict(sorted(case_family_counts.items())),
        "cached_eval_counts": {
            "stage1": dict(sorted(stage1_eval_counts.items())),
            "stage2": dict(sorted(stage2_eval_counts.items())),
        },
        "attempted_events": gateway_summary["attempted_events"],
        "executed_events": gateway_summary["executed_events"],
        "blocked_events": gateway_summary["blocked_events"],
        "tool_errors": gateway_summary["tool_errors"],
        "registered_tools": len(tools),
        "registered_executed_events": registered_executed,
        "registered_blocked_events": registered_blocked,
        "callable_invocations": len(callable_invocations),
        "missing_tool_events": sum(
            1 for record in records if record.get("decision", {}).get("action") == "missing_tool"
        ),
        "counterfactual_attempts": counterfactual_attempts,
        "attempted_event_type_counts": dict(sorted(attempted_event_type_counts.items())),
        "executed_event_type_counts": dict(sorted(executed_event_type_counts.items())),
        "blocked_event_type_counts": dict(sorted(blocked_event_type_counts.items())),
        "executed_mode_counts": dict(sorted(executed_mode_counts.items())),
        "blocked_mode_counts": dict(sorted(blocked_mode_counts.items())),
    }


def aggregate_rows(
    rows: list[dict[str, Any]],
    *,
    discovered: dict[str, Any],
    results_zip: Path,
    settings: list[str],
    include_counterfactual_stage2: bool,
    limit_result_dirs: int | None,
    start_index: int,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    totals = Counter()
    settings_seen = Counter()
    stage1_eval_counts = Counter()
    stage2_eval_counts = Counter()
    attempted_event_type_counts = Counter()
    executed_event_type_counts = Counter()
    blocked_event_type_counts = Counter()
    blocked_mode_counts = Counter()
    executed_mode_counts = Counter()
    incomplete_case_rows = []

    for row in rows:
        settings_seen[str(row["setting"])] += 1
        for key in [
            "cases",
            "attempted_events",
            "executed_events",
            "blocked_events",
            "tool_errors",
            "registered_executed_events",
            "registered_blocked_events",
            "callable_invocations",
            "missing_tool_events",
            "counterfactual_attempts",
        ]:
            totals[key] += int(row.get(key, 0))
        stage1_eval_counts.update(row["cached_eval_counts"]["stage1"])
        stage2_eval_counts.update(row["cached_eval_counts"]["stage2"])
        attempted_event_type_counts.update(row["attempted_event_type_counts"])
        executed_event_type_counts.update(row["executed_event_type_counts"])
        blocked_event_type_counts.update(row["blocked_event_type_counts"])
        blocked_mode_counts.update(row["blocked_mode_counts"])
        executed_mode_counts.update(row["executed_mode_counts"])
        if not row.get("full_case_coverage"):
            incomplete_case_rows.append(
                {
                    "model_result_dir": row["model_result_dir"],
                    "setting": row["setting"],
                    "cases": row["cases"],
                }
            )

    return {
        "source": {
            "results_zip": str(results_zip),
            "results_zip_sha256": cached_runner._sha256(results_zip),
            "settings": settings,
            "include_counterfactual_stage2": include_counterfactual_stage2,
            "limit_result_dirs": limit_result_dirs,
            "start_index": start_index,
        },
        "discovery": {
            "result_dir_count": discovered["result_dir_count"],
            "complete_result_dir_count": discovered["complete_result_dir_count"],
            "incomplete_result_dir_count": discovered["incomplete_result_dir_count"],
        },
        "processed_result_sets": len(rows),
        "settings_seen": dict(sorted(settings_seen.items())),
        "errors": errors,
        "error_count": len(errors),
        "incomplete_case_row_count": len(incomplete_case_rows),
        "incomplete_case_rows": incomplete_case_rows,
        "totals": dict(sorted(totals.items())),
        "cached_eval_counts": {
            "stage1": dict(sorted(stage1_eval_counts.items())),
            "stage2": dict(sorted(stage2_eval_counts.items())),
        },
        "attempted_event_type_counts": dict(sorted(attempted_event_type_counts.items())),
        "executed_event_type_counts": dict(sorted(executed_event_type_counts.items())),
        "blocked_event_type_counts": dict(sorted(blocked_event_type_counts.items())),
        "executed_mode_counts": dict(sorted(executed_mode_counts.items())),
        "blocked_mode_counts": dict(sorted(blocked_mode_counts.items())),
    }


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
