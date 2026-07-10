"""Replay tau2 reference actions through compiler-generated leases.

This is a bridge between the non-evaluation-task-JSON lease compiler corpus and
the runtime checker. It consumes saved compiler output, lowers generated leases
to IntentCap checker leases, then replays tau2 assistant reference actions
through TraceGateway. It does not run a model, execute tau2 tools, call reward
functions, use APIs, or sync datasets. Reference actions are used only as
post-hoc replay events.
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


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from intentcap.gateway import TraceGateway  # noqa: E402
from probe_tau2_bench import _load_json_list  # noqa: E402
from run_tau2_local_llm_task_gateway import (  # noqa: E402
    TRUSTED_TASK_INTENT,
    _reference_actions_by_requestor,
)
from run_tau2_local_llm_visible_lease_compiler import (  # noqa: E402
    DEFAULT_DOMAINS,
    _parse_assistant_tools,
)


TASK_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "source_parse_ok",
    "source_visible_arg_repairs",
    "active_leases",
    "reference_actions",
    "gateway_allowed_reference_actions",
    "gateway_blocked_reference_actions",
    "allowed_with_all_reference_args_constrained",
    "allowed_with_broad_or_runtime_args",
    "blocked_broad_or_runtime_policy",
    "blocked_missing_tool",
    "blocked_constraint_mismatch",
    "exposed_objects",
]
LEASE_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "lease_id",
    "tool",
    "valid_tool",
    "active",
    "inactive_reason",
    "object",
    "constrained_args",
    "broad_or_runtime_args",
    "argument_policy_json",
    "intent_evidence",
]
ACTION_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "action_id",
    "index",
    "tool",
    "args_json",
    "gateway_allowed",
    "gateway_reason",
    "lease_id",
    "coverage_class",
    "missing_reference_arg_constraints",
    "reward_basis",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay tau2 reference actions through compiler-generated leases"
    )
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--source-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R075")
    parser.add_argument("--domains", nargs="*", default=list(DEFAULT_DOMAINS))
    parser.add_argument("--max-tasks-per-domain", type=int, default=5)
    parser.add_argument(
        "--require-all-tool-args-constrained",
        action="store_true",
        help=(
            "Only activate compiler leases whose every declared tool argument has "
            "an exact equals_any policy. Broad/runtime policies become inactive."
        ),
    )
    args = parser.parse_args()

    result = replay(
        benchmark_dir=args.benchmark_dir,
        source_run_dir=args.source_run_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
        domains=tuple(args.domains),
        max_tasks_per_domain=args.max_tasks_per_domain,
        require_all_tool_args_constrained=args.require_all_tool_args_constrained,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def replay(
    *,
    benchmark_dir: Path,
    source_run_dir: Path,
    output_dir: Path,
    run_id: str,
    domains: tuple[str, ...] = DEFAULT_DOMAINS,
    max_tasks_per_domain: int | None = 5,
    require_all_tool_args_constrained: bool = False,
) -> dict[str, Any]:
    data_root = benchmark_dir / "data" / "tau2" / "domains"
    src_root = benchmark_dir / "src" / "tau2" / "domains"
    records = _load_source_records(source_run_dir / "samples.jsonl")
    source_summary = _load_json_if_exists(source_run_dir / "llm_visible_lease_compiler_summary.json")
    domain_names = [
        domain
        for domain in domains
        if (data_root / domain / "tasks.json").exists()
    ]
    tools_by_domain = {
        domain: {
            tool.name: tool
            for tool in _parse_assistant_tools(src_root / domain / "tools.py", domain=domain)
        }
        for domain in domain_names
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    task_rows: list[dict[str, Any]] = []
    lease_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    coverage_counter: Counter[str] = Counter()
    domain_counters: dict[str, Counter[str]] = defaultdict(Counter)

    for domain in domain_names:
        raw_tasks = _load_json_list(data_root / domain / "tasks.json")
        if max_tasks_per_domain is not None:
            raw_tasks = raw_tasks[:max_tasks_per_domain]
        for raw_task in raw_tasks:
            task_id = str(raw_task.get("id", ""))
            criteria = raw_task.get("evaluation_criteria") or {}
            reference_actions = _reference_actions_by_requestor(
                domain,
                task_id,
                criteria,
                requestor="assistant",
            )
            if not reference_actions:
                continue
            record = records.get((domain, task_id), {})
            model_json = _selected_model_json(record)
            trace, task_lease_rows, lease_meta = build_compiler_trace(
                run_id=run_id,
                domain=domain,
                task_id=task_id,
                reference_actions=reference_actions,
                model_json=model_json,
                tools_by_name=tools_by_domain.get(domain, {}),
                require_all_tool_args_constrained=require_all_tool_args_constrained,
            )
            gateway = TraceGateway(trace)
            events = [
                _reference_event(domain, task_id, action)
                for action in reference_actions
            ]
            decisions = [gateway.authorize(event).to_dict() for event in events]
            task_counts: Counter[str] = Counter()
            for action, event, decision in zip(reference_actions, events, decisions, strict=True):
                row = _action_row(
                    run_id=run_id,
                    action=action,
                    event=event,
                    decision=decision,
                    lease_meta=lease_meta,
                    has_tool_lease=_has_tool_lease(lease_meta, action.name),
                    has_inactive_broad_tool_lease=_has_tool_lease(
                        lease_meta,
                        action.name,
                        active=False,
                        inactive_reason="broad_or_runtime_args",
                        event_args=event["args"],
                        require_constrained_args_match=True,
                    ),
                )
                action_rows.append(row)
                coverage_class = str(row["coverage_class"])
                coverage_counter[coverage_class] += 1
                domain_counters[domain][coverage_class] += 1
                domain_counters[domain]["reference_actions"] += 1
                task_counts[coverage_class] += 1
            lease_rows.extend(task_lease_rows)
            task_rows.append(
                {
                    "run_id": run_id,
                    "domain": domain,
                    "task_id": task_id,
                    "source_parse_ok": bool((record.get("task_row") or {}).get("parse_ok", False)),
                    "source_visible_arg_repairs": int(record.get("visible_arg_repairs") or 0),
                    "active_leases": len(trace["leases"]),
                    "reference_actions": len(reference_actions),
                    "gateway_allowed_reference_actions": (
                        task_counts["allowed_all_reference_args_constrained"]
                        + task_counts["allowed_broad_or_runtime_args"]
                    ),
                    "gateway_blocked_reference_actions": len(reference_actions)
                    - task_counts["allowed_all_reference_args_constrained"]
                    - task_counts["allowed_broad_or_runtime_args"],
                    "allowed_with_all_reference_args_constrained": task_counts[
                        "allowed_all_reference_args_constrained"
                    ],
                    "allowed_with_broad_or_runtime_args": task_counts[
                        "allowed_broad_or_runtime_args"
                    ],
                    "blocked_broad_or_runtime_policy": task_counts[
                        "blocked_broad_or_runtime_policy"
                    ],
                    "blocked_missing_tool": task_counts["blocked_missing_tool"],
                    "blocked_constraint_mismatch": task_counts[
                        "blocked_constraint_mismatch"
                    ],
                    "exposed_objects": len(gateway.exposed_objects()),
                }
            )

    summary = summarize(
        run_id=run_id,
        benchmark_dir=benchmark_dir,
        source_run_dir=source_run_dir,
        source_summary=source_summary,
        domains=domain_names,
        max_tasks_per_domain=max_tasks_per_domain,
        require_all_tool_args_constrained=require_all_tool_args_constrained,
        task_rows=task_rows,
        lease_rows=lease_rows,
        action_rows=action_rows,
        coverage_counter=coverage_counter,
        domain_counters=domain_counters,
    )

    (output_dir / "compiler_gateway_replay_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    _write_rows(output_dir / "task_results.csv", task_rows, TASK_FIELDS)
    _write_rows(output_dir / "lease_results.csv", lease_rows, LEASE_FIELDS)
    _write_rows(output_dir / "action_results.csv", action_rows, ACTION_FIELDS)
    (output_dir / "command.txt").write_text(_command_text())
    return {
        "summary": summary,
        "task_rows": task_rows,
        "lease_rows": lease_rows,
        "action_rows": action_rows,
    }


def build_compiler_trace(
    *,
    run_id: str,
    domain: str,
    task_id: str,
    reference_actions: list[Any],
    model_json: dict[str, Any] | None,
    tools_by_name: dict[str, Any],
    require_all_tool_args_constrained: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    decisions = sorted({f"{domain}.{action.name}.tool_choice" for action in reference_actions})
    leases: list[dict[str, Any]] = []
    lease_rows: list[dict[str, Any]] = []
    lease_meta: dict[str, dict[str, Any]] = {}
    model_leases = model_json.get("leases", []) if isinstance(model_json, dict) else []
    for index, lease in enumerate(model_leases):
        if not isinstance(lease, dict):
            continue
        tool_name = str(lease.get("tool", ""))
        tool = tools_by_name.get(tool_name)
        valid_tool = tool is not None
        lease_id = f"compiler:{domain}:{task_id}:{index}:{tool_name}"
        object_name = f"tau2.{domain}.assistant.{tool_name}"
        argument_policy = lease.get("argument_policy")
        if not isinstance(argument_policy, dict):
            argument_policy = {}
        arg_constraints, constrained_args, broad_args = _lower_argument_policy(
            argument_policy,
            tuple(tool.arguments) if tool else (),
        )
        active = bool(valid_tool)
        inactive_reason = ""
        if not valid_tool:
            active = False
            inactive_reason = "invalid_tool"
        elif require_all_tool_args_constrained and broad_args:
            active = False
            inactive_reason = "broad_or_runtime_args"
        if active:
            leases.append(
                {
                    "id": lease_id,
                    "op": "tool.call",
                    "object": object_name,
                    "args": arg_constraints,
                    "control_may_depend_on": [TRUSTED_TASK_INTENT],
                    "data_may_depend_on": [TRUSTED_TASK_INTENT],
                }
            )
            lease_meta[lease_id] = {
                "tool": tool_name,
                "object": object_name,
                "arg_constraints": arg_constraints,
                "constrained_args": set(constrained_args),
                "broad_or_runtime_args": set(broad_args),
                "active": active,
                "inactive_reason": inactive_reason,
            }
        elif valid_tool:
            lease_meta[lease_id] = {
                "tool": tool_name,
                "object": object_name,
                "arg_constraints": arg_constraints,
                "constrained_args": set(constrained_args),
                "broad_or_runtime_args": set(broad_args),
                "active": active,
                "inactive_reason": inactive_reason,
            }
        lease_rows.append(
            {
                "run_id": run_id,
                "domain": domain,
                "task_id": task_id,
                "lease_id": lease_id,
                "tool": tool_name,
                "valid_tool": valid_tool,
                "active": active,
                "inactive_reason": inactive_reason,
                "object": object_name if valid_tool else "",
                "constrained_args": "|".join(constrained_args),
                "broad_or_runtime_args": "|".join(broad_args),
                "argument_policy_json": json.dumps(argument_policy, sort_keys=True),
                "intent_evidence": str(lease.get("intent_evidence", "")),
            }
        )
    return (
        {
            "labels": {
                TRUSTED_TASK_INTENT: {
                    "allowed": {
                        "tool_select": decisions,
                    }
                }
            },
            "leases": leases,
            "events": [],
            "metadata": {
                "source": "tau2 compiler-generated leases gateway replay",
                "domain": domain,
                "task_id": task_id,
                "note": (
                    "Compiler leases come from saved non-evaluation-task-JSON "
                    "model output; reference actions are replay events only."
                ),
            },
        },
        lease_rows,
        lease_meta,
    )


def _lower_argument_policy(
    argument_policy: dict[str, Any],
    tool_arguments: tuple[str, ...],
) -> tuple[dict[str, Any], list[str], list[str]]:
    constraints: dict[str, Any] = {}
    constrained_args: list[str] = []
    broad_args: list[str] = []
    for arg in tool_arguments:
        policy = argument_policy.get(arg)
        if not isinstance(policy, dict):
            broad_args.append(arg)
            continue
        mode = str(policy.get("mode", ""))
        values = policy.get("values")
        if mode == "equals_any" and isinstance(values, list) and values:
            constraints[arg] = {"one_of": values}
            constrained_args.append(arg)
        else:
            broad_args.append(arg)
    return constraints, sorted(constrained_args), sorted(broad_args)


def _reference_event(domain: str, task_id: str, action: Any) -> dict[str, Any]:
    return {
        "id": action.event_id,
        "op": "tool.call",
        "object": action.object_name,
        "args": dict(action.args),
        "decision": f"{domain}.{action.name}.tool_choice",
        "mode": "tool_select",
        "control_provenance": [TRUSTED_TASK_INTENT],
        "data_provenance": [TRUSTED_TASK_INTENT],
        "intentcap_event_type": "tau2_reference_action_replay",
        "domain": domain,
        "task_id": task_id,
        "logical_tool": action.name,
    }


def _action_row(
    *,
    run_id: str,
    action: Any,
    event: dict[str, Any],
    decision: dict[str, Any],
    lease_meta: dict[str, dict[str, Any]],
    has_tool_lease: bool,
    has_inactive_broad_tool_lease: bool,
) -> dict[str, Any]:
    allowed = bool(decision.get("allowed"))
    lease_id = str(decision.get("lease_id") or "")
    missing_constraints: list[str] = []
    if allowed:
        meta = lease_meta.get(lease_id, {})
        constrained_args = set(meta.get("constrained_args", set()))
        missing_constraints = sorted(set(action.args) - constrained_args)
        coverage_class = (
            "allowed_all_reference_args_constrained"
            if not missing_constraints
            else "allowed_broad_or_runtime_args"
        )
    elif has_inactive_broad_tool_lease:
        coverage_class = "blocked_broad_or_runtime_policy"
    elif has_tool_lease:
        coverage_class = "blocked_constraint_mismatch"
    else:
        coverage_class = "blocked_missing_tool"
    return {
        "run_id": run_id,
        "domain": action.domain,
        "task_id": action.task_id,
        "action_id": action.action_id,
        "index": action.index,
        "tool": action.name,
        "args_json": json.dumps(event["args"], sort_keys=True),
        "gateway_allowed": allowed,
        "gateway_reason": str(decision.get("reason", "")),
        "lease_id": lease_id,
        "coverage_class": coverage_class,
        "missing_reference_arg_constraints": "|".join(missing_constraints),
        "reward_basis": "|".join(action.reward_basis),
    }


def _has_tool_lease(
    lease_meta: dict[str, dict[str, Any]],
    tool: str,
    *,
    active: bool | None = None,
    inactive_reason: str | None = None,
    event_args: dict[str, Any] | None = None,
    require_constrained_args_match: bool = False,
) -> bool:
    for meta in lease_meta.values():
        if str(meta.get("tool", "")) != tool:
            continue
        if active is not None and bool(meta.get("active")) != active:
            continue
        if inactive_reason is not None and str(meta.get("inactive_reason", "")) != inactive_reason:
            continue
        if require_constrained_args_match and not _constrained_args_match_event(
            meta,
            event_args or {},
        ):
            continue
        return True
    return False


def _constrained_args_match_event(
    lease_meta: dict[str, Any],
    event_args: dict[str, Any],
) -> bool:
    constraints = lease_meta.get("arg_constraints", {})
    if not isinstance(constraints, dict):
        return False
    for arg, predicate in constraints.items():
        if not isinstance(predicate, dict):
            return False
        values = predicate.get("one_of")
        if not isinstance(values, list) or event_args.get(arg) not in values:
            return False
    return True


def _selected_model_json(record: dict[str, Any]) -> dict[str, Any] | None:
    repaired = record.get("repaired_model_json")
    if isinstance(repaired, dict):
        return repaired
    parsed = record.get("parsed_model_json")
    return parsed if isinstance(parsed, dict) else None


def summarize(
    *,
    run_id: str,
    benchmark_dir: Path,
    source_run_dir: Path,
    source_summary: dict[str, Any],
    domains: list[str],
    max_tasks_per_domain: int | None,
    require_all_tool_args_constrained: bool,
    task_rows: list[dict[str, Any]],
    lease_rows: list[dict[str, Any]],
    action_rows: list[dict[str, Any]],
    coverage_counter: Counter[str],
    domain_counters: dict[str, Counter[str]],
) -> dict[str, Any]:
    reference_actions = len(action_rows)
    allowed = (
        coverage_counter["allowed_all_reference_args_constrained"]
        + coverage_counter["allowed_broad_or_runtime_args"]
    )
    return {
        "run_id": run_id,
        "benchmark": "tau2-bench",
        "benchmark_dir": str(benchmark_dir),
        "source_run_dir": str(source_run_dir),
        "source_run_id": source_summary.get("run_id", ""),
        "domains": domains,
        "max_tasks_per_domain": max_tasks_per_domain,
        "require_all_tool_args_constrained": require_all_tool_args_constrained,
        "tasks_evaluated": len(task_rows),
        "assistant_reference_actions": reference_actions,
        "active_leases_total": sum(int(row["active_leases"]) for row in task_rows),
        "valid_lease_rows_total": sum(1 for row in lease_rows if row["valid_tool"]),
        "invalid_lease_rows_total": sum(1 for row in lease_rows if not row["valid_tool"]),
        "inactive_valid_broad_lease_rows_total": sum(
            1
            for row in lease_rows
            if row["valid_tool"] and not row["active"] and row["inactive_reason"] == "broad_or_runtime_args"
        ),
        "gateway_allowed_reference_actions": allowed,
        "gateway_blocked_reference_actions": reference_actions - allowed,
        "gateway_allowed_rate": allowed / reference_actions if reference_actions else 1.0,
        "allowed_all_reference_args_constrained": coverage_counter[
            "allowed_all_reference_args_constrained"
        ],
        "allowed_broad_or_runtime_args": coverage_counter[
            "allowed_broad_or_runtime_args"
        ],
        "blocked_broad_or_runtime_policy": coverage_counter[
            "blocked_broad_or_runtime_policy"
        ],
        "blocked_missing_tool": coverage_counter["blocked_missing_tool"],
        "blocked_constraint_mismatch": coverage_counter["blocked_constraint_mismatch"],
        "coverage_class_counts": dict(sorted(coverage_counter.items())),
        "domain_counts": {
            domain: dict(sorted(counter.items()))
            for domain, counter in sorted(domain_counters.items())
        },
        "machine": platform.platform(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "source_summary_sha256": _file_digest(
            source_run_dir / "llm_visible_lease_compiler_summary.json"
        ),
        "source_samples_sha256": _file_digest(source_run_dir / "samples.jsonl"),
        "notes": [
            "Compiler leases are loaded from saved non-evaluation-task-JSON model output; repaired_model_json is preferred when present.",
            "Reference actions are used only as post-hoc replay events and are not used to synthesize leases.",
            "This run does not execute tau2 tools, run a simulator/reward loop, call a model/API, or sync datasets.",
            "allowed_all_reference_args_constrained means the matching compiler lease constrained every reference argument.",
            "allowed_broad_or_runtime_args means the checker allowed the reference event through a selected tool lease that left at least one reference argument unconstrained.",
            "blocked_broad_or_runtime_policy means an inactive compiler lease selected the reference tool and matched its constrained arguments, but strict lowering made it inactive because other tool arguments were broad/runtime.",
            "blocked_missing_tool means no compiler lease selected the reference tool.",
            "blocked_constraint_mismatch means a compiler lease selected the tool but constrained at least one argument to non-matching values.",
        ],
    }


def _load_source_records(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    if not path.exists():
        return records
    with path.open() as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            records[(str(record.get("domain", "")), str(record.get("task_id", "")))] = record
    return records


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _file_digest(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(args: list[str]) -> str:
    completed = subprocess.run(
        args,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.stdout.strip()


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
