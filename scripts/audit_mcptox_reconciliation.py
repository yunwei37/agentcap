"""Audit MCPTox artifact counts and IntentCap replay provenance.

This script reconciles three different MCPTox count surfaces:

* benchmark artifact counts from response_all.json;
* generated poisoned-tool records from pure_tool.json / def_tool files;
* IntentCap protected-decision events exported from successful model responses.

It does not run an LLM and does not relabel benchmark outcomes. Its purpose is
to prevent paper text from mixing cases, success labels, poisoned-tool records,
and exported protected events as if they were the same unit.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit MCPTox artifact and IntentCap replay counts")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/mcptox"))
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    response_all = _load_json(args.benchmark_dir / "response_all.json")
    pure_tool = _load_json(args.benchmark_dir / "pure_tool.json")
    trace = _load_json(args.trace)
    verdicts = _load_json(args.verdicts) if args.verdicts else []

    audit = audit_mcptox(
        response_all,
        pure_tool,
        trace,
        verdicts=verdicts,
        def_tool_dir=args.benchmark_dir / "def_tool",
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(audit["summary"], indent=2, sort_keys=True))
    (args.output_dir / "count_reconciliation.json").write_text(
        json.dumps(audit["count_reconciliation"], indent=2, sort_keys=True)
    )
    (args.output_dir / "server_audit.json").write_text(json.dumps(audit["server_audit"], indent=2, sort_keys=True))
    (args.output_dir / "risk_audit.json").write_text(json.dumps(audit["risk_audit"], indent=2, sort_keys=True))
    (args.output_dir / "parse_audit.json").write_text(json.dumps(audit["parse_audit"], indent=2, sort_keys=True))
    write_rows_csv(audit["server_audit"], args.output_dir / "server_audit.csv")
    write_rows_csv(audit["risk_audit"], args.output_dir / "risk_audit.csv")
    write_rows_csv(audit["parse_audit"], args.output_dir / "parse_audit.csv")
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(audit["summary"], indent=2, sort_keys=True))
    return 0


def audit_mcptox(
    response_all: dict[str, Any],
    pure_tool: list[dict[str, Any]],
    trace: dict[str, Any],
    *,
    verdicts: list[dict[str, Any]] | None = None,
    def_tool_dir: Path | None = None,
) -> dict[str, Any]:
    artifact = _artifact_counts(response_all, pure_tool, def_tool_dir)
    trace_counts = _trace_counts(trace, verdicts or [])
    count_reconciliation = _count_reconciliation(artifact, trace_counts)
    server_audit = _server_audit(response_all, trace)
    risk_audit = _risk_audit(response_all, trace)
    parse_audit = _parse_audit(trace)
    warnings = _warnings(artifact, trace_counts)

    summary = {
        "audit_verdict": "warn" if warnings else "pass",
        "warnings": warnings,
        "artifact_counts": artifact,
        "trace_counts": trace_counts,
        "reporting_guidance": count_reconciliation["reporting_guidance"],
    }
    return {
        "summary": summary,
        "count_reconciliation": count_reconciliation,
        "server_audit": server_audit,
        "risk_audit": risk_audit,
        "parse_audit": parse_audit,
    }


def write_rows_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _artifact_counts(
    response_all: dict[str, Any],
    pure_tool: list[dict[str, Any]],
    def_tool_dir: Path | None,
) -> dict[str, Any]:
    servers = response_all.get("servers", {})
    tool_name_refs = sum(len(server.get("tool_names", [])) for server in servers.values())
    unique_server_tool_names = {
        (server_name, tool_name)
        for server_name, server in servers.items()
        for tool_name in server.get("tool_names", [])
    }
    malicious_instances = [
        (server_name, instance)
        for server_name, server in servers.items()
        for instance in server.get("malicious_instance", [])
    ]
    data_records = [
        (server_name, instance_index, data)
        for server_name, server in servers.items()
        for instance_index, instance in enumerate(server.get("malicious_instance", []))
        for data in instance.get("datas", [])
    ]

    pure_entries: list[dict[str, Any]] = []
    for group in pure_tool:
        for record in group.values():
            pure_entries.append(record)

    label_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    labels_by_model: Counter[str] = Counter()
    successful_response_keys: set[tuple[str, int, int, Any, str]] = set()
    instances_with_success: set[tuple[str, int]] = set()
    for server_name, server in servers.items():
        for instance_index, instance in enumerate(server.get("malicious_instance", [])):
            for data_index, data in enumerate(instance.get("datas", [])):
                for model, label in data.get("label", {}).items():
                    label = str(label)
                    model = str(model)
                    label_counts[label] += 1
                    model_counts[model] += 1
                    labels_by_model[f"{model}:{label}"] += 1
                    if label == "Success":
                        successful_response_keys.add(
                            (server_name, instance_index, data_index, data.get("id"), model)
                        )
                        instances_with_success.add((server_name, instance_index))

    def_tool_files = 0
    if def_tool_dir is not None and def_tool_dir.exists():
        def_tool_files = len(list(def_tool_dir.glob("*.py")))

    return {
        "response_all_data_length": response_all.get("data_length"),
        "server_count": len(servers),
        "attack_scope_count": len(response_all.get("attack_scopes", [])),
        "attack_scopes": response_all.get("attack_scopes", []),
        "label_scopes": response_all.get("label_scopes", []),
        "call_behaviors": response_all.get("call_behaviors", []),
        "malicious_instances": len(malicious_instances),
        "data_records": len(data_records),
        "server_tool_name_refs": tool_name_refs,
        "unique_server_tool_names": len(unique_server_tool_names),
        "pure_tool_server_groups": len(pure_tool),
        "pure_tool_entries": len(pure_entries),
        "pure_tool_unique_server_tool_pairs": len(
            {(record.get("server_name"), record.get("tool_name")) for record in pure_entries}
        ),
        "def_tool_python_files": def_tool_files,
        "label_counts": dict(sorted(label_counts.items())),
        "model_counts": dict(sorted(model_counts.items())),
        "labels_by_model": dict(sorted(labels_by_model.items())),
        "success_labels": label_counts["Success"],
        "instances_with_success": len(instances_with_success),
        "successful_response_records": len(successful_response_keys),
    }


def _trace_counts(trace: dict[str, Any], verdicts: list[dict[str, Any]]) -> dict[str, Any]:
    events = trace.get("events", [])
    event_ids = {str(event.get("id")) for event in events}
    verdict_by_event = {str(verdict.get("event_id")): verdict for verdict in verdicts}
    parse_methods: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    server_counts: Counter[str] = Counter()
    success_response_keys: Counter[tuple[str, int, int, Any, str]] = Counter()
    instance_keys: set[tuple[str, int]] = set()
    data_keys: set[tuple[str, int, int, Any]] = set()

    for event in events:
        meta = event.get("mcptox", {})
        parse_methods[str(meta.get("parse_method", "unknown"))] += 1
        mode_counts[str(event.get("mode", "unknown"))] += 1
        risk_counts[str(meta.get("security_risk", "unknown"))] += 1
        model_counts[str(meta.get("model", "unknown"))] += 1
        server_counts[str(meta.get("server", "unknown"))] += 1
        server = str(meta.get("server", "unknown"))
        instance_index = int(meta.get("instance_index", -1))
        data_index = int(meta.get("data_index", -1))
        data_id = meta.get("data_id")
        model = str(meta.get("model", "unknown"))
        instance_keys.add((server, instance_index))
        data_keys.add((server, instance_index, data_index, data_id))
        success_response_keys[(server, instance_index, data_index, data_id, model)] += 1

    verdict_allowed = sum(1 for verdict in verdicts if verdict.get("allowed"))
    verdict_denied = sum(1 for verdict in verdicts if not verdict.get("allowed"))
    missing_verdicts = sorted(event_ids - set(verdict_by_event))

    return {
        "trace_events": len(events),
        "parse_method_counts": dict(sorted(parse_methods.items())),
        "mode_counts": dict(sorted(mode_counts.items())),
        "risk_event_counts": dict(sorted(risk_counts.items())),
        "model_event_counts": dict(sorted(model_counts.items())),
        "server_event_counts": dict(sorted(server_counts.items())),
        "unique_instances_with_events": len(instance_keys),
        "unique_data_records_with_events": len(data_keys),
        "unique_success_responses_with_events": len(success_response_keys),
        "events_per_success_response_counts": dict(
            sorted(Counter(success_response_keys.values()).items())
        ),
        "checker_allowed": verdict_allowed,
        "checker_denied": verdict_denied,
        "missing_verdicts": missing_verdicts,
    }


def _count_reconciliation(artifact: dict[str, Any], trace_counts: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {
            "item": "benchmark_servers",
            "recommended_reporting_unit": "MCP servers in response_all.json",
            "count": artifact["server_count"],
            "status": "paper_ready" if artifact["server_count"] == 45 else "needs_review",
        },
        {
            "item": "authentic_tools",
            "recommended_reporting_unit": "server tool-name references in response_all.json",
            "count": artifact["server_tool_name_refs"],
            "status": "paper_ready" if artifact["server_tool_name_refs"] == 353 else "needs_review",
        },
        {
            "item": "malicious_test_cases",
            "recommended_reporting_unit": "response_all.data_length / malicious_instance records",
            "count": artifact["malicious_instances"],
            "status": "paper_ready"
            if artifact["malicious_instances"] == artifact["response_all_data_length"]
            else "needs_review",
        },
        {
            "item": "poisoned_tool_records",
            "recommended_reporting_unit": "pure_tool.json generated poisoned-tool records",
            "count": artifact["pure_tool_entries"],
            "status": "artifact_only_not_authentic_tool_count",
        },
        {
            "item": "model_success_labels",
            "recommended_reporting_unit": "model responses labeled Success",
            "count": artifact["success_labels"],
            "status": "benchmark_label_count_not_case_count",
        },
        {
            "item": "intentcap_protected_events",
            "recommended_reporting_unit": "exported protected-decision events from Success responses",
            "count": trace_counts["trace_events"],
            "status": "intentcap_replay_event_count_not_case_count",
        },
    ]
    return {
        "checks": checks,
        "reporting_guidance": {
            "paper_benchmark_case_count": artifact["malicious_instances"],
            "paper_benchmark_server_count": artifact["server_count"],
            "paper_benchmark_authentic_tool_count": artifact["server_tool_name_refs"],
            "do_not_report_pure_tool_entries_as_authentic_tools": artifact["pure_tool_entries"],
            "success_labels_are_model_response_outcomes": artifact["success_labels"],
            "intentcap_events_are_replay_events": trace_counts["trace_events"],
            "fallback_events_require_separate_reporting": trace_counts["parse_method_counts"].get("fallback", 0),
        },
    }


def _server_audit(response_all: dict[str, Any], trace: dict[str, Any]) -> list[dict[str, Any]]:
    success_by_server: Counter[str] = Counter()
    event_by_server: Counter[str] = Counter()
    fallback_by_server: Counter[str] = Counter()
    instance_success_by_server: set[tuple[str, int]] = set()
    for server_name, server in response_all.get("servers", {}).items():
        for instance_index, instance in enumerate(server.get("malicious_instance", [])):
            has_success = False
            for data in instance.get("datas", []):
                for label in data.get("label", {}).values():
                    if label == "Success":
                        success_by_server[server_name] += 1
                        has_success = True
            if has_success:
                instance_success_by_server.add((server_name, instance_index))
    for event in trace.get("events", []):
        server = str(event.get("mcptox", {}).get("server", "unknown"))
        parse_method = str(event.get("mcptox", {}).get("parse_method", "unknown"))
        event_by_server[server] += 1
        if parse_method == "fallback":
            fallback_by_server[server] += 1

    rows = []
    for server_name, server in sorted(response_all.get("servers", {}).items()):
        rows.append(
            {
                "server": server_name,
                "tool_count": len(server.get("tool_names", [])),
                "malicious_instances": len(server.get("malicious_instance", [])),
                "success_labels": success_by_server[server_name],
                "instances_with_success": sum(
                    1 for key in instance_success_by_server if key[0] == server_name
                ),
                "intentcap_events": event_by_server[server_name],
                "fallback_events": fallback_by_server[server_name],
            }
        )
    return rows


def _risk_audit(response_all: dict[str, Any], trace: dict[str, Any]) -> list[dict[str, Any]]:
    instances_by_risk: Counter[str] = Counter()
    success_by_risk: Counter[str] = Counter()
    events_by_risk: Counter[str] = Counter()
    fallback_by_risk: Counter[str] = Counter()
    for server in response_all.get("servers", {}).values():
        for instance in server.get("malicious_instance", []):
            risk = str(instance.get("metadata", {}).get("security risk", "unknown"))
            instances_by_risk[risk] += 1
            for data in instance.get("datas", []):
                success_by_risk[risk] += sum(1 for label in data.get("label", {}).values() if label == "Success")
    for event in trace.get("events", []):
        meta = event.get("mcptox", {})
        risk = str(meta.get("security_risk", "unknown"))
        events_by_risk[risk] += 1
        if meta.get("parse_method") == "fallback":
            fallback_by_risk[risk] += 1

    risks = sorted(set(instances_by_risk) | set(success_by_risk) | set(events_by_risk))
    return [
        {
            "security_risk": risk,
            "malicious_instances": instances_by_risk[risk],
            "success_labels": success_by_risk[risk],
            "intentcap_events": events_by_risk[risk],
            "fallback_events": fallback_by_risk[risk],
        }
        for risk in risks
    ]


def _parse_audit(trace: dict[str, Any]) -> list[dict[str, Any]]:
    by_parse: dict[str, Counter[str]] = {}
    by_parse_mode: dict[str, Counter[str]] = {}
    for event in trace.get("events", []):
        meta = event.get("mcptox", {})
        parse_method = str(meta.get("parse_method", "unknown"))
        by_parse.setdefault(parse_method, Counter())[str(meta.get("security_risk", "unknown"))] += 1
        by_parse_mode.setdefault(parse_method, Counter())[str(event.get("mode", "unknown"))] += 1

    rows = []
    for parse_method in sorted(by_parse):
        rows.append(
            {
                "parse_method": parse_method,
                "events": sum(by_parse[parse_method].values()),
                "risk_counts": dict(sorted(by_parse[parse_method].items())),
                "mode_counts": dict(sorted(by_parse_mode[parse_method].items())),
                "paper_use": "structured event count" if parse_method == "structured" else "fallback event count; audit separately",
            }
        )
    return rows


def _warnings(artifact: dict[str, Any], trace_counts: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if artifact["pure_tool_entries"] != artifact["server_tool_name_refs"]:
        warnings.append(
            "pure_tool.json entries are generated poisoned-tool records and must not be reported as authentic tool count."
        )
    if artifact["successful_response_records"] != artifact["success_labels"]:
        warnings.append("Success label record accounting mismatch.")
    if artifact["success_labels"] != trace_counts["unique_success_responses_with_events"]:
        warnings.append("Not every Success-labeled response has an exported IntentCap event.")
    if trace_counts["trace_events"] != artifact["success_labels"]:
        warnings.append(
            "IntentCap event count differs from Success label count because some responses contain multiple tool calls."
        )
    if trace_counts["parse_method_counts"].get("fallback", 0):
        warnings.append(
            "Fallback-parsed events preserve tool names but only bounded raw argument snippets; report them separately."
        )
    if trace_counts["missing_verdicts"]:
        warnings.append("Some exported events are missing checker verdicts.")
    return warnings


def _csv_value(value: Any) -> Any:
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True)
    return value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


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
