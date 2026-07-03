"""Run tau2/tau3 reference actions through IntentCap and tau2 evaluators.

R023 showed that exact assistant reference-action leases can invoke real tau2
toolkit callables. This script takes the next step: it builds a tau2 message
trajectory from benchmark reference actions, routes assistant actions through
LiveToolGateway, routes user actions as simulator-side actions, and scores the
result with tau2's action and environment evaluators.

This is still not a model/user-simulator run. It is an evaluator-backed replay
of benchmark reference actions that checks whether the IntentCap event shape can
reach tau2's DB/env-assertion oracle without broad domain tool exposure.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from intentcap.live_gateway import LiveToolGateway


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_tau2_bench import KNOWN_DOMAINS, _load_json_list  # noqa: E402
from run_tau2_reference_actions_live_gateway import (  # noqa: E402
    ReferenceAction,
    _install_tau2_import_shims,
    _json_default,
    build_trace,
)


TOOL_ORACLE_BASIS = {"DB", "ENV_ASSERTION", "ACTION"}
UNEVALUATED_BASIS = {"COMMUNICATE", "NL_ASSERTION"}
TASK_ROW_FIELDS = [
    "domain",
    "task_id",
    "reward_basis",
    "tool_oracle_basis",
    "unevaluated_basis",
    "tool_oracle_applicable",
    "tool_oracle_pass",
    "action_reward",
    "env_oracle_applicable",
    "env_reward",
    "db_match",
    "env_assertions",
    "env_assertions_met",
    "reference_actions",
    "assistant_reference_actions",
    "user_reference_actions",
    "assistant_gateway_allowed",
    "assistant_gateway_blocked",
    "tool_error_events",
]
EVENT_ROW_FIELDS = [
    "event_id",
    "domain",
    "task_id",
    "action_id",
    "requestor",
    "tool",
    "gateway_allowed",
    "gateway_executed",
    "tool_error",
    "reward_basis",
]
UNSUPPORTED_ROW_FIELDS = ["domain", "task_id", "reason"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay tau2/tau3 reference actions through IntentCap and tau2 evaluators"
    )
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--domains", nargs="*", default=list(KNOWN_DOMAINS))
    parser.add_argument("--max-tasks-per-domain", type=int, default=None)
    args = parser.parse_args()

    result = run(
        benchmark_dir=args.benchmark_dir,
        domains=tuple(args.domains),
        max_tasks_per_domain=args.max_tasks_per_domain,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "oracle_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True, default=_json_default)
    )
    (args.output_dir / "assistant_gateway_records.json").write_text(
        json.dumps(result["gateway_records"], indent=2, sort_keys=True, default=_json_default)
    )
    (args.output_dir / "intentcap_traces.json").write_text(
        json.dumps(result["intentcap_traces"], indent=2, sort_keys=True, default=_json_default)
    )
    _write_rows(args.output_dir / "task_oracle_results.csv", result["task_rows"], TASK_ROW_FIELDS)
    _write_rows(args.output_dir / "event_results.csv", result["event_rows"], EVENT_ROW_FIELDS)
    _write_rows(args.output_dir / "unsupported_tasks.csv", result["unsupported_rows"], UNSUPPORTED_ROW_FIELDS)
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True, default=_json_default))
    return 0


def run(
    *,
    benchmark_dir: Path,
    domains: tuple[str, ...],
    max_tasks_per_domain: int | None = None,
) -> dict[str, Any]:
    _install_tau2_import_shims(benchmark_dir)

    task_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []
    gateway_records: list[dict[str, Any]] = []
    intentcap_traces: list[dict[str, Any]] = []

    for domain in domains:
        domain_result = _run_domain(
            benchmark_dir=benchmark_dir,
            domain=domain,
            max_tasks=max_tasks_per_domain,
        )
        task_rows.extend(domain_result["task_rows"])
        event_rows.extend(domain_result["event_rows"])
        unsupported_rows.extend(domain_result["unsupported_rows"])
        gateway_records.extend(domain_result["gateway_records"])
        intentcap_traces.extend(domain_result["intentcap_traces"])

    summary = summarize(
        task_rows=task_rows,
        event_rows=event_rows,
        unsupported_rows=unsupported_rows,
        gateway_records=gateway_records,
        domains=domains,
    )
    return {
        "summary": summary,
        "task_rows": task_rows,
        "event_rows": event_rows,
        "unsupported_rows": unsupported_rows,
        "gateway_records": gateway_records,
        "intentcap_traces": intentcap_traces,
    }


def summarize(
    *,
    task_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    unsupported_rows: list[dict[str, Any]],
    gateway_records: list[dict[str, Any]],
    domains: tuple[str, ...],
) -> dict[str, Any]:
    domain_counts = Counter(row["domain"] for row in task_rows)
    basis_counts = Counter()
    for row in task_rows:
        for basis in str(row["reward_basis"]).split("|"):
            if basis:
                basis_counts[basis] += 1

    tool_oracle_applicable = [
        row for row in task_rows if str(row["tool_oracle_applicable"]) == "True"
    ]
    fully_tool_oracle_supported = [
        row for row in tool_oracle_applicable if str(row["tool_oracle_pass"]) == "True"
    ]
    env_applicable = [row for row in task_rows if str(row["env_oracle_applicable"]) == "True"]
    action_basis_tasks = [row for row in task_rows if "ACTION" in str(row["reward_basis"]).split("|")]
    unevaluated_tasks = [
        row for row in task_rows if str(row["unevaluated_basis"]) not in {"", "none"}
    ]
    gateway_allowed = sum(
        1
        for record in gateway_records
        if record.get("decision", {}).get("allowed")
    )
    gateway_blocked = len(gateway_records) - gateway_allowed
    tool_errors = sum(1 for row in event_rows if str(row["tool_error"]) == "True")
    assistant_events = sum(1 for row in event_rows if row["requestor"] == "assistant")
    user_events = sum(1 for row in event_rows if row["requestor"] == "user")

    return {
        "benchmark": "tau2-bench / tau3-bench",
        "domains_requested": list(domains),
        "domains_evaluated": sorted(domain_counts),
        "tasks_evaluated": len(task_rows),
        "unsupported_tasks": len(unsupported_rows),
        "events_replayed": len(event_rows),
        "assistant_reference_actions": assistant_events,
        "user_reference_actions_excluded_from_assistant_authority": user_events,
        "assistant_gateway_records": len(gateway_records),
        "assistant_gateway_allowed": gateway_allowed,
        "assistant_gateway_blocked": gateway_blocked,
        "tool_error_events": tool_errors,
        "tool_oracle_applicable_tasks": len(tool_oracle_applicable),
        "tool_oracle_pass_tasks": len(fully_tool_oracle_supported),
        "tool_oracle_pass_rate": (
            len(fully_tool_oracle_supported) / len(tool_oracle_applicable)
            if tool_oracle_applicable
            else 1.0
        ),
        "env_oracle_applicable_tasks": len(env_applicable),
        "env_oracle_pass_tasks": sum(1 for row in env_applicable if str(row["env_reward"]) == "1.0"),
        "action_basis_tasks": len(action_basis_tasks),
        "action_basis_pass_tasks": sum(1 for row in action_basis_tasks if str(row["action_reward"]) == "1.0"),
        "tasks_with_unevaluated_communicate_or_nl_basis": len(unevaluated_tasks),
        "reward_basis_counts": dict(sorted(basis_counts.items())),
        "tasks_by_domain": dict(sorted(domain_counts.items())),
        "notes": [
            "Assistant reference actions are checked by exact IntentCap event leases before execution.",
            "User reference actions are replayed as simulator-side actions and are not counted as assistant authority.",
            "The oracle covers tau2 ACTION, DB, and ENV_ASSERTION components; COMMUNICATE and NL_ASSERTION are reported as unevaluated.",
            "The banking_knowledge domain uses a local no-retrieval environment fallback because the official retrieval dependency is unavailable locally.",
            "This is reference-action replay through tau2 evaluators, not a model/user-simulator benchmark run.",
        ],
    }


def _run_domain(
    *,
    benchmark_dir: Path,
    domain: str,
    max_tasks: int | None,
) -> dict[str, Any]:
    task_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []
    gateway_records: list[dict[str, Any]] = []
    intentcap_traces: list[dict[str, Any]] = []

    data_dir = benchmark_dir / "data" / "tau2" / "domains" / domain
    raw_tasks = _load_json_list(data_dir / "tasks.json")
    if max_tasks is not None:
        raw_tasks = raw_tasks[:max_tasks]

    try:
        task_cls = _import_attr("tau2.data_model.tasks", "Task")
        action_evaluator = _import_attr("tau2.evaluator.evaluator_action", "ActionEvaluator")
        env_evaluator = _import_attr("tau2.evaluator.evaluator_env", "EnvironmentEvaluator")
    except Exception as exc:
        unsupported_rows.append(_unsupported_row(domain, "", f"evaluator_import_error:{type(exc).__name__}: {exc}"))
        return {
            "task_rows": task_rows,
            "event_rows": event_rows,
            "unsupported_rows": unsupported_rows,
            "gateway_records": gateway_records,
        }

    for raw_task in raw_tasks:
        task_id = str(raw_task.get("id", ""))
        try:
            task = task_cls.model_validate(raw_task)
            env_constructor = _environment_constructor(domain, task)
            trajectory_result = _reference_trajectory(domain, task, env_constructor)
            trajectory = trajectory_result["trajectory"]
            task_event_rows = trajectory_result["event_rows"]
            task_gateway_records = trajectory_result["gateway_records"]
            action_reward_info = action_evaluator.calculate_reward(task, trajectory)
            env_reward_info = env_evaluator.calculate_reward(env_constructor, task, trajectory)
            task_row = _task_row(
                domain=domain,
                task=task,
                action_reward_info=action_reward_info,
                env_reward_info=env_reward_info,
                event_rows=task_event_rows,
                gateway_records=task_gateway_records,
            )
        except Exception as exc:
            unsupported_rows.append(_unsupported_row(domain, task_id, f"task_eval_error:{type(exc).__name__}: {exc}"))
            continue

        task_rows.append(task_row)
        event_rows.extend(task_event_rows)
        gateway_records.extend(task_gateway_records)
        intentcap_traces.append(trajectory_result["intentcap_trace"])

    return {
        "task_rows": task_rows,
        "event_rows": event_rows,
        "unsupported_rows": unsupported_rows,
        "gateway_records": gateway_records,
        "intentcap_traces": intentcap_traces,
    }


def _reference_trajectory(domain: str, task: Any, env_constructor: Callable[..., Any]) -> dict[str, Any]:
    message_mod = importlib.import_module("tau2.data_model.message")
    assistant_message_cls = getattr(message_mod, "AssistantMessage")
    user_message_cls = getattr(message_mod, "UserMessage")
    tool_call_cls = getattr(message_mod, "ToolCall")

    env = env_constructor()
    initialization_data, initialization_actions, message_history = _initial_state(task)
    env.set_state(
        initialization_data=initialization_data,
        initialization_actions=initialization_actions,
        message_history=message_history,
    )
    actions = list((task.evaluation_criteria.actions if task.evaluation_criteria else []) or [])
    assistant_reference_actions = [
        _reference_action(domain, task.id, index, action)
        for index, action in enumerate(actions)
        if str(action.requestor) == "assistant"
    ]
    trace = build_trace(assistant_reference_actions)
    gateway_records: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    trajectory: list[Any] = list(message_history)

    event_by_id = {event["id"]: event for event in trace.get("events", [])}
    event_to_action = {action.event_id: action for action in assistant_reference_actions}

    def make_tool(_object_name: str) -> Callable[..., Any]:
        def tool(**kwargs: Any) -> Any:
            event_id = str(kwargs.pop("intentcap_event_id"))
            reference_action = event_to_action[event_id]
            tool_call = tool_call_cls(
                id=event_id,
                name=reference_action.name,
                arguments=reference_action.args,
                requestor="assistant",
            )
            return env.get_response(tool_call)

        return tool

    tools = {action.object_name: make_tool(action.object_name) for action in assistant_reference_actions}
    gateway = LiveToolGateway(trace, tools)

    for index, action in enumerate(actions):
        requestor = str(action.requestor)
        event_id = _event_id(domain, task.id, index, action)
        tool_call = tool_call_cls(
            id=event_id,
            name=action.name,
            arguments=dict(action.arguments),
            requestor=requestor,
        )
        if requestor == "assistant":
            event = event_by_id[event_id]
            record = gateway.call(event)
            gateway_records.append(record)
            if record.get("executed"):
                tool_message = record.get("result")
            else:
                tool_message = _blocked_tool_message(event_id, requestor, record.get("decision", {}))
        else:
            tool_message = env.get_response(tool_call)

        message = (
            assistant_message_cls(role="assistant", tool_calls=[tool_call])
            if requestor == "assistant"
            else user_message_cls(role="user", tool_calls=[tool_call])
        )
        trajectory.extend([message, tool_message])
        event_rows.append(
            {
                "event_id": event_id,
                "domain": domain,
                "task_id": str(task.id),
                "action_id": str(action.action_id),
                "requestor": requestor,
                "tool": str(action.name),
                "gateway_allowed": (
                    bool(gateway_records[-1].get("decision", {}).get("allowed"))
                    if requestor == "assistant"
                    else ""
                ),
                "gateway_executed": (
                    bool(gateway_records[-1].get("executed"))
                    if requestor == "assistant"
                    else ""
                ),
                "tool_error": bool(getattr(tool_message, "error", False)),
                "reward_basis": "|".join(_reward_basis(task)),
            }
        )

    return {
        "trajectory": trajectory,
        "event_rows": event_rows,
        "gateway_records": gateway_records,
        "intentcap_trace": {
            "domain": domain,
            "task_id": str(task.id),
            "trace": trace,
        },
    }


def _initial_state(task: Any) -> tuple[Any, list[Any] | None, list[Any]]:
    if task.initial_state is None:
        return None, None, []
    initialization_data = task.initial_state.initialization_data
    initialization_actions = task.initial_state.initialization_actions
    message_history = list(task.initial_state.message_history or [])
    return initialization_data, initialization_actions, message_history


def _task_row(
    *,
    domain: str,
    task: Any,
    action_reward_info: Any,
    env_reward_info: Any,
    event_rows: list[dict[str, Any]],
    gateway_records: list[dict[str, Any]],
) -> dict[str, Any]:
    reward_basis = _reward_basis(task)
    unevaluated = sorted(set(reward_basis) & UNEVALUATED_BASIS)
    tool_oracle_basis = sorted(set(reward_basis) & TOOL_ORACLE_BASIS)
    action_required = "ACTION" in reward_basis
    env_applicable = bool(set(reward_basis) & {"DB", "ENV_ASSERTION"})
    action_pass = float(getattr(action_reward_info, "reward", 1.0)) == 1.0
    env_pass = float(getattr(env_reward_info, "reward", 1.0)) == 1.0
    tool_oracle_pass = (
        (not action_required or action_pass)
        and (not env_applicable or env_pass)
    )
    db_check = getattr(env_reward_info, "db_check", None)
    env_assertions = getattr(env_reward_info, "env_assertions", None) or []
    gateway_allowed = sum(1 for record in gateway_records if record.get("decision", {}).get("allowed"))
    gateway_blocked = len(gateway_records) - gateway_allowed
    return {
        "domain": domain,
        "task_id": str(task.id),
        "reward_basis": "|".join(reward_basis),
        "tool_oracle_basis": "|".join(tool_oracle_basis) if tool_oracle_basis else "none",
        "unevaluated_basis": "|".join(unevaluated) if unevaluated else "none",
        "tool_oracle_applicable": bool(tool_oracle_basis),
        "tool_oracle_pass": bool(tool_oracle_basis and tool_oracle_pass),
        "action_reward": float(getattr(action_reward_info, "reward", 1.0)),
        "env_oracle_applicable": env_applicable,
        "env_reward": float(getattr(env_reward_info, "reward", 1.0)),
        "db_match": getattr(db_check, "db_match", "") if db_check is not None else "",
        "env_assertions": len(env_assertions),
        "env_assertions_met": sum(1 for item in env_assertions if getattr(item, "met", False)),
        "reference_actions": len(event_rows),
        "assistant_reference_actions": sum(1 for row in event_rows if row["requestor"] == "assistant"),
        "user_reference_actions": sum(1 for row in event_rows if row["requestor"] == "user"),
        "assistant_gateway_allowed": gateway_allowed,
        "assistant_gateway_blocked": gateway_blocked,
        "tool_error_events": sum(1 for row in event_rows if row["tool_error"]),
    }


def _environment_constructor(domain: str, task: Any) -> Callable[..., Any]:
    if domain == "banking_knowledge":
        return _banking_knowledge_environment_constructor()
    module = importlib.import_module(f"tau2.domains.{domain}.environment")

    def constructor(*, solo_mode: bool = False, **kwargs: Any) -> Any:
        return module.get_environment(solo_mode=solo_mode, **kwargs)

    return constructor


def _banking_knowledge_environment_constructor() -> Callable[..., Any]:
    def constructor(*, solo_mode: bool = False, **_kwargs: Any) -> Any:
        if solo_mode:
            raise ValueError("banking_knowledge domain does not support solo mode")
        env_cls = _import_attr("tau2.environment.environment", "Environment")
        db_cls = _import_attr("tau2.domains.banking_knowledge.data_model", "TransactionalDB")
        tools_module = importlib.import_module("tau2.domains.banking_knowledge.tools")
        utils_module = importlib.import_module("tau2.domains.banking_knowledge.utils")
        db = db_cls.load(str(utils_module.KNOWLEDGE_DB_PATH))
        tools = tools_module.KnowledgeTools(db)
        user_tools = tools_module.KnowledgeUserTools(db)
        return env_cls(
            domain_name="banking_knowledge",
            policy="",
            tools=tools,
            user_tools=user_tools,
        )

    return constructor


def _reference_action(domain: str, task_id: str, index: int, action: Any) -> ReferenceAction:
    return ReferenceAction(
        event_id=_event_id(domain, task_id, index, action),
        domain=domain,
        task_id=str(task_id),
        action_id=str(action.action_id),
        index=index,
        name=str(action.name),
        requestor="assistant",
        args=dict(action.arguments),
        reward_basis=tuple(),
        object_name=f"tau2.{domain}.assistant.{action.name}",
    )


def _event_id(domain: str, task_id: str, index: int, action: Any) -> str:
    return f"{domain}:{task_id}:{action.action_id or index}"


def _blocked_tool_message(event_id: str, requestor: str, decision: dict[str, Any]) -> Any:
    tool_message_cls = _import_attr("tau2.data_model.message", "ToolMessage")
    return tool_message_cls(
        id=event_id,
        role="tool",
        requestor=requestor,
        error=True,
        content=json.dumps({"error": "blocked", "reason": decision.get("reason")}),
    )


def _reward_basis(task: Any) -> list[str]:
    if task.evaluation_criteria is None:
        return []
    return [str(item.value if hasattr(item, "value") else item) for item in task.evaluation_criteria.reward_basis]


def _unsupported_row(domain: str, task_id: str, reason: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "task_id": task_id,
        "reason": reason,
    }


def _import_attr(module_name: str, attr_name: str) -> Any:
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    fieldnames = fieldnames or (list(rows[0].keys()) if rows else [])
    if not fieldnames:
        path.write_text("")
        return
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
