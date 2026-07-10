"""Analyze tau2/tau3 reference-action authority breadth.

This script uses tau2/tau3 task artifacts as a utility-side substrate for
IntentCap. It does not run a model, simulator, or reward function. Instead, it
compares narrow reference-action lease candidates against broader static tool
policies over benchmark-provided evaluation actions.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_tau2_bench import (  # noqa: E402
    KNOWN_DOMAINS,
    _load_json_dict,
    _load_json_list,
    _parse_tools,
)


BASELINE_ORDER = (
    "intentcap_reference_events",
    "task_reference_tools",
    "domain_assistant_regular",
    "domain_assistant_all",
    "global_assistant_regular",
    "global_all_tools",
)

TOOL_RISK = {
    "read": 1,
    "generic": 2,
    "think": 2,
    "write": 3,
    "unknown": 2,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze tau2/tau3 authority minimization")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--domains",
        nargs="*",
        default=list(KNOWN_DOMAINS),
        help="Subset of tau2/tau3 domains to analyze.",
    )
    args = parser.parse_args()

    result = analyze(args.benchmark_dir, tuple(args.domains))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "authority_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "task_exposure.csv", result["task_exposure"])
    _write_rows(args.output_dir / "domain_baseline_summary.csv", result["domain_baseline_summary"])
    _write_rows(args.output_dir / "uncovered_reference_actions.csv", result["uncovered_reference_actions"])
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(benchmark_dir: Path, domains: tuple[str, ...] = KNOWN_DOMAINS) -> dict[str, Any]:
    data_root = benchmark_dir / "data" / "tau2" / "domains"
    src_root = benchmark_dir / "src" / "tau2" / "domains"
    domain_names = [
        domain
        for domain in domains
        if (data_root / domain).exists() or (src_root / domain).exists()
    ]
    tool_catalog = _tool_catalog(data_root, src_root, domain_names)
    tasks = _task_records(data_root, domain_names, tool_catalog)

    global_assistant_regular = {
        tool_id
        for tool_id, tool in tool_catalog.items()
        if tool["requestor"] == "assistant" and not tool["discoverable"]
    }
    global_all_tools = set(tool_catalog)

    baseline_summaries: dict[str, Any] = {}
    task_rows: list[dict[str, Any]] = []
    domain_summary_accumulator: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    uncovered_rows: list[dict[str, Any]] = []

    for baseline in BASELINE_ORDER:
        exposed_counts: list[int] = []
        extra_counts: list[int] = []
        risk_scores: list[int] = []
        covered_actions = 0
        assistant_actions = 0
        exact_event_leases = 0
        reference_tool_slots = 0
        exposed_tool_slots = 0
        extra_tool_slots = 0
        tasks_with_full_coverage = 0
        tasks_with_assistant_actions = 0
        write_tool_slots = 0
        discoverable_tool_slots = 0

        for task in tasks:
            reference_event_ids = task["assistant_reference_event_ids"]
            reference_tool_ids = task["assistant_reference_tool_ids"]
            scope = _scope_for_baseline(
                baseline,
                task,
                tool_catalog,
                global_assistant_regular,
                global_all_tools,
            )
            coverage = _covered_reference_events(baseline, task, scope)
            extra_tools = _extra_tools(baseline, scope, reference_tool_ids)
            risk_score = _scope_risk_score(baseline, task, scope, tool_catalog)
            exposed_count = _exposed_count(baseline, scope, task)

            assistant_action_count = len(reference_event_ids)
            assistant_actions += assistant_action_count
            covered_actions += coverage
            exact_event_leases += assistant_action_count if baseline == "intentcap_reference_events" else 0
            reference_tool_slots += len(reference_tool_ids)
            exposed_tool_slots += exposed_count
            extra_tool_slots += len(extra_tools)
            exposed_counts.append(exposed_count)
            extra_counts.append(len(extra_tools))
            risk_scores.append(risk_score)
            if assistant_action_count:
                tasks_with_assistant_actions += 1
            if coverage == assistant_action_count:
                tasks_with_full_coverage += 1

            scoped_tool_ids = (
                [event["tool_id"] for event in task["assistant_reference_events"]]
                if baseline == "intentcap_reference_events"
                else list(scope)
            )
            write_tool_slots += sum(
                1
                for tool_id in scoped_tool_ids
                if tool_catalog.get(tool_id, {}).get("tool_type", "unknown") == "write"
            )
            discoverable_tool_slots += sum(
                1
                for tool_id in scoped_tool_ids
                if bool(tool_catalog.get(tool_id, {}).get("discoverable", False))
            )

            task_row = {
                "baseline": baseline,
                "domain": task["domain"],
                "task_id": task["task_id"],
                "split_names": "|".join(task["split_names"]),
                "reward_basis": "|".join(task["reward_basis"]),
                "assistant_reference_actions": assistant_action_count,
                "user_reference_actions": len(task["user_reference_events"]),
                "assistant_reference_tools": len(reference_tool_ids),
                "exposed_tools": exposed_count,
                "extra_tools": len(extra_tools),
                "covered_assistant_reference_actions": coverage,
                "coverage_rate": coverage / assistant_action_count if assistant_action_count else 1.0,
                "risk_score": risk_score,
                "write_tool_slots": sum(
                    1
                    for tool_id in scoped_tool_ids
                    if tool_catalog.get(tool_id, {}).get("tool_type", "unknown") == "write"
                ),
                "discoverable_tool_slots": sum(
                    1
                    for tool_id in scoped_tool_ids
                    if bool(tool_catalog.get(tool_id, {}).get("discoverable", False))
                ),
                "required_documents": len(task["required_documents"]),
                "task_declared_user_tools": len(task["task_declared_user_tools"]),
            }
            task_rows.append(task_row)
            domain_summary_accumulator[(baseline, task["domain"])].append(task_row)

            if coverage < assistant_action_count:
                for event in task["assistant_reference_events"]:
                    if event["event_id"] not in _covered_event_ids(baseline, task, scope):
                        uncovered_rows.append(
                            {
                                "baseline": baseline,
                                "domain": task["domain"],
                                "task_id": task["task_id"],
                                "action_id": event["action_id"],
                                "name": event["name"],
                                "requestor": event["requestor"],
                                "tool_id": event["tool_id"],
                                "reward_basis": "|".join(task["reward_basis"]),
                            }
                        )

        baseline_summaries[baseline] = {
            "description": _baseline_description(baseline),
            "tasks": len(tasks),
            "tasks_with_assistant_reference_actions": tasks_with_assistant_actions,
            "tasks_with_full_assistant_reference_coverage": tasks_with_full_coverage,
            "assistant_reference_actions": assistant_actions,
            "covered_assistant_reference_actions": covered_actions,
            "assistant_reference_coverage_rate": covered_actions / assistant_actions if assistant_actions else 1.0,
            "exact_event_leases": exact_event_leases,
            "reference_tool_slots_total": reference_tool_slots,
            "exposed_tool_slots_total": exposed_tool_slots,
            "extra_tool_slots_total": extra_tool_slots,
            "mean_exposed_tools_per_task": _mean(exposed_counts),
            "median_exposed_tools_per_task": _median(exposed_counts),
            "p95_exposed_tools_per_task": _percentile(exposed_counts, 0.95),
            "max_exposed_tools_per_task": max(exposed_counts, default=0),
            "mean_extra_tools_per_task": _mean(extra_counts),
            "mean_risk_score_per_task": _mean(risk_scores),
            "write_tool_slots_total": write_tool_slots,
            "discoverable_tool_slots_total": discoverable_tool_slots,
            "event_id_checked": baseline == "intentcap_reference_events",
            "control_provenance_checked": baseline == "intentcap_reference_events",
            "argument_values_constrained": baseline in {"intentcap_reference_events", "task_reference_tools"},
        }

    intentcap_slots = baseline_summaries["intentcap_reference_events"]["exposed_tool_slots_total"]
    intentcap_risk = baseline_summaries["intentcap_reference_events"]["mean_risk_score_per_task"]
    for baseline, summary in baseline_summaries.items():
        summary["tool_slot_over_intentcap_ratio"] = (
            summary["exposed_tool_slots_total"] / intentcap_slots
            if intentcap_slots
            else 0.0
        )
        summary["extra_tool_slots_vs_intentcap"] = summary["exposed_tool_slots_total"] - intentcap_slots
        summary["mean_risk_over_intentcap"] = (
            summary["mean_risk_score_per_task"] / intentcap_risk
            if intentcap_risk
            else 0.0
        )

    domain_rows = _domain_summary_rows(domain_summary_accumulator)
    reference_actions = sum(len(task["assistant_reference_events"]) + len(task["user_reference_events"]) for task in tasks)
    assistant_unknown = sorted(
        {
            event["tool_id"]
            for task in tasks
            for event in task["assistant_reference_events"]
            if event["tool_id"] not in tool_catalog
        }
    )

    summary = {
        "benchmark": "tau2-bench / tau3-bench",
        "benchmark_dir": str(benchmark_dir),
        "domains": domain_names,
        "tasks": len(tasks),
        "tasks_with_reference_actions": sum(
            1 for task in tasks if task["assistant_reference_events"] or task["user_reference_events"]
        ),
        "tasks_with_assistant_reference_actions": sum(1 for task in tasks if task["assistant_reference_events"]),
        "reference_actions": reference_actions,
        "assistant_reference_actions": sum(len(task["assistant_reference_events"]) for task in tasks),
        "user_reference_actions": sum(len(task["user_reference_events"]) for task in tasks),
        "assistant_reference_actions_not_in_tool_catalog": len(assistant_unknown),
        "assistant_reference_actions_not_in_tool_catalog_sample": assistant_unknown[:20],
        "ordinary_assistant_tools": len(global_assistant_regular),
        "discoverable_assistant_tools": sum(
            1 for tool in tool_catalog.values() if tool["requestor"] == "assistant" and tool["discoverable"]
        ),
        "all_tool_objects": len(tool_catalog),
        "baseline_order": list(BASELINE_ORDER),
        "baselines": baseline_summaries,
        "notes": [
            "This is a reference-action authority analysis only; it does not run tau2 simulations, model APIs, rewards, or denial recovery.",
            "Assistant-reference-action coverage is the utility-side proxy because these are agent-side tool actions in benchmark labels.",
            "Reference actions are benchmark labels for expected state/action checks; they are not treated as proof that an IntentCap runtime completed the task.",
            "IntentCap reference-event leases model exact event/action leases with provenance and argument constraints, while static baselines expose broader tool scopes.",
        ],
    }
    return {
        "summary": summary,
        "task_exposure": task_rows,
        "domain_baseline_summary": domain_rows,
        "uncovered_reference_actions": uncovered_rows,
    }


def _tool_catalog(data_root: Path, src_root: Path, domains: list[str]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for domain in domains:
        src_dir = src_root / domain
        for tool in _parse_tools(src_dir / "tools.py", requestor="assistant"):
            tool_id = _tool_id(domain, tool["requestor"], tool["name"])
            catalog[tool_id] = {"domain": domain, **tool}
        for tool in _parse_tools(src_dir / "user_tools.py", requestor="user"):
            tool_id = _tool_id(domain, tool["requestor"], tool["name"])
            catalog[tool_id] = {"domain": domain, **tool}

        # Some tau2/tau3 tasks declare user-side tools in task metadata instead
        # of a separate user_tools.py module.
        task_declared_user_tools: set[str] = set()
        for task in _load_json_list(data_root / domain / "tasks.json"):
            for name in task.get("user_tools") or []:
                task_declared_user_tools.add(str(name))
        for name in sorted(task_declared_user_tools):
            tool_id = _tool_id(domain, "user", name)
            catalog.setdefault(
                tool_id,
                {
                    "domain": domain,
                    "requestor": "user",
                    "name": name,
                    "tool_type": "write",
                    "discoverable": False,
                    "argument_count": 0,
                    "arguments": "",
                    "docstring_words": 0,
                    "source_file": "task.user_tools",
                    "task_declared": True,
                },
            )
    return catalog


def _task_records(
    data_root: Path,
    domains: list[str],
    tool_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for domain in domains:
        split_membership = _split_membership(data_root / domain / "split_tasks.json")
        for task in _load_json_list(data_root / domain / "tasks.json"):
            task_id = str(task.get("id", ""))
            criteria = task.get("evaluation_criteria", {}) or {}
            reward_basis = [str(item) for item in (criteria.get("reward_basis") or [])]
            assistant_events: list[dict[str, Any]] = []
            user_events: list[dict[str, Any]] = []
            for index, action in enumerate(criteria.get("actions") or []):
                if not isinstance(action, dict):
                    continue
                requestor = str(action.get("requestor", "assistant"))
                name = str(action.get("name", ""))
                event = {
                    "event_id": f"{domain}:{task_id}:{action.get('action_id', index)}",
                    "action_id": str(action.get("action_id", index)),
                    "name": name,
                    "requestor": requestor,
                    "tool_id": _tool_id(domain, requestor, name),
                    "tool_type": tool_catalog.get(_tool_id(domain, requestor, name), {}).get("tool_type", "unknown"),
                    "argument_keys": sorted(str(key) for key in (action.get("arguments") or {})),
                }
                if requestor == "assistant":
                    assistant_events.append(event)
                else:
                    user_events.append(event)
            tasks.append(
                {
                    "domain": domain,
                    "task_id": task_id,
                    "split_names": split_membership.get(task_id, []),
                    "reward_basis": reward_basis,
                    "required_documents": [str(item) for item in (task.get("required_documents") or [])],
                    "task_declared_user_tools": [str(item) for item in (task.get("user_tools") or [])],
                    "assistant_reference_events": assistant_events,
                    "user_reference_events": user_events,
                    "assistant_reference_event_ids": {event["event_id"] for event in assistant_events},
                    "assistant_reference_tool_ids": {event["tool_id"] for event in assistant_events},
                }
            )
    return tasks


def _split_membership(path: Path) -> dict[str, list[str]]:
    memberships: dict[str, list[str]] = defaultdict(list)
    splits = _load_json_dict(path)
    for split_name, task_ids in splits.items():
        if not isinstance(task_ids, list):
            continue
        for task_id in task_ids:
            memberships[str(task_id)].append(str(split_name))
    return {task_id: sorted(names) for task_id, names in memberships.items()}


def _scope_for_baseline(
    baseline: str,
    task: dict[str, Any],
    tool_catalog: dict[str, dict[str, Any]],
    global_assistant_regular: set[str],
    global_all_tools: set[str],
) -> set[str]:
    domain = task["domain"]
    if baseline == "intentcap_reference_events":
        return set(task["assistant_reference_event_ids"])
    if baseline == "task_reference_tools":
        return set(task["assistant_reference_tool_ids"])
    if baseline == "domain_assistant_regular":
        return {
            tool_id
            for tool_id, tool in tool_catalog.items()
            if tool["domain"] == domain and tool["requestor"] == "assistant" and not tool["discoverable"]
        }
    if baseline == "domain_assistant_all":
        return {
            tool_id
            for tool_id, tool in tool_catalog.items()
            if tool["domain"] == domain and tool["requestor"] == "assistant"
        }
    if baseline == "global_assistant_regular":
        return set(global_assistant_regular)
    if baseline == "global_all_tools":
        return set(global_all_tools)
    raise ValueError(f"unknown baseline: {baseline}")


def _covered_reference_events(baseline: str, task: dict[str, Any], scope: set[str]) -> int:
    return len(_covered_event_ids(baseline, task, scope))


def _covered_event_ids(baseline: str, task: dict[str, Any], scope: set[str]) -> set[str]:
    covered: set[str] = set()
    for event in task["assistant_reference_events"]:
        if baseline == "intentcap_reference_events":
            if event["event_id"] in scope:
                covered.add(event["event_id"])
        elif event["tool_id"] in scope:
            covered.add(event["event_id"])
    return covered


def _extra_tools(baseline: str, scope: set[str], reference_tool_ids: set[str]) -> set[str]:
    if baseline == "intentcap_reference_events":
        return set()
    return set(scope) - set(reference_tool_ids)


def _scope_risk_score(
    baseline: str,
    task: dict[str, Any],
    scope: set[str],
    tool_catalog: dict[str, dict[str, Any]],
) -> int:
    if baseline == "intentcap_reference_events":
        return sum(_risk_for_event(event, tool_catalog) for event in task["assistant_reference_events"])
    return sum(_risk_for_tool_id(tool_id, tool_catalog) for tool_id in scope)


def _risk_for_event(event: dict[str, Any], tool_catalog: dict[str, dict[str, Any]]) -> int:
    tool_type = str(tool_catalog.get(event["tool_id"], {}).get("tool_type", event.get("tool_type", "unknown")))
    return TOOL_RISK.get(tool_type, TOOL_RISK["unknown"])


def _risk_for_tool_id(tool_id: str, tool_catalog: dict[str, dict[str, Any]]) -> int:
    tool_type = str(tool_catalog.get(tool_id, {}).get("tool_type", "unknown"))
    return TOOL_RISK.get(tool_type, TOOL_RISK["unknown"])


def _exposed_count(baseline: str, scope: set[str], task: dict[str, Any]) -> int:
    if baseline == "intentcap_reference_events":
        return len(task["assistant_reference_events"])
    return len(scope)


def _domain_summary_rows(accumulator: dict[tuple[str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (baseline, domain), task_rows in sorted(accumulator.items()):
        assistant_actions = sum(int(row["assistant_reference_actions"]) for row in task_rows)
        covered = sum(int(row["covered_assistant_reference_actions"]) for row in task_rows)
        rows.append(
            {
                "baseline": baseline,
                "domain": domain,
                "tasks": len(task_rows),
                "tasks_with_assistant_reference_actions": sum(
                    1 for row in task_rows if int(row["assistant_reference_actions"]) > 0
                ),
                "assistant_reference_actions": assistant_actions,
                "covered_assistant_reference_actions": covered,
                "assistant_reference_coverage_rate": covered / assistant_actions if assistant_actions else 1.0,
                "exposed_tool_slots_total": sum(int(row["exposed_tools"]) for row in task_rows),
                "extra_tool_slots_total": sum(int(row["extra_tools"]) for row in task_rows),
                "mean_exposed_tools_per_task": _mean([int(row["exposed_tools"]) for row in task_rows]),
                "mean_extra_tools_per_task": _mean([int(row["extra_tools"]) for row in task_rows]),
                "mean_risk_score_per_task": _mean([int(row["risk_score"]) for row in task_rows]),
                "write_tool_slots_total": sum(int(row["write_tool_slots"]) for row in task_rows),
                "discoverable_tool_slots_total": sum(int(row["discoverable_tool_slots"]) for row in task_rows),
            }
        )
    return rows


def _tool_id(domain: str, requestor: str, name: str) -> str:
    return f"{domain}:{requestor}:{name}"


def _baseline_description(baseline: str) -> str:
    return {
        "intentcap_reference_events": "One exact assistant reference-action lease per benchmark action label, with event-id/provenance/argument constraints.",
        "task_reference_tools": "Per-task ACL containing the unique assistant reference-action tool names, without event-id/provenance constraints.",
        "domain_assistant_regular": "All ordinary non-discoverable assistant tools in the task domain.",
        "domain_assistant_all": "All assistant tools in the task domain, including discoverable tools.",
        "global_assistant_regular": "All ordinary non-discoverable assistant tools across analyzed domains.",
        "global_all_tools": "All parsed assistant, discoverable, user, and task-declared user tools across analyzed domains.",
    }[baseline]


def _mean(values: list[int]) -> float:
    return statistics.fmean(values) if values else 0.0


def _median(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def _percentile(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return float(ordered[index])


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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
