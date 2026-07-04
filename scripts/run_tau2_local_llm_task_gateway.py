"""Run local Qwen on tau2 tasks behind an IntentCap gateway.

R031 is the first fresh local-model task-environment probe. It prompts a local
llama.cpp/Qwen model with tau2 task text and tool schemas, asks for assistant
tool calls, binds exact tool+argument matches to pre-minted per-task leases,
and executes allowed calls through LiveToolGateway against the tau2 environment.

This is intentionally a small pilot. By default it runs the mock domain only,
does not sync datasets, and uses exact reference-action leases as the oracle
authorization profile. It is therefore not a full tau2/tau3 online benchmark or
a complete lease compiler evaluation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from intentcap.live_gateway import LiveToolGateway


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_tau2_bench import _load_json_list  # noqa: E402
from run_local_llm_lease_corpus import (  # noqa: E402
    DEFAULT_LLAMA_BIN,
    DEFAULT_MODEL,
    _file_digest,
    _llama_command,
    _run_llama,
)
from run_tau2_evaluator_backed_replay import (  # noqa: E402
    _blocked_tool_message,
    _environment_constructor,
    _initial_state,
    _reward_basis,
)
from run_tau2_reference_actions_live_gateway import (  # noqa: E402
    ReferenceAction,
    _install_tau2_import_shims,
)


TRUSTED_TASK_INTENT = "trusted_tau2_task_intent"
ROW_FIELDS = [
    "domain",
    "task_id",
    "prompt_path",
    "raw_output_path",
    "parse_ok",
    "model_calls",
    "reference_actions",
    "bound_reference_calls",
    "gateway_allowed",
    "gateway_blocked",
    "executed_calls",
    "tool_error_calls",
    "off_lease_calls_blocked",
    "exact_sequence_match",
    "all_reference_actions_executed",
    "action_reward",
    "env_reward",
    "tool_oracle_applicable",
    "tool_oracle_pass",
    "reward_basis",
]
ACTION_ROW_FIELDS = [
    "domain",
    "task_id",
    "index",
    "model_tool",
    "model_args_json",
    "bound_reference_event_id",
    "event_id",
    "object",
    "gateway_allowed",
    "gateway_action",
    "gateway_reason",
    "executed",
    "tool_error",
]
UNSUPPORTED_ROW_FIELDS = ["domain", "task_id", "reason"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local Qwen tau2 task proposals through IntentCap LiveToolGateway"
    )
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R031")
    parser.add_argument("--domains", nargs="*", default=["mock"])
    parser.add_argument("--max-tasks-per-domain", type=int, default=6)
    parser.add_argument("--llama-bin", type=Path, default=DEFAULT_LLAMA_BIN)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--n-predict", type=int, default=512)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--gpu-layers", type=int, default=999)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_experiment(
        benchmark_dir=args.benchmark_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
        domains=tuple(args.domains),
        max_tasks_per_domain=args.max_tasks_per_domain,
        llama_bin=args.llama_bin,
        model=args.model,
        n_predict=args.n_predict,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def run_experiment(
    *,
    benchmark_dir: Path,
    output_dir: Path,
    run_id: str = "R031",
    domains: tuple[str, ...] = ("mock",),
    max_tasks_per_domain: int | None = 6,
    llama_bin: Path = DEFAULT_LLAMA_BIN,
    model: Path = DEFAULT_MODEL,
    n_predict: int = 512,
    ctx_size: int = 4096,
    gpu_layers: int = 999,
    timeout_seconds: int = 120,
    dry_run: bool = False,
    runner: Callable[[list[str], int], tuple[str, str, int, float]] | None = None,
) -> dict[str, Any]:
    _install_tau2_import_shims(benchmark_dir)
    runner = runner or _run_llama

    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir = output_dir / "prompts"
    raw_dir = output_dir / "raw_outputs"
    prompt_dir.mkdir(exist_ok=True)
    raw_dir.mkdir(exist_ok=True)

    task_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for domain in domains:
        data_dir = benchmark_dir / "data" / "tau2" / "domains" / domain
        raw_tasks = _load_json_list(data_dir / "tasks.json")
        if max_tasks_per_domain is not None:
            raw_tasks = raw_tasks[:max_tasks_per_domain]
        for raw_task in raw_tasks:
            task_id = str(raw_task.get("id", ""))
            criteria = raw_task.get("evaluation_criteria") or {}
            reference_actions = _reference_actions(domain, task_id, criteria)
            if not reference_actions:
                unsupported_rows.append(
                    {
                        "domain": domain,
                        "task_id": task_id,
                        "reason": "no_assistant_reference_actions",
                    }
                )
                continue
            try:
                task_record = _run_task(
                    benchmark_dir=benchmark_dir,
                    data_dir=data_dir,
                    domain=domain,
                    raw_task=raw_task,
                    reference_actions=reference_actions,
                    prompt_dir=prompt_dir,
                    raw_dir=raw_dir,
                    llama_bin=llama_bin,
                    model=model,
                    n_predict=n_predict,
                    ctx_size=ctx_size,
                    gpu_layers=gpu_layers,
                    timeout_seconds=timeout_seconds,
                    dry_run=dry_run,
                    runner=runner,
                )
            except Exception as exc:
                unsupported_rows.append(
                    {
                        "domain": domain,
                        "task_id": task_id,
                        "reason": f"task_error:{type(exc).__name__}: {exc}",
                    }
                )
                continue
            task_rows.append(task_record["task_row"])
            action_rows.extend(task_record["action_rows"])
            records.append(task_record["record"])

    summary = summarize(
        run_id=run_id,
        task_rows=task_rows,
        action_rows=action_rows,
        unsupported_rows=unsupported_rows,
        domains=domains,
        benchmark_dir=benchmark_dir,
        llama_bin=llama_bin,
        model=model,
        n_predict=n_predict,
        ctx_size=ctx_size,
        gpu_layers=gpu_layers,
        timeout_seconds=timeout_seconds,
        max_tasks_per_domain=max_tasks_per_domain,
        dry_run=dry_run,
    )

    (output_dir / "task_gateway_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=_json_default)
    )
    _write_rows(output_dir / "task_results.csv", task_rows, ROW_FIELDS)
    _write_rows(output_dir / "action_results.csv", action_rows, ACTION_ROW_FIELDS)
    _write_rows(output_dir / "unsupported_tasks.csv", unsupported_rows, UNSUPPORTED_ROW_FIELDS)
    with (output_dir / "samples.jsonl").open("w") as file:
        for record in records:
            file.write(json.dumps(record, sort_keys=True, default=_json_default) + "\n")
    (output_dir / "input_digests.csv").write_text(_input_digest_csv(benchmark_dir, domains))
    (output_dir / "command.txt").write_text(_command_text())
    return {
        "summary": summary,
        "task_rows": task_rows,
        "action_rows": action_rows,
        "unsupported_rows": unsupported_rows,
        "records": records,
    }


def _run_task(
    *,
    benchmark_dir: Path,
    data_dir: Path,
    domain: str,
    raw_task: dict[str, Any],
    reference_actions: list[ReferenceAction],
    prompt_dir: Path,
    raw_dir: Path,
    llama_bin: Path,
    model: Path,
    n_predict: int,
    ctx_size: int,
    gpu_layers: int,
    timeout_seconds: int,
    dry_run: bool,
    runner: Callable[[list[str], int], tuple[str, str, int, float]],
) -> dict[str, Any]:
    task_id = str(raw_task.get("id", ""))
    task_cls = _import_attr("tau2.data_model.tasks", "Task")
    action_evaluator = _import_attr("tau2.evaluator.evaluator_action", "ActionEvaluator")
    env_evaluator = _import_attr("tau2.evaluator.evaluator_env", "EnvironmentEvaluator")
    message_mod = _import_module("tau2.data_model.message")
    assistant_message_cls = getattr(message_mod, "AssistantMessage")
    tool_call_cls = getattr(message_mod, "ToolCall")

    task = task_cls.model_validate(raw_task)
    env_constructor = _environment_constructor(domain, task)
    env = env_constructor()
    initialization_data, initialization_actions, message_history = _initial_state(task)
    env.set_state(
        initialization_data=initialization_data,
        initialization_actions=initialization_actions,
        message_history=message_history,
    )
    trajectory: list[Any] = list(message_history)

    trace = build_task_trace(domain, task_id, reference_actions)
    prompt = build_prompt(domain, raw_task, _tool_schemas(env))
    prompt_path = prompt_dir / f"{_safe_id(domain, task_id)}.txt"
    raw_path = raw_dir / f"{_safe_id(domain, task_id)}.txt"
    prompt_path.write_text(prompt)

    if dry_run:
        stdout, stderr, returncode, latency = "", "", 0, 0.0
    else:
        command = _llama_command(
            llama_bin=llama_bin,
            model=model,
            prompt_path=prompt_path,
            n_predict=n_predict,
            ctx_size=ctx_size,
            gpu_layers=gpu_layers,
        )
        stdout, stderr, returncode, latency = runner(command, timeout_seconds)
    raw_payload = _raw_payload(stdout, stderr, returncode)
    raw_path.write_text(raw_payload)
    parsed = None if dry_run else parse_model_json(stdout)
    model_calls = normalize_model_calls(parsed)

    reference_by_event = {action.event_id: action for action in reference_actions}
    pending = list(reference_actions)
    callable_invocations: list[dict[str, Any]] = []
    tools = build_tool_registry(reference_actions, env, callable_invocations)
    gateway = LiveToolGateway(trace, tools)

    action_rows: list[dict[str, Any]] = []
    executed_reference_ids: list[str] = []
    bound_reference_ids: list[str] = []

    for index, model_call in enumerate(model_calls):
        event, bound_action = bind_model_call(
            domain=domain,
            task_id=task_id,
            index=index,
            model_call=model_call,
            pending_reference_actions=pending,
        )
        if bound_action is not None:
            pending.remove(bound_action)
            bound_reference_ids.append(bound_action.event_id)
        record = gateway.call(event)
        decision = record.get("decision", {})
        model_args = {
            key: value
            for key, value in dict(model_call.get("arguments") or {}).items()
            if not str(key).startswith("_intentcap_")
        }
        if record.get("executed"):
            event_id = str(decision.get("event_id", ""))
            ref = reference_by_event.get(event_id)
            if ref is not None:
                executed_reference_ids.append(event_id)
            tool_call = tool_call_cls(
                id=event_id,
                name=str(model_call.get("tool", "")),
                arguments=model_args,
                requestor="assistant",
            )
            trajectory.extend(
                [
                    assistant_message_cls(role="assistant", tool_calls=[tool_call]),
                    record.get("result"),
                ]
            )
        elif bool(decision.get("allowed")):
            trajectory.append(
                _blocked_tool_message(
                    str(event.get("id", f"model:{index}")),
                    "assistant",
                    decision,
                )
            )

        action_rows.append(
            {
                "domain": domain,
                "task_id": task_id,
                "index": index,
                "model_tool": str(model_call.get("tool", "")),
                "model_args_json": json.dumps(model_args, sort_keys=True),
                "bound_reference_event_id": bound_action.event_id if bound_action else "",
                "event_id": str(event.get("id", "")),
                "object": str(event.get("object", "")),
                "gateway_allowed": bool(decision.get("allowed")),
                "gateway_action": str(decision.get("action", "")),
                "gateway_reason": str(decision.get("reason", "")),
                "executed": bool(record.get("executed")),
                "tool_error": bool(record.get("error")),
            }
        )

    action_reward_info = action_evaluator.calculate_reward(task, trajectory)
    try:
        env_reward_info = env_evaluator.calculate_reward(env_constructor, task, trajectory)
        env_reward = float(getattr(env_reward_info, "reward", 1.0))
        env_error = ""
    except Exception as exc:
        env_reward_info = None
        env_reward = 0.0
        env_error = f"{type(exc).__name__}: {exc}"

    reward_basis = _reward_basis(task)
    action_required = bool(reference_actions)
    env_applicable = bool(set(reward_basis) & {"DB", "ENV_ASSERTION"})
    action_reward = float(getattr(action_reward_info, "reward", 1.0))
    tool_oracle_pass = (
        (not action_required or action_reward == 1.0)
        and (not env_applicable or env_reward == 1.0)
    )
    exact_sequence = [
        {"tool": action.name, "arguments": action.args}
        for action in reference_actions
    ] == [
        {
            "tool": str(call.get("tool", "")),
            "arguments": {
                key: value
                for key, value in dict(call.get("arguments") or {}).items()
                if not str(key).startswith("_intentcap_")
            },
        }
        for call in model_calls
    ]
    gateway_allowed = sum(1 for row in action_rows if row["gateway_allowed"])
    gateway_blocked = len(action_rows) - gateway_allowed
    executed = sum(1 for row in action_rows if row["executed"])
    tool_errors = sum(1 for row in action_rows if row["tool_error"])
    task_row = {
        "domain": domain,
        "task_id": task_id,
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_path),
        "parse_ok": parsed is not None,
        "model_calls": len(model_calls),
        "reference_actions": len(reference_actions),
        "bound_reference_calls": len(bound_reference_ids),
        "gateway_allowed": gateway_allowed,
        "gateway_blocked": gateway_blocked,
        "executed_calls": executed,
        "tool_error_calls": tool_errors,
        "off_lease_calls_blocked": sum(
            1
            for row in action_rows
            if not row["bound_reference_event_id"] and not row["gateway_allowed"]
        ),
        "exact_sequence_match": exact_sequence,
        "all_reference_actions_executed": (
            set(executed_reference_ids) == {action.event_id for action in reference_actions}
        ),
        "action_reward": action_reward,
        "env_reward": env_reward,
        "tool_oracle_applicable": True,
        "tool_oracle_pass": tool_oracle_pass,
        "reward_basis": "|".join(reward_basis),
    }
    return {
        "task_row": task_row,
        "action_rows": action_rows,
        "record": {
            "domain": domain,
            "task_id": task_id,
            "prompt_path": str(prompt_path),
            "raw_output_path": str(raw_path),
            "raw_output_sha256": _sha256(raw_payload.encode()),
            "latency_seconds": latency,
            "returncode": returncode,
            "parsed": parsed,
            "model_calls": model_calls,
            "reference_actions": [
                {
                    "event_id": action.event_id,
                    "tool": action.name,
                    "arguments": action.args,
                }
                for action in reference_actions
            ],
            "task_row": task_row,
            "action_rows": action_rows,
            "callable_invocations": callable_invocations,
            "env_error": env_error,
            "env_reward_info": env_reward_info,
        },
    }


def build_prompt(domain: str, raw_task: dict[str, Any], tools: list[dict[str, Any]]) -> str:
    public_task = {
        key: value
        for key, value in raw_task.items()
        if key not in {"evaluation_criteria", "annotations"}
    }
    payload = {
        "domain": domain,
        "task": public_task,
        "available_tools": tools,
        "output_schema": {
            "actions": [
                {
                    "tool": "tool_name",
                    "arguments": {"arg_name": "arg_value"},
                }
            ],
            "final_response": "short user-facing response",
        },
    }
    return (
        "You are a tau2 assistant agent.\n"
        "Read the trusted user task and choose the assistant tool calls needed to complete it.\n"
        "Return exactly one JSON object and no prose.\n"
        "Use only tools listed in input.available_tools.\n"
        "Do not invent tool names or argument keys. If no tool is needed, return an empty actions list.\n"
        "Input JSON:\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=_json_default)}\n"
        "Output JSON:\n"
    )


def build_task_trace(
    domain: str,
    task_id: str,
    reference_actions: list[ReferenceAction],
) -> dict[str, Any]:
    decisions = sorted({f"{domain}.{action.name}.tool_choice" for action in reference_actions})
    return {
        "labels": {
            TRUSTED_TASK_INTENT: {
                "allowed": {
                    "tool_select": decisions,
                }
            }
        },
        "leases": [
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
                "control_may_depend_on": [TRUSTED_TASK_INTENT],
                "data_may_depend_on": [TRUSTED_TASK_INTENT],
            }
            for action in reference_actions
        ],
        "events": [],
        "metadata": {
            "source": "tau2 task prompt plus exact reference-action leases",
            "domain": domain,
            "task_id": task_id,
            "note": (
                "The model does not see reference actions. The gateway binds a "
                "model call to an exact lease only when tool name and arguments "
                "match a pending reference action."
            ),
        },
    }


def bind_model_call(
    *,
    domain: str,
    task_id: str,
    index: int,
    model_call: dict[str, Any],
    pending_reference_actions: list[ReferenceAction],
) -> tuple[dict[str, Any], ReferenceAction | None]:
    tool = str(model_call.get("tool", ""))
    args = dict(model_call.get("arguments") or {})
    bound = None
    for action in pending_reference_actions:
        if action.name == tool and action.args == args:
            bound = action
            break
    event_id = bound.event_id if bound else f"model:{domain}:{task_id}:{index}"
    object_name = (
        bound.object_name if bound else f"tau2.{domain}.assistant.{tool}"
    )
    event_args = dict(args)
    if bound is not None:
        event_args["_intentcap_event_id"] = bound.event_id
        event_args["intentcap_event_id"] = bound.event_id
    return (
        {
            "id": event_id,
            "op": "tool.call",
            "object": object_name,
            "args": event_args,
            "decision": f"{domain}.{tool}.tool_choice",
            "mode": "tool_select",
            "control_provenance": [TRUSTED_TASK_INTENT],
            "data_provenance": [TRUSTED_TASK_INTENT],
            "intentcap_event_type": "tau2_model_proposed_action",
            "domain": domain,
            "task_id": task_id,
            "logical_tool": tool,
        },
        bound,
    )


def build_tool_registry(
    reference_actions: list[ReferenceAction],
    env: Any,
    callable_invocations: list[dict[str, Any]],
) -> dict[str, Callable[..., Any]]:
    by_event = {action.event_id: action for action in reference_actions}
    object_names = sorted({action.object_name for action in reference_actions})
    tool_call_cls = _import_attr("tau2.data_model.message", "ToolCall")

    def make_tool(object_name: str) -> Callable[..., Any]:
        def tool(**kwargs: Any) -> Any:
            event_id = str(kwargs.pop("intentcap_event_id", ""))
            action = by_event[event_id]
            tool_args = {
                key: value
                for key, value in kwargs.items()
                if not str(key).startswith("_intentcap_")
            }
            callable_invocations.append(
                {
                    "event_id": event_id,
                    "tool": action.name,
                    "object": object_name,
                    "args": tool_args,
                }
            )
            tool_call = tool_call_cls(
                id=event_id,
                name=action.name,
                arguments=tool_args,
                requestor="assistant",
            )
            return env.get_response(tool_call)

        return tool

    return {object_name: make_tool(object_name) for object_name in object_names}


def parse_model_json(text: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "")
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def normalize_model_calls(parsed: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(parsed, dict):
        return []
    raw_actions = parsed.get("actions")
    if raw_actions is None and ("tool" in parsed or "name" in parsed):
        raw_actions = [parsed]
    if not isinstance(raw_actions, list):
        return []
    calls: list[dict[str, Any]] = []
    for raw in raw_actions:
        if not isinstance(raw, dict):
            continue
        tool = str(raw.get("tool") or raw.get("name") or "")
        arguments = raw.get("arguments", raw.get("args", {}))
        if not tool:
            continue
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append({"tool": tool, "arguments": arguments})
    return calls


def summarize(
    *,
    run_id: str,
    task_rows: list[dict[str, Any]],
    action_rows: list[dict[str, Any]],
    unsupported_rows: list[dict[str, Any]],
    domains: tuple[str, ...],
    benchmark_dir: Path,
    llama_bin: Path,
    model: Path,
    n_predict: int,
    ctx_size: int,
    gpu_layers: int,
    timeout_seconds: int,
    max_tasks_per_domain: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    unsupported_reasons = Counter(row["reason"].split(":", 1)[0] for row in unsupported_rows)
    tool_oracle_rows = [row for row in task_rows if row["tool_oracle_applicable"]]
    return {
        "run_id": run_id,
        "analysis": "fresh local Qwen tau2 task proposals through exact IntentCap task leases",
        "benchmark": "tau2-bench / tau3-bench",
        "dry_run": dry_run,
        "domains_requested": list(domains),
        "max_tasks_per_domain": max_tasks_per_domain,
        "tasks_evaluated": len(task_rows),
        "unsupported_tasks": len(unsupported_rows),
        "unsupported_reason_counts": dict(sorted(unsupported_reasons.items())),
        "model_parse_success_tasks": sum(1 for row in task_rows if row["parse_ok"]),
        "model_calls": len(action_rows),
        "tasks_with_model_calls": sum(1 for row in task_rows if int(row["model_calls"]) > 0),
        "reference_actions": sum(int(row["reference_actions"]) for row in task_rows),
        "bound_reference_calls": sum(int(row["bound_reference_calls"]) for row in task_rows),
        "gateway_allowed": sum(1 for row in action_rows if row["gateway_allowed"]),
        "gateway_blocked": sum(1 for row in action_rows if not row["gateway_allowed"]),
        "executed_calls": sum(1 for row in action_rows if row["executed"]),
        "tool_error_calls": sum(1 for row in action_rows if row["tool_error"]),
        "off_lease_calls_blocked": sum(int(row["off_lease_calls_blocked"]) for row in task_rows),
        "exact_sequence_match_tasks": sum(1 for row in task_rows if row["exact_sequence_match"]),
        "all_reference_actions_executed_tasks": sum(
            1 for row in task_rows if row["all_reference_actions_executed"]
        ),
        "action_reward_pass_tasks": sum(1 for row in task_rows if float(row["action_reward"]) == 1.0),
        "env_reward_pass_tasks": sum(1 for row in task_rows if float(row["env_reward"]) == 1.0),
        "tool_oracle_applicable_tasks": len(tool_oracle_rows),
        "tool_oracle_pass_tasks": sum(1 for row in tool_oracle_rows if row["tool_oracle_pass"]),
        "tool_oracle_pass_rate": (
            sum(1 for row in tool_oracle_rows if row["tool_oracle_pass"]) / len(tool_oracle_rows)
            if tool_oracle_rows
            else 1.0
        ),
        "action_outcome_counts": _counts(
            "allowed" if row["gateway_allowed"] else "blocked"
            for row in action_rows
        ),
        "llama_bin": str(llama_bin),
        "llama_bin_sha256": _file_digest(llama_bin)["sha256"] if llama_bin.exists() else None,
        "llama_version": _command_output([str(llama_bin), "--version"]),
        "model": str(model),
        "model_bytes": model.stat().st_size if model.exists() else None,
        "n_predict": n_predict,
        "ctx_size": ctx_size,
        "gpu_layers": gpu_layers,
        "timeout_seconds": timeout_seconds,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": _sha256(Path(__file__).read_bytes()),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "input_digests": [
            _file_digest(benchmark_dir / "data" / "tau2" / "domains" / domain / "tasks.json")
            for domain in domains
        ],
        "notes": [
            "This run uses the existing local tau2-bench artifact only; it does not clone, sync, or download datasets.",
            "The model sees task text and tool schemas, but not evaluation_criteria.actions.",
            "Exact reference-action leases are used as the oracle authorization profile; this is not a complete lease compiler evaluation.",
            "By default this is a mock-domain pilot, not a benchmark-scale tau2/tau3 online run.",
        ],
    }


def _reference_actions(domain: str, task_id: str, criteria: dict[str, Any]) -> list[ReferenceAction]:
    actions: list[ReferenceAction] = []
    for index, action in enumerate(criteria.get("actions") or []):
        if not isinstance(action, dict):
            continue
        if str(action.get("requestor", "assistant")) != "assistant":
            continue
        name = str(action.get("name", ""))
        action_id = str(action.get("action_id", index))
        actions.append(
            ReferenceAction(
                event_id=_reference_event_id(domain, task_id, action_id, index),
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
        )
    return actions


def _reference_event_id(domain: str, task_id: str, action_id: str, index: int) -> str:
    return f"{domain}:{task_id}:{action_id or index}"


def _tool_schemas(env: Any) -> list[dict[str, Any]]:
    schemas = []
    tools = env.tools.get_tools() if getattr(env, "tools", None) is not None else {}
    for name, tool in sorted(tools.items()):
        schema = tool.openai_schema.get("function", {})
        schemas.append(
            {
                "name": name,
                "description": schema.get("description", ""),
                "parameters": schema.get("parameters", {}),
            }
        )
    return schemas


def _import_module(module_name: str) -> Any:
    __import__(module_name)
    return sys.modules[module_name]


def _import_attr(module_name: str, attr_name: str) -> Any:
    module = _import_module(module_name)
    return getattr(module, attr_name)


def _safe_id(domain: str, task_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_id).strip("_") or "task"
    return f"{domain}_{safe}"


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _input_digest_csv(benchmark_dir: Path, domains: tuple[str, ...]) -> str:
    rows = [
        _file_digest(benchmark_dir / "data" / "tau2" / "domains" / domain / "tasks.json")
        for domain in domains
    ]
    lines = ["path,sha256,bytes"]
    lines.extend(f"{row['path']},{row['sha256']},{row['bytes']}" for row in rows)
    return "\n".join(lines) + "\n"


def _raw_payload(stdout: str, stderr: str, returncode: int) -> str:
    return json.dumps(
        {"returncode": returncode, "stdout": stdout, "stderr": stderr},
        indent=2,
        sort_keys=True,
    )


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return str(value)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _command_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
    except (OSError, subprocess.SubprocessError):
        return ""


def _git_output(command: list[str]) -> str:
    return _command_output(command) or "unavailable"


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
