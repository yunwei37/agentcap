"""Export AgentDojo tasks into IntentCap-style trace inputs.

This script does not run an LLM. It reads AgentDojo task metadata and injection
ground-truth tool calls, then emits a trace that the IntentCap offline checker
can process. Injection tasks with no ground-truth calls are reported in the
catalog as natural-language-only attack goals.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite

from intentcap.checker import check_trace


SINK_KEYS = {
    "account",
    "accounts",
    "address",
    "addresses",
    "attendee",
    "attendees",
    "channel",
    "channels",
    "email",
    "emails",
    "host",
    "participant",
    "participants",
    "recipient",
    "recipients",
    "repo",
    "sender",
    "to",
    "url",
}

DESTRUCTIVE_WORDS = ("delete", "remove", "cancel", "transfer", "send", "share", "create")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export AgentDojo metadata as IntentCap traces")
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    suite = get_suite(args.benchmark_version, args.suite)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    catalog = _catalog(suite, args.benchmark_version)
    trace = _trace_from_injection_ground_truth(suite, args.benchmark_version)

    (args.output_dir / "catalog.json").write_text(json.dumps(catalog, indent=2, sort_keys=True))
    (args.output_dir / "intentcap_trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True))

    summary = {
        "benchmark_version": args.benchmark_version,
        "suite": args.suite,
        "user_tasks": len(catalog["user_tasks"]),
        "injection_tasks": len(catalog["injection_tasks"]),
        "tools": len(catalog["tools"]),
        "injection_tasks_with_ground_truth": sum(
            1 for task in catalog["injection_tasks"] if task["ground_truth_calls"] > 0
        ),
        "trace_events": len(trace["events"]),
    }

    if args.check:
        verdicts = check_trace(trace)
        (args.output_dir / "intentcap_verdicts.json").write_text(json.dumps(verdicts, indent=2, sort_keys=True))
        summary["checker_allowed"] = sum(1 for verdict in verdicts if verdict["allowed"])
        summary["checker_denied"] = sum(1 for verdict in verdicts if not verdict["allowed"])

    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _catalog(suite: Any, benchmark_version: str) -> dict[str, Any]:
    environment = suite.load_and_inject_default_environment(suite.get_injection_vector_defaults())
    return {
        "benchmark_version": benchmark_version,
        "suite": suite.name,
        "tools": [_tool_to_dict(tool) for tool in suite.tools],
        "user_tasks": [
            {
                "id": task.ID,
                "class": type(task).__name__,
                "difficulty": str(getattr(task, "DIFFICULTY", "")),
                "prompt": getattr(task, "PROMPT", ""),
                "ground_truth_calls": len(task.ground_truth(_copy_environment(environment))),
            }
            for task in suite.user_tasks.values()
        ],
        "injection_tasks": [
            {
                "id": task.ID,
                "class": type(task).__name__,
                "difficulty": str(getattr(task, "DIFFICULTY", "")),
                "goal": getattr(task, "GOAL", ""),
                "ground_truth_calls": len(task.ground_truth(_copy_environment(environment))),
            }
            for task in suite.injection_tasks.values()
        ],
    }


def _trace_from_injection_ground_truth(suite: Any, benchmark_version: str) -> dict[str, Any]:
    environment = suite.load_and_inject_default_environment(suite.get_injection_vector_defaults())
    labels: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    leases: list[dict[str, Any]] = []

    for task in suite.injection_tasks.values():
        source = f"agentdojo_injection_goal:{task.ID}"
        labels[source] = {
            "origin": "agentdojo_injection_task",
            "integrity": "untrusted_attack_goal",
            "allowed": {
                "parameterize": ["tool.arguments", "message.body"],
                "summarize": ["user.visible_summary"],
            },
        }
        calls = task.ground_truth(_copy_environment(environment))
        for index, call in enumerate(calls):
            args = _jsonable(call.placeholder_args or call.args)
            decision, mode = _classify_call(call.function, args)
            event_id = f"{task.ID}:{index}:{call.function}"
            event_args = dict(args)
            event_args["_intentcap_event_id"] = event_id
            events.append(
                {
                    "id": event_id,
                    "op": "tool.call",
                    "object": call.function,
                    "args": event_args,
                    "decision": decision,
                    "mode": mode,
                    "control_provenance": [source],
                    "data_provenance": [source],
                    "agentdojo": {
                        "benchmark_version": benchmark_version,
                        "suite": suite.name,
                        "injection_task": task.ID,
                        "goal": getattr(task, "GOAL", ""),
                    },
                }
            )
            # This intentionally models an overbroad operation lease to isolate
            # the context-authority check: even if a tool call is otherwise
            # leased, an untrusted injection goal must not control protected
            # decisions such as sink selection or destructive actions.
            leases.append(
                {
                    "id": f"overbroad:{event_id}",
                    "op": "tool.call",
                    "object": call.function,
                    "args": {
                        "_intentcap_event_id": {
                            "equals": event_id,
                        },
                    },
                    "control_may_depend_on": [source],
                    "data_may_depend_on": [source],
                }
            )

    return {
        "intent": {
            "id": f"agentdojo:{benchmark_version}:{suite.name}",
            "goal": "replay_agentdojo_injection_ground_truth_as_untrusted_context",
        },
        "labels": labels,
        "leases": leases,
        "events": events,
    }


def _classify_call(function: str, args: dict[str, Any]) -> tuple[str, str]:
    function_lower = function.lower()
    if any(word in function_lower for word in ("delete", "remove", "cancel")):
        return f"{function}.destructive_action", "authorize"
    if any(word in function_lower for word in ("send", "share", "transfer", "create")):
        return f"{function}.sink", "sink_select"
    if any(_is_sink_key(key) for key in args):
        return f"{function}.sink", "sink_select"
    if any(word in function_lower for word in DESTRUCTIVE_WORDS):
        return f"{function}.authority", "authorize"
    return f"{function}.arguments", "parameterize"


def _is_sink_key(key: str) -> bool:
    key_lower = key.lower()
    return key_lower in SINK_KEYS or any(part in SINK_KEYS for part in re.split(r"[_-]", key_lower))


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    schema = tool.parameters.model_json_schema() if hasattr(tool.parameters, "model_json_schema") else {}
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": schema,
        "dependencies": sorted(tool.dependencies.keys()),
    }


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _copy_environment(environment: Any) -> Any:
    if hasattr(environment, "model_copy"):
        return environment.model_copy(deep=True)
    return environment.copy(deep=True)


if __name__ == "__main__":
    raise SystemExit(main())
