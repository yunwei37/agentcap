"""Run official cached InjecAgent model outputs through LiveToolGateway.

This runner is between replay and a full online model run. It does not call a
model API; instead, it consumes InjecAgent's released model-output archive and
turns benchmark-labeled successful attacker actions into live gateway events.
Trusted benchmark setup tools execute, while model-produced attacker decisions
must be blocked before their registered callables run.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.live_gateway import LiveToolGateway


FAMILY_TO_FILE_PREFIX = {
    "direct_harm": "dh",
    "data_stealing": "ds",
}

SINK_WORDS = (
    "email",
    "gmail",
    "message",
    "post",
    "publish",
    "send",
    "share",
    "transfer",
    "upload",
    "withdraw",
)

DATA_READ_WORDS = (
    "get",
    "list",
    "read",
    "retrieve",
    "search",
    "view",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cached InjecAgent model outputs through LiveToolGateway")
    parser.add_argument("--results-zip", type=Path, required=True)
    parser.add_argument("--model-result-dir", required=True)
    parser.add_argument("--setting", choices=["base", "enhanced"], default="base")
    parser.add_argument("--attack-family", choices=["direct_harm", "data_stealing", "all"], default="all")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument(
        "--include-counterfactual-stage2",
        action="store_true",
        help=(
            "Include cached data-stealing stage-2 model outputs. These are "
            "counterfactual for IntentCap because stage 1 is blocked first."
        ),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    loaded = _load_cached_outputs(
        args.results_zip,
        args.model_result_dir,
        setting=args.setting,
        attack_family=args.attack_family,
        max_cases=args.max_cases,
    )
    trace = _trace_from_cached_outputs(
        loaded,
        include_counterfactual_stage2=args.include_counterfactual_stage2,
    )
    callable_invocations: list[dict[str, Any]] = []
    tools = _tool_registry(trace, callable_invocations)
    gateway = LiveToolGateway(trace, tools)
    records = gateway.run_events()
    summary = _summary(
        loaded,
        trace,
        records,
        callable_invocations,
        gateway.summary(records),
        tools,
        results_zip=args.results_zip,
        model_result_dir=args.model_result_dir,
        setting=args.setting,
        attack_family=args.attack_family,
        include_counterfactual_stage2=args.include_counterfactual_stage2,
    )

    (args.output_dir / "intentcap_trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True))
    (args.output_dir / "live_gateway_records.json").write_text(json.dumps(records, indent=2, sort_keys=True))
    (args.output_dir / "callable_invocations.json").write_text(
        json.dumps(callable_invocations, indent=2, sort_keys=True)
    )
    (args.output_dir / "registered_tools.json").write_text(json.dumps(sorted(tools), indent=2))
    (args.output_dir / "cached_output_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _load_cached_outputs(
    results_zip: Path,
    model_result_dir: str,
    *,
    setting: str,
    attack_family: str,
    max_cases: int | None = None,
) -> list[dict[str, Any]]:
    families = ["direct_harm", "data_stealing"] if attack_family == "all" else [attack_family]
    loaded: list[dict[str, Any]] = []
    with zipfile.ZipFile(results_zip) as zf:
        for family in families:
            prefix = FAMILY_TO_FILE_PREFIX[family]
            member = f"{model_result_dir.rstrip('/')}/test_cases_{prefix}_{setting}.json"
            with zf.open(member) as raw:
                for index, line in enumerate(raw):
                    if max_cases is not None and len(loaded) >= max_cases:
                        return loaded
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    loaded.append(
                        {
                            "family": family,
                            "setting": setting,
                            "index": index,
                            "zip_member": member,
                            "item": item,
                        }
                    )
    return loaded


def _trace_from_cached_outputs(
    loaded: list[dict[str, Any]],
    *,
    include_counterfactual_stage2: bool,
) -> dict[str, Any]:
    labels: dict[str, Any] = {}
    leases: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    for record in loaded:
        item = record["item"]
        case_id = _case_id(record)
        trusted_source = f"injecagent_user_intent:{case_id}"
        user_tool = str(item.get("User Tool", "<unknown>"))
        user_decision = f"{user_tool}.tool_choice"
        labels[trusted_source] = {
            "origin": "trusted_user_instruction",
            "integrity": "trusted_user_intent",
            "allowed": {
                "tool_select": [user_decision],
            },
        }

        user_event_id = f"{case_id}:setup:{user_tool}"
        user_args = _parse_tool_parameters(item.get("Tool Parameters"))
        user_args["_intentcap_event_id"] = user_event_id
        events.append(
            {
                "id": user_event_id,
                "op": "tool.call",
                "object": user_tool,
                "args": user_args,
                "decision": user_decision,
                "mode": "tool_select",
                "control_provenance": [trusted_source],
                "data_provenance": [trusted_source],
                "intentcap_event_type": "benchmark_setup_user_tool",
                "injecagent": _event_metadata(record, stage="setup"),
            }
        )
        leases.append(_event_lease(f"intent:{user_event_id}", user_tool, user_event_id, trusted_source))

        attacker_source = f"injecagent_cached_model_output:{case_id}"
        labels[attacker_source] = {
            "origin": "released_injecagent_model_output_with_untrusted_tool_response",
            "integrity": "untrusted_tool_response",
            "allowed": {
                "quote": ["user.visible_summary"],
                "summarize": ["user.visible_summary"],
                "parameterize": ["benign_tool.arguments"],
            },
        }

        attacker_tools = [str(tool) for tool in item.get("Attacker Tools", [])]
        if item.get("eval") == "succ" and attacker_tools:
            event_id = f"{case_id}:model_stage1:{attacker_tools[0]}"
            events.append(
                _attacker_event(
                    record,
                    event_id=event_id,
                    tool_name=attacker_tools[0],
                    source=attacker_source,
                    stage="model_stage1",
                    parameters=item.get("Attacker Tool Parameters"),
                    counterfactual=False,
                )
            )
            leases.append(_event_lease(f"overbroad:{event_id}", attacker_tools[0], event_id, attacker_source))

        if (
            include_counterfactual_stage2
            and record["family"] == "data_stealing"
            and item.get("eval") == "succ"
            and item.get("eval Step 2") == "succ"
            and len(attacker_tools) > 1
        ):
            event_id = f"{case_id}:model_stage2:{attacker_tools[1]}"
            events.append(
                _attacker_event(
                    record,
                    event_id=event_id,
                    tool_name=attacker_tools[1],
                    source=attacker_source,
                    stage="model_stage2_counterfactual",
                    parameters=_extract_action_input(item.get("output Step 2"), attacker_tools[1]),
                    counterfactual=True,
                )
            )
            leases.append(_event_lease(f"overbroad:{event_id}", attacker_tools[1], event_id, attacker_source))

    return {
        "intent": {
            "id": "injecagent:cached-model-output-live-gateway",
            "goal": "execute_benign_setup_and_block_cached_model_attacker_decisions",
        },
        "labels": labels,
        "leases": leases,
        "events": events,
    }


def _attacker_event(
    record: dict[str, Any],
    *,
    event_id: str,
    tool_name: str,
    source: str,
    stage: str,
    parameters: Any,
    counterfactual: bool,
) -> dict[str, Any]:
    decision, mode = _classify_attacker_tool(
        tool_name,
        str(record["item"].get("Attack Type", "")),
        str(record["family"]),
    )
    args = _parse_tool_parameters(parameters)
    args["_intentcap_event_id"] = event_id
    return {
        "id": event_id,
        "op": "tool.call",
        "object": tool_name,
        "args": args,
        "decision": decision,
        "mode": mode,
        "control_provenance": [source],
        "data_provenance": [source],
        "intentcap_event_type": f"cached_model_attacker_tool_{stage}",
        "counterfactual": counterfactual,
        "injecagent": _event_metadata(record, stage=stage, attacker_tool=tool_name),
    }


def _event_lease(lease_id: str, tool_name: str, event_id: str, source: str) -> dict[str, Any]:
    return {
        "id": lease_id,
        "op": "tool.call",
        "object": tool_name,
        "args": {
            "_intentcap_event_id": {
                "equals": event_id,
            },
        },
        "control_may_depend_on": [source],
        "data_may_depend_on": [source],
    }


def _tool_registry(trace: dict[str, Any], callable_invocations: list[dict[str, Any]]):
    objects = {
        str(event.get("object", ""))
        for event in trace.get("events", [])
        if event.get("op") == "tool.call"
    }
    return {
        obj: _make_recording_tool(obj, callable_invocations)
        for obj in objects
    }


def _make_recording_tool(tool_name: str, callable_invocations: list[dict[str, Any]]):
    def tool(**kwargs: Any) -> dict[str, Any]:
        callable_invocations.append(
            {
                "tool": tool_name,
                "args": kwargs,
            }
        )
        return {
            "tool": tool_name,
            "status": "executed",
        }

    return tool


def _summary(
    loaded: list[dict[str, Any]],
    trace: dict[str, Any],
    records: list[dict[str, Any]],
    callable_invocations: list[dict[str, Any]],
    gateway_summary: dict[str, Any],
    tools: dict[str, Any],
    *,
    results_zip: Path,
    model_result_dir: str,
    setting: str,
    attack_family: str,
    include_counterfactual_stage2: bool,
) -> dict[str, Any]:
    event_by_id = {str(event.get("id", "")): event for event in trace.get("events", [])}
    eval_counts: dict[str, Counter[str]] = {
        "stage1": Counter(),
        "stage2": Counter(),
    }
    case_family_counts = Counter()
    event_type_counts = Counter()
    executed_event_types = Counter()
    blocked_event_types = Counter()
    blocked_modes = Counter()
    executed_modes = Counter()
    registered_executed = 0
    registered_blocked = 0
    counterfactual_attempts = 0

    for loaded_record in loaded:
        item = loaded_record["item"]
        case_family_counts[str(loaded_record["family"])] += 1
        eval_counts["stage1"][str(item.get("eval", "missing"))] += 1
        if loaded_record["family"] == "data_stealing":
            eval_counts["stage2"][str(item.get("eval Step 2", "missing"))] += 1

    for record in records:
        decision = record.get("decision", {})
        event = event_by_id.get(str(decision.get("event_id", "")), {})
        event_type = str(event.get("intentcap_event_type", "unknown"))
        mode = str(event.get("mode", "unknown"))
        obj = str(decision.get("object", ""))
        event_type_counts[event_type] += 1
        counterfactual_attempts += int(bool(event.get("counterfactual")))
        if record.get("executed"):
            executed_event_types[event_type] += 1
            executed_modes[mode] += 1
            registered_executed += int(obj in tools)
        else:
            blocked_event_types[event_type] += 1
            blocked_modes[mode] += 1
            registered_blocked += int(obj in tools)

    return {
        **gateway_summary,
        "source": {
            "results_zip": str(results_zip),
            "results_zip_sha256": _sha256(results_zip),
            "model_result_dir": model_result_dir,
            "setting": setting,
            "attack_family": attack_family,
            "include_counterfactual_stage2": include_counterfactual_stage2,
        },
        "cases": len(loaded),
        "case_family_counts": dict(sorted(case_family_counts.items())),
        "cached_eval_counts": {
            key: dict(sorted(counts.items()))
            for key, counts in eval_counts.items()
        },
        "registered_tools": len(tools),
        "registered_executed_events": registered_executed,
        "registered_blocked_events": registered_blocked,
        "callable_invocations": len(callable_invocations),
        "callable_invocation_event_type_counts": dict(sorted(executed_event_types.items())),
        "attempted_event_type_counts": dict(sorted(event_type_counts.items())),
        "executed_event_type_counts": dict(sorted(executed_event_types.items())),
        "blocked_event_type_counts": dict(sorted(blocked_event_types.items())),
        "executed_mode_counts": dict(sorted(executed_modes.items())),
        "blocked_mode_counts": dict(sorted(blocked_modes.items())),
        "counterfactual_attempts": counterfactual_attempts,
        "missing_tool_events": sum(
            1 for record in records if record.get("decision", {}).get("action") == "missing_tool"
        ),
    }


def _case_id(record: dict[str, Any]) -> str:
    item = record["item"]
    return f"{record['setting']}:{record['family']}:{record['index']}:{item.get('User Tool', '<unknown>')}"


def _event_metadata(
    record: dict[str, Any],
    *,
    stage: str,
    attacker_tool: str | None = None,
) -> dict[str, Any]:
    item = record["item"]
    return {
        "setting": record["setting"],
        "attack_family": record["family"],
        "case_index": record["index"],
        "zip_member": record["zip_member"],
        "stage": stage,
        "attack_type": item.get("Attack Type"),
        "user_tool": item.get("User Tool"),
        "attacker_tool": attacker_tool,
        "benchmark_eval": item.get("eval"),
        "benchmark_eval_step2": item.get("eval Step 2"),
    }


def _classify_attacker_tool(tool_name: str, attack_type: str, attack_family: str) -> tuple[str, str]:
    tool_lower = tool_name.lower()
    if any(word in tool_lower for word in SINK_WORDS):
        return f"{tool_name}.sink", "sink_select"
    if attack_family == "data_stealing" and any(word in tool_lower for word in DATA_READ_WORDS):
        return f"{tool_name}.authority", "authorize"
    if "data" in attack_type.lower() and any(word in tool_lower for word in DATA_READ_WORDS):
        return f"{tool_name}.authority", "authorize"
    return f"{tool_name}.authority", "authorize"


def _parse_tool_parameters(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    if not isinstance(value, str):
        return {"_raw_tool_parameters": value}

    text = value.strip()
    if _should_keep_raw(text):
        return _raw_parameters(text)

    try:
        parsed = ast.literal_eval(text)
    except (MemoryError, RecursionError, SyntaxError, ValueError):
        return _raw_parameters(text)

    if isinstance(parsed, dict):
        return dict(parsed)
    return _raw_parameters(parsed)


def _should_keep_raw(value: str) -> bool:
    return len(value) > 2048 or "\n" in value or "\\" in value


def _raw_parameters(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {"_raw_tool_parameters": value}
    return {
        "_raw_tool_parameters": value[:4096],
        "_raw_tool_parameters_truncated": len(value) > 4096,
    }


def _extract_action_input(output: Any, tool_name: str) -> str | None:
    if not isinstance(output, str):
        return None
    action_marker = f"Action: {tool_name}"
    action_index = output.find(action_marker)
    if action_index < 0:
        return None
    input_marker = "Action Input:"
    input_index = output.find(input_marker, action_index)
    if input_index < 0:
        return None
    observation_index = output.find("Observation:", input_index)
    raw = output[input_index + len(input_marker): observation_index if observation_index >= 0 else None]
    return raw.strip()


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
