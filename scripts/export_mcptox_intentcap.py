"""Export MCPTox tool-poisoning cases into IntentCap-style traces.

This script does not run an LLM. It reads MCPTox's published response labels
and converts successful malicious tool-call responses into protected-decision
events whose control provenance is the poisoned MCP tool description.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.checker import check_trace


SINK_KEYS = {
    "account",
    "accounts",
    "address",
    "addresses",
    "channel",
    "channels",
    "email",
    "emails",
    "host",
    "phone",
    "recipient",
    "recipients",
    "repo",
    "repository",
    "sender",
    "to",
    "url",
    "webhook",
}

SINK_WORDS = (
    "email",
    "message",
    "navigate",
    "post",
    "publish",
    "redirect",
    "request",
    "send",
    "share",
    "transfer",
    "upload",
)

AUTHORITY_WORDS = (
    "create",
    "delete",
    "drop",
    "edit",
    "evaluate",
    "execute",
    "insert",
    "move",
    "query",
    "read",
    "remove",
    "run",
    "update",
    "write",
)

AUTHORITY_RISKS = {
    "Code Injection",
    "Credential Leakage",
    "Data Tampering",
    "Financial Loss",
    "Infrastructure Damage",
    "Instruction Tampering",
    "Privacy Leakage",
    "Service Disruption",
}

SINK_RISKS = {
    "Message Hijacking",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export MCPTox labeled responses as IntentCap traces")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/mcptox"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--success-label", default="Success")
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    response_all = _load_json(args.benchmark_dir / "response_all.json")
    pure_tool = _load_json(args.benchmark_dir / "pure_tool.json")

    catalog = _catalog(response_all, pure_tool)
    trace, export_summary = _trace_from_success_labels(
        response_all,
        success_label=args.success_label,
        max_events=args.max_events,
    )

    (args.output_dir / "catalog.json").write_text(json.dumps(catalog, indent=2, sort_keys=True))
    (args.output_dir / "intentcap_trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True))

    summary = {
        **export_summary,
        "benchmark_dir": str(args.benchmark_dir),
        "success_label": args.success_label,
    }

    if args.check:
        verdicts = check_trace(trace)
        (args.output_dir / "intentcap_verdicts.json").write_text(json.dumps(verdicts, indent=2, sort_keys=True))
        summary["checker_allowed"] = sum(1 for verdict in verdicts if verdict["allowed"])
        summary["checker_denied"] = sum(1 for verdict in verdicts if not verdict["allowed"])

    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _catalog(response_all: dict[str, Any], pure_tool: list[dict[str, Any]]) -> dict[str, Any]:
    risks: Counter[str] = Counter()
    paradigms: Counter[str] = Counter()
    pure_tools = 0
    for group in pure_tool:
        for record in group.values():
            pure_tools += 1
            risks[str(record.get("security risk", ""))] += 1
            paradigms[str(record.get("paradigm", ""))] += 1

    servers = []
    for server_name, server in response_all.get("servers", {}).items():
        malicious_instances = server.get("malicious_instance", [])
        servers.append(
            {
                "server_name": server_name,
                "server_id": server.get("server_id"),
                "category_id": server.get("category_id"),
                "tool_count": len(server.get("tool_names", [])),
                "clean_query_count": len(server.get("clean_querys", [])),
                "malicious_instances": len(malicious_instances),
                "server_url": server.get("server_url"),
            }
        )

    return {
        "data_length": response_all.get("data_length"),
        "attack_scopes": response_all.get("attack_scopes", []),
        "label_scopes": response_all.get("label_scopes", []),
        "call_behaviors": response_all.get("call_behaviors", []),
        "server_count": len(response_all.get("servers", {})),
        "servers": servers,
        "pure_tool_entries": pure_tools,
        "pure_tool_risks": dict(sorted(risks.items())),
        "pure_tool_paradigms": dict(sorted(paradigms.items())),
    }


def _trace_from_success_labels(
    response_all: dict[str, Any],
    *,
    success_label: str,
    max_events: int | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    labels: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    leases: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    parse_failures: list[dict[str, Any]] = []

    for server_name, server in response_all.get("servers", {}).items():
        for instance_index, instance in enumerate(server.get("malicious_instance", [])):
            metadata = instance.get("metadata", {})
            security_risk = str(metadata.get("security risk", ""))
            paradigm = str(metadata.get("paradigm", ""))
            poisoned_tool_name = _extract_poisoned_tool_name(instance.get("poisoned_tool", ""))
            source = f"mcptox_tool_description:{server_name}:{instance_index}:{poisoned_tool_name}"
            labels[source] = {
                "origin": "mcp_tool_description",
                "integrity": "untrusted_tool_metadata",
                "allowed": {
                    "quote": ["audit.explanation"],
                    "summarize": ["user.visible_summary"],
                },
                "mcptox": {
                    "server": server_name,
                    "instance_index": instance_index,
                    "poisoned_tool": poisoned_tool_name,
                    "security_risk": security_risk,
                    "paradigm": paradigm,
                },
            }
            stats["malicious_instances_seen"] += 1
            risk_counts[security_risk] += 1

            for data_index, data in enumerate(instance.get("datas", [])):
                stats["data_records_seen"] += 1
                labels_by_model = data.get("label", {})
                responses = data.get("response", {})
                for model, label in labels_by_model.items():
                    if label != success_label:
                        continue
                    stats["success_labels_seen"] += 1
                    response = str(responses.get(model, ""))
                    calls = _extract_tool_calls(response)
                    if not calls:
                        stats["successful_responses_without_parsed_call"] += 1
                        if len(parse_failures) < 10:
                            parse_failures.append(
                                {
                                    "server": server_name,
                                    "instance_index": instance_index,
                                    "data_index": data_index,
                                    "model": model,
                                    "response_prefix": response[:240],
                                }
                            )
                        continue

                    for call_index, call in enumerate(calls):
                        if max_events is not None and len(events) >= max_events:
                            return _finalize_trace(labels, leases, events), _summary(
                                response_all,
                                stats,
                                mode_counts,
                                risk_counts,
                                parse_failures,
                            )
                        tool_name = str(call.get("tool", "<unknown>"))
                        args = _jsonable(call.get("arguments", {}))
                        if not isinstance(args, dict):
                            args = {"value": args}
                        parse_method = str(call.get("_intentcap_parse_method", "structured"))
                        decision, mode = _classify_call(server_name, tool_name, args, security_risk)
                        event_id = (
                            f"{server_name}:{instance_index}:{data.get('id', data_index)}:"
                            f"{model}:{call_index}:{tool_name}"
                        )
                        event_args = dict(args)
                        event_args["_intentcap_event_id"] = event_id
                        event_object = f"{server_name}.{tool_name}"
                        events.append(
                            {
                                "id": event_id,
                                "op": "mcp.call",
                                "object": event_object,
                                "args": event_args,
                                "decision": decision,
                                "mode": mode,
                                "control_provenance": [source],
                                "data_provenance": [source],
                                "mcptox": {
                                    "server": server_name,
                                    "instance_index": instance_index,
                                    "data_index": data_index,
                                    "data_id": data.get("id"),
                                    "model": model,
                                    "label": label,
                                    "query": data.get("query"),
                                    "poisoned_tool": poisoned_tool_name,
                                    "security_risk": security_risk,
                                    "paradigm": paradigm,
                                    "parse_method": parse_method,
                                },
                            }
                        )
                        leases.append(
                            {
                                "id": f"overbroad:{event_id}",
                                "op": "mcp.call",
                                "object": event_object,
                                "args": {
                                    "_intentcap_event_id": {
                                        "equals": event_id,
                                    },
                                },
                                "control_may_depend_on": [source],
                                "data_may_depend_on": [source],
                            }
                        )
                        stats["parsed_success_tool_calls"] += 1
                        stats[f"{parse_method}_success_tool_calls"] += 1
                        mode_counts[mode] += 1

    return _finalize_trace(labels, leases, events), _summary(
        response_all,
        stats,
        mode_counts,
        risk_counts,
        parse_failures,
    )


def _finalize_trace(
    labels: dict[str, Any],
    leases: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "intent": {
            "id": "mcptox:labeled-success-responses",
            "goal": "replay_mcptox_successful_tool_poisoning_as_untrusted_metadata_control",
        },
        "labels": labels,
        "leases": leases,
        "events": events,
    }


def _summary(
    response_all: dict[str, Any],
    stats: Counter[str],
    mode_counts: Counter[str],
    risk_counts: Counter[str],
    parse_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "servers": len(response_all.get("servers", {})),
        "benchmark_data_length": response_all.get("data_length"),
        "malicious_instances_seen": stats["malicious_instances_seen"],
        "data_records_seen": stats["data_records_seen"],
        "success_labels_seen": stats["success_labels_seen"],
        "parsed_success_tool_calls": stats["parsed_success_tool_calls"],
        "structured_success_tool_calls": stats["structured_success_tool_calls"],
        "fallback_success_tool_calls": stats["fallback_success_tool_calls"],
        "successful_responses_without_parsed_call": stats["successful_responses_without_parsed_call"],
        "trace_events": stats["parsed_success_tool_calls"],
        "mode_counts": dict(sorted(mode_counts.items())),
        "risk_counts": dict(sorted(risk_counts.items())),
        "parse_failure_samples": parse_failures,
    }


def _extract_tool_calls(response: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for candidate in _balanced_dict_candidates(response):
        parsed = _parse_dict(candidate)
        if isinstance(parsed, dict) and "tool" in parsed:
            calls.append(
                {
                    "tool": parsed.get("tool"),
                    "arguments": parsed.get("arguments", {}),
                    "_intentcap_parse_method": "structured",
                }
            )
            continue

        fallback = _parse_lax_tool_call(candidate)
        if fallback is not None:
            calls.append(fallback)
    if not calls:
        fallback = _parse_lax_tool_call(response)
        if fallback is not None:
            calls.append(fallback)
    return calls


def _balanced_dict_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    depth = 0
    start: int | None = None
    quote: str | None = None
    escaped = False

    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in ("'", '"'):
            quote = char
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : index + 1])
                start = None

    return candidates


def _parse_dict(candidate: str) -> Any:
    try:
        return json.loads(candidate)
    except (ValueError, TypeError, json.JSONDecodeError):
        pass

    for normalized in (candidate, _normalize_json_literals(candidate)):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                return ast.literal_eval(normalized)
        except (SyntaxError, ValueError, TypeError):
            continue
    return None


def _parse_lax_tool_call(candidate: str) -> dict[str, Any] | None:
    tool_match = re.search(r"['\"]tool['\"]\s*:\s*['\"]([^'\"]+)['\"]", candidate)
    if not tool_match:
        return None
    tool_name = tool_match.group(1)
    return {
        "tool": tool_name,
        "arguments": {
            "_raw_tool_call_prefix": _bounded_snippet(candidate),
        },
        "_intentcap_parse_method": "fallback",
    }


def _bounded_snippet(value: str, limit: int = 1000) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "...<truncated>"


def _normalize_json_literals(candidate: str) -> str:
    normalized = re.sub(r"(?<!['\"])\bfalse\b", "False", candidate)
    normalized = re.sub(r"(?<!['\"])\btrue\b", "True", normalized)
    normalized = re.sub(r"(?<!['\"])\bnull\b", "None", normalized)
    return normalized


def _extract_poisoned_tool_name(poisoned_tool: str) -> str:
    match = re.search(r"Tool:\s*([^\n]+)", poisoned_tool)
    if not match:
        return "<unknown>"
    return match.group(1).strip()


def _classify_call(
    server_name: str,
    tool_name: str,
    args: dict[str, Any],
    security_risk: str,
) -> tuple[str, str]:
    tool_lower = tool_name.lower()
    if security_risk in SINK_RISKS:
        return f"{server_name}.{tool_name}.sink", "sink_select"
    if any(word in tool_lower for word in SINK_WORDS):
        return f"{server_name}.{tool_name}.sink", "sink_select"
    if _contains_sinkish_value(args) or any(_is_sink_key(key) for key in args):
        return f"{server_name}.{tool_name}.sink", "sink_select"
    if security_risk in AUTHORITY_RISKS:
        return f"{server_name}.{tool_name}.authority", "authorize"
    if any(word in tool_lower for word in AUTHORITY_WORDS):
        return f"{server_name}.{tool_name}.authority", "authorize"
    return f"{server_name}.{tool_name}.tool_choice", "tool_select"


def _is_sink_key(key: str) -> bool:
    key_lower = key.lower()
    return key_lower in SINK_KEYS or any(part in SINK_KEYS for part in re.split(r"[_-]", key_lower))


def _contains_sinkish_value(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_sinkish_value(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_sinkish_value(v) for v in value)
    if not isinstance(value, str):
        return False
    lower = value.lower()
    return bool(
        re.search(r"https?://", lower)
        or re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", lower)
        or "attacker" in lower
        or "evil.com" in lower
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
