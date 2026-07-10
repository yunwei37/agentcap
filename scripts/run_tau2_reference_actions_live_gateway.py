"""Run tau2/tau3 assistant reference actions through LiveToolGateway.

This runner is a bridge between the static tau2 authority analysis and a real
runtime shape. For each benchmark task it loads a fresh tau2 domain toolkit,
applies benchmark initial state where possible, mints one exact IntentCap lease
per assistant reference action, and executes the action only after the checker
allows it.

It is still not a full tau2 model/simulator/reward run: the attempted actions
come from benchmark reference labels, and user-side reference actions are
reported but not granted to the assistant.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import sys
import types
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from intentcap.live_gateway import LiveToolGateway


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_tau2_bench import KNOWN_DOMAINS, _load_json_list  # noqa: E402


@dataclass(frozen=True)
class DomainConfig:
    data_model_module: str
    db_class: str
    tools_module: str
    tools_class: str
    user_data_model_module: str | None = None
    user_db_class: str | None = None
    user_tools_module: str | None = None
    user_tools_class: str | None = None


@dataclass(frozen=True)
class ReferenceAction:
    event_id: str
    domain: str
    task_id: str
    action_id: str
    index: int
    name: str
    requestor: str
    args: dict[str, Any]
    reward_basis: tuple[str, ...]
    object_name: str


@dataclass
class TaskRuntime:
    domain: str
    task_id: str
    assistant_tools: Any
    user_tools: Any | None
    initialization_events: int = 0
    initialization_errors: list[str] | None = None

    def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return self.assistant_tools.use_tool(tool_name, **arguments)


DOMAIN_CONFIGS: dict[str, DomainConfig] = {
    "mock": DomainConfig(
        "tau2.domains.mock.data_model",
        "MockDB",
        "tau2.domains.mock.tools",
        "MockTools",
        "tau2.domains.mock.user_data_model",
        "MockUserDB",
        "tau2.domains.mock.user_tools",
        "MockUserTools",
    ),
    "airline": DomainConfig(
        "tau2.domains.airline.data_model",
        "FlightDB",
        "tau2.domains.airline.tools",
        "AirlineTools",
    ),
    "retail": DomainConfig(
        "tau2.domains.retail.data_model",
        "RetailDB",
        "tau2.domains.retail.tools",
        "RetailTools",
    ),
    "telecom": DomainConfig(
        "tau2.domains.telecom.data_model",
        "TelecomDB",
        "tau2.domains.telecom.tools",
        "TelecomTools",
        "tau2.domains.telecom.user_data_model",
        "TelecomUserDB",
        "tau2.domains.telecom.user_tools",
        "TelecomUserTools",
    ),
    "banking_knowledge": DomainConfig(
        "tau2.domains.banking_knowledge.data_model",
        "TransactionalDB",
        "tau2.domains.banking_knowledge.tools",
        "KnowledgeTools",
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute tau2/tau3 assistant reference actions through the live IntentCap gateway"
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
    (args.output_dir / "trace.json").write_text(
        json.dumps(result["trace"], indent=2, sort_keys=True, default=_json_default)
    )
    (args.output_dir / "live_gateway_records.json").write_text(
        json.dumps(result["records"], indent=2, sort_keys=True, default=_json_default)
    )
    (args.output_dir / "live_gateway_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True, default=_json_default)
    )
    (args.output_dir / "callable_invocations.json").write_text(
        json.dumps(result["callable_invocations"], indent=2, sort_keys=True, default=_json_default)
    )
    (args.output_dir / "registered_tools.json").write_text(
        json.dumps(result["registered_tools"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "event_results.csv", result["event_rows"])
    _write_rows(args.output_dir / "unsupported_tools.csv", result["unsupported_rows"])
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

    actions: list[ReferenceAction] = []
    runtimes: dict[str, TaskRuntime] = {}
    unsupported_rows: list[dict[str, Any]] = []
    task_counts: Counter[str] = Counter()
    user_reference_actions = 0

    for domain in domains:
        domain_actions, domain_runtimes, domain_unsupported, domain_user_actions = _load_domain_actions(
            benchmark_dir=benchmark_dir,
            domain=domain,
            max_tasks=max_tasks_per_domain,
        )
        actions.extend(domain_actions)
        runtimes.update(domain_runtimes)
        unsupported_rows.extend(domain_unsupported)
        user_reference_actions += domain_user_actions
        task_counts[domain] += len(
            {
                action.task_id
                for action in domain_actions
            }
        )

    trace = build_trace(actions)
    callable_invocations: list[dict[str, Any]] = []
    tools = build_tool_registry(actions, runtimes, callable_invocations)
    gateway = LiveToolGateway(trace, tools)
    records = gateway.run_events()
    summary = summarize(
        trace=trace,
        records=records,
        callable_invocations=callable_invocations,
        gateway_summary=gateway.summary(records),
        registered_tools=tools,
        actions=actions,
        runtimes=runtimes,
        unsupported_rows=unsupported_rows,
        user_reference_actions=user_reference_actions,
        task_counts=task_counts,
    )
    event_rows = event_result_rows(trace, records, actions, runtimes)

    return {
        "trace": trace,
        "records": records,
        "summary": summary,
        "callable_invocations": callable_invocations,
        "registered_tools": sorted(tools),
        "unsupported_rows": unsupported_rows,
        "event_rows": event_rows,
    }


def build_trace(actions: list[ReferenceAction]) -> dict[str, Any]:
    decisions = sorted({f"{action.domain}.{action.name}.tool_choice" for action in actions})
    labels = {
        "trusted_tau2_reference": {
            "allowed": {
                "tool_select": decisions,
            }
        }
    }
    leases = [
        {
            "id": f"lease:{action.event_id}",
            "op": "tool.call",
            "object": action.object_name,
            "args": {
                "_intentcap_event_id": {"equals": action.event_id},
                "intentcap_event_id": {"equals": action.event_id},
                **{
                    key: {"equals": value}
                    for key, value in sorted(action.args.items())
                },
            },
            "control_may_depend_on": ["trusted_tau2_reference"],
            "data_may_depend_on": ["trusted_tau2_reference"],
        }
        for action in actions
    ]
    events = [
        {
            "id": action.event_id,
            "op": "tool.call",
            "object": action.object_name,
            "args": {
                "_intentcap_event_id": action.event_id,
                "intentcap_event_id": action.event_id,
                **action.args,
            },
            "decision": f"{action.domain}.{action.name}.tool_choice",
            "mode": "tool_select",
            "control_provenance": ["trusted_tau2_reference"],
            "data_provenance": ["trusted_tau2_reference"],
            "intentcap_event_type": "tau2_assistant_reference_action",
            "domain": action.domain,
            "task_id": action.task_id,
            "action_id": action.action_id,
            "logical_tool": action.name,
            "reward_basis": list(action.reward_basis),
        }
        for action in actions
    ]
    return {
        "labels": labels,
        "leases": leases,
        "events": events,
        "metadata": {
            "source": "tau2/tau3 tasks.json evaluation_criteria.actions",
            "note": (
                "Reference actions are benchmark labels. This trace exercises "
                "IntentCap gateway execution over those actions; it is not a "
                "model/simulator/reward run."
            ),
        },
    }


def build_tool_registry(
    actions: list[ReferenceAction],
    runtimes: dict[str, TaskRuntime],
    callable_invocations: list[dict[str, Any]],
) -> dict[str, Callable[..., Any]]:
    event_to_action = {action.event_id: action for action in actions}
    object_names = sorted({action.object_name for action in actions})

    def make_tool(object_name: str) -> Callable[..., Any]:
        def tool(**kwargs: Any) -> Any:
            event_id = str(kwargs.pop("intentcap_event_id", ""))
            action = event_to_action[event_id]
            runtime = runtimes[event_id]
            tool_args = {
                key: value
                for key, value in kwargs.items()
                if not str(key).startswith("_intentcap_")
            }
            callable_invocations.append(
                {
                    "event_id": event_id,
                    "domain": action.domain,
                    "task_id": action.task_id,
                    "action_id": action.action_id,
                    "tool": action.name,
                    "object": object_name,
                    "args": tool_args,
                }
            )
            return runtime.call(action.name, tool_args)

        return tool

    return {
        object_name: make_tool(object_name)
        for object_name in object_names
    }


def summarize(
    *,
    trace: dict[str, Any],
    records: list[dict[str, Any]],
    callable_invocations: list[dict[str, Any]],
    gateway_summary: dict[str, Any],
    registered_tools: dict[str, Callable[..., Any]],
    actions: list[ReferenceAction],
    runtimes: dict[str, TaskRuntime],
    unsupported_rows: list[dict[str, Any]],
    user_reference_actions: int,
    task_counts: Counter[str],
) -> dict[str, Any]:
    event_by_id = {str(event.get("id", "")): event for event in trace.get("events", [])}
    domain_counts = Counter(action.domain for action in actions)
    tool_counts = Counter(action.name for action in actions)
    successful = sum(1 for record in records if record.get("executed") and not record.get("error"))
    with_tool_errors = sum(1 for record in records if record.get("executed") and record.get("error"))
    blocked = sum(1 for record in records if not record.get("executed"))
    initialization_errors = sum(
        len(runtime.initialization_errors or [])
        for runtime in runtimes.values()
    )
    tasks_with_initialization_errors = len(
        {
            (runtime.domain, runtime.task_id)
            for runtime in runtimes.values()
            if runtime.initialization_errors
        }
    )
    error_types = Counter(
        str(record.get("error", "")).split(":", 1)[0]
        for record in records
        if record.get("error")
    )
    blocked_domains = Counter(
        str(event_by_id.get(str(record.get("decision", {}).get("event_id", "")), {}).get("domain", "unknown"))
        for record in records
        if not record.get("executed")
    )

    return {
        **gateway_summary,
        "benchmark": "tau2-bench / tau3-bench",
        "reference_action_source": "evaluation_criteria.actions",
        "domains": sorted(domain_counts),
        "tasks_with_assistant_reference_actions_by_domain": dict(sorted(task_counts.items())),
        "assistant_reference_actions": len(actions),
        "user_reference_actions_excluded_from_assistant_authority": user_reference_actions,
        "registered_tools": len(registered_tools),
        "callable_invocations": len(callable_invocations),
        "successful_tool_events": successful,
        "executed_with_tool_error_events": with_tool_errors,
        "blocked_events": blocked,
        "unsupported_rows": len(unsupported_rows),
        "initialization_errors": initialization_errors,
        "tasks_with_initialization_errors": tasks_with_initialization_errors,
        "domain_action_counts": dict(sorted(domain_counts.items())),
        "top_tool_counts": dict(tool_counts.most_common(20)),
        "tool_error_type_counts": dict(sorted(error_types.items())),
        "blocked_domain_counts": dict(sorted(blocked_domains.items())),
        "notes": [
            "Each assistant reference action receives one exact event lease with event-id, provenance, and argument constraints.",
            "The run executes tau2 domain toolkit methods through IntentCap LiveToolGateway after checker approval.",
            "This is not a full model-driven tau2 utility run and does not invoke the user simulator or reward scorer.",
            "Tool exceptions are runtime precondition/type errors from direct reference-action replay, not checker denials.",
        ],
    }


def event_result_rows(
    trace: dict[str, Any],
    records: list[dict[str, Any]],
    actions: list[ReferenceAction],
    runtimes: dict[str, TaskRuntime],
) -> list[dict[str, Any]]:
    event_by_id = {str(event.get("id", "")): event for event in trace.get("events", [])}
    action_by_event = {action.event_id: action for action in actions}
    rows: list[dict[str, Any]] = []
    for record in records:
        decision = record.get("decision", {})
        event_id = str(decision.get("event_id", ""))
        event = event_by_id.get(event_id, {})
        action = action_by_event.get(event_id)
        runtime = runtimes.get(event_id)
        error = str(record.get("error") or "")
        rows.append(
            {
                "event_id": event_id,
                "domain": str(event.get("domain", "")),
                "task_id": str(event.get("task_id", "")),
                "action_id": str(event.get("action_id", "")),
                "tool": action.name if action else "",
                "object": str(decision.get("object", "")),
                "allowed_by_checker": bool(decision.get("allowed")),
                "executed": bool(record.get("executed")),
                "tool_success": bool(record.get("executed") and not record.get("error")),
                "error_type": error.split(":", 1)[0] if error else "",
                "error": error,
                "reward_basis": "|".join(str(item) for item in event.get("reward_basis", [])),
                "initialization_events": runtime.initialization_events if runtime else 0,
                "initialization_errors": len(runtime.initialization_errors or []) if runtime else 0,
            }
        )
    return rows


def _load_domain_actions(
    *,
    benchmark_dir: Path,
    domain: str,
    max_tasks: int | None,
) -> tuple[list[ReferenceAction], dict[str, TaskRuntime], list[dict[str, Any]], int]:
    data_dir = benchmark_dir / "data" / "tau2" / "domains" / domain
    tasks = _load_json_list(data_dir / "tasks.json")
    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    unsupported_rows: list[dict[str, Any]] = []
    actions: list[ReferenceAction] = []
    runtimes: dict[str, TaskRuntime] = {}
    user_reference_actions = 0

    if domain not in DOMAIN_CONFIGS:
        unsupported_rows.append(
            {
                "domain": domain,
                "task_id": "",
                "tool": "",
                "reason": "domain_not_configured",
            }
        )
        return actions, runtimes, unsupported_rows, user_reference_actions

    for task in tasks:
        criteria = task.get("evaluation_criteria") or {}
        reference_actions = [
            action
            for action in criteria.get("actions") or []
            if isinstance(action, dict)
        ]
        assistant_actions = [
            action
            for action in reference_actions
            if str(action.get("requestor", "assistant")) == "assistant"
        ]
        user_reference_actions += sum(
            1
            for action in reference_actions
            if str(action.get("requestor", "assistant")) != "assistant"
        )
        if not assistant_actions:
            continue

        task_id = str(task.get("id", ""))
        try:
            runtime = _make_task_runtime(data_dir, domain, task)
        except Exception as exc:
            unsupported_rows.append(
                {
                    "domain": domain,
                    "task_id": task_id,
                    "tool": "",
                    "reason": f"runtime_init_error:{type(exc).__name__}: {exc}",
                }
            )
            continue

        for index, action in enumerate(assistant_actions):
            name = str(action.get("name", ""))
            action_id = str(action.get("action_id", index))
            if not runtime.assistant_tools.has_tool(name):
                unsupported_rows.append(
                    {
                        "domain": domain,
                        "task_id": task_id,
                        "tool": name,
                        "reason": "assistant_tool_not_registered",
                    }
                )
                continue
            event_id = f"{domain}:{task_id}:{action_id}"
            reference_action = ReferenceAction(
                event_id=event_id,
                domain=domain,
                task_id=task_id,
                action_id=action_id,
                index=index,
                name=name,
                requestor="assistant",
                args=dict(action.get("arguments") or {}),
                reward_basis=tuple(str(item) for item in (criteria.get("reward_basis") or [])),
                object_name=f"tau2.{domain}.assistant.{name}",
            )
            actions.append(reference_action)
            runtimes[event_id] = runtime

    return actions, runtimes, unsupported_rows, user_reference_actions


def _make_task_runtime(
    data_dir: Path,
    domain: str,
    task: dict[str, Any],
) -> TaskRuntime:
    config = DOMAIN_CONFIGS[domain]
    db = _load_db(config.data_model_module, config.db_class, _data_file(data_dir, "db"))
    tools_cls = _import_attr(config.tools_module, config.tools_class)
    assistant_tools = tools_cls(db)

    user_tools = None
    user_db_path = _data_file(data_dir, "user_db", required=False)
    if (
        config.user_data_model_module
        and config.user_db_class
        and config.user_tools_module
        and config.user_tools_class
        and user_db_path is not None
        and user_db_path.exists()
    ):
        user_db = _load_db(config.user_data_model_module, config.user_db_class, user_db_path)
        user_tools_cls = _import_attr(config.user_tools_module, config.user_tools_class)
        user_tools = user_tools_cls(user_db)

    runtime = TaskRuntime(
        domain=domain,
        task_id=str(task.get("id", "")),
        assistant_tools=assistant_tools,
        user_tools=user_tools,
        initialization_events=0,
        initialization_errors=[],
    )
    _apply_initial_state(runtime, task.get("initial_state") or {})
    return runtime


def _load_db(module_name: str, class_name: str, path: Path) -> Any:
    db_cls = _import_attr(module_name, class_name)
    return db_cls.load(str(path))


def _data_file(data_dir: Path, stem: str, *, required: bool = True) -> Path | None:
    for suffix in (".json", ".toml", ".yaml", ".yml"):
        path = data_dir / f"{stem}{suffix}"
        if path.exists():
            return path
    if required:
        raise FileNotFoundError(f"missing {stem} data file in {data_dir}")
    return None


def _apply_initial_state(runtime: TaskRuntime, initial_state: dict[str, Any]) -> None:
    initialization_data = initial_state.get("initialization_data") or {}
    if isinstance(initialization_data, dict):
        _apply_initialization_data(runtime, initialization_data)

    initialization_actions = initial_state.get("initialization_actions") or []
    if isinstance(initialization_actions, list):
        for action in initialization_actions:
            _run_initialization_action(runtime, action)

    message_history = initial_state.get("message_history") or []
    if isinstance(message_history, list):
        for message in message_history:
            _run_message_history_tools(runtime, message)


def _apply_initialization_data(runtime: TaskRuntime, initialization_data: dict[str, Any]) -> None:
    agent_data = initialization_data.get("agent_data")
    if isinstance(agent_data, dict):
        try:
            runtime.assistant_tools.update_db(agent_data)
            runtime.initialization_events += 1
        except Exception as exc:
            runtime.initialization_errors.append(f"agent_data:{type(exc).__name__}: {exc}")

    user_data = initialization_data.get("user_data")
    if isinstance(user_data, dict) and runtime.user_tools is not None:
        try:
            runtime.user_tools.update_db(user_data)
            runtime.initialization_events += 1
        except Exception as exc:
            runtime.initialization_errors.append(f"user_data:{type(exc).__name__}: {exc}")


def _run_initialization_action(runtime: TaskRuntime, action: Any) -> None:
    if not isinstance(action, dict):
        return
    env_type = str(action.get("env_type", "assistant"))
    func_name = str(action.get("func_name") or action.get("name") or "")
    arguments = dict(action.get("arguments") or {})
    toolkit = runtime.assistant_tools if env_type == "assistant" else runtime.user_tools
    if toolkit is None or not hasattr(toolkit, func_name):
        runtime.initialization_errors.append(f"{env_type}.{func_name}:missing")
        return
    try:
        getattr(toolkit, func_name)(**arguments)
        runtime.initialization_events += 1
    except Exception as exc:
        runtime.initialization_errors.append(f"{env_type}.{func_name}:{type(exc).__name__}: {exc}")


def _run_message_history_tools(runtime: TaskRuntime, message: Any) -> None:
    if not isinstance(message, dict):
        return
    role = str(message.get("role", "assistant"))
    toolkit = runtime.user_tools if role == "user" else runtime.assistant_tools
    tool_calls = message.get("tool_calls") or []
    if not isinstance(tool_calls, list):
        return
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        name = str(tool_call.get("name", ""))
        arguments = dict(tool_call.get("arguments") or {})
        if not name or toolkit is None or not toolkit.has_tool(name):
            continue
        if hasattr(toolkit, "tool_mutates_state") and not toolkit.tool_mutates_state(name):
            continue
        try:
            toolkit.use_tool(name, **arguments)
            runtime.initialization_events += 1
        except Exception as exc:
            runtime.initialization_errors.append(f"message_history.{role}.{name}:{type(exc).__name__}: {exc}")


def _install_tau2_import_shims(benchmark_dir: Path) -> None:
    src_tau2 = benchmark_dir / "src" / "tau2"
    os.environ.setdefault("TAU2_DATA_DIR", str(benchmark_dir / "data"))
    if "tau2" not in sys.modules:
        tau2_pkg = types.ModuleType("tau2")
        tau2_pkg.__path__ = [str(src_tau2)]  # type: ignore[attr-defined]
        sys.modules["tau2"] = tau2_pkg
    if "loguru" not in sys.modules:
        loguru_module = types.ModuleType("loguru")
        loguru_module.logger = _NoopLogger()
        sys.modules["loguru"] = loguru_module
    if "addict" not in sys.modules:
        addict_module = types.ModuleType("addict")
        addict_module.Dict = _AddictDict
        sys.modules["addict"] = addict_module


class _NoopLogger:
    def __getattr__(self, _name: str) -> Callable[..., None]:
        def log(*_args: Any, **_kwargs: Any) -> None:
            return None

        return log


class _AddictDict(dict):
    """Small local subset of addict.Dict used by tau2's pydantic updater."""

    def update(self, other: Any = None, **kwargs: Any) -> None:  # type: ignore[override]
        updates = dict(other or {})
        updates.update(kwargs)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(self.get(key), dict):
                nested = _AddictDict(self[key])
                nested.update(value)
                self[key] = nested
            else:
                self[key] = _AddictDict(value) if isinstance(value, dict) else value

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value.to_dict() if isinstance(value, _AddictDict) else value
            for key, value in self.items()
        }


def _import_attr(module_name: str, attr_name: str) -> Any:
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return str(value)


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
