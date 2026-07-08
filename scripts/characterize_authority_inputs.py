"""Characterize issuer classes in saved IntentCap traces.

This is a trace-level characterization, not a new online benchmark run.  It
uses existing IntentCap artifacts to answer a reviewer-facing question: are
agent/instruction/tool/env issuer classes exercised by concrete workflows, and
which unsafe substitutions would be admitted if those classes were collapsed?
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from intentcap.checker import check_trace


ISSUER_CLASSES = ("agent", "instruction", "tool", "env")

DEFAULT_TRACE_PATHS = (
    Path("examples/env_adapter_side_effect_suite.json"),
    Path("examples/residual_workflow_policy_suite.json"),
    Path("results/agentdojo/R011/intentcap_trace.json"),
    Path("results/mcptox/R007/intentcap_trace.json"),
    Path("results/online/R010/export/intentcap_trace.json"),
    Path("results/tau2/R024/intentcap_traces.json"),
)

DEFAULT_RUNTIME_SUMMARY_PATHS = (
    Path("results/eval/R136/task_gateway_summary.json"),
)

EVENT_FIELDS = [
    "source",
    "source_path",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "checker_allowed",
    "required_classes",
    "control_classes",
    "data_classes",
    "requires_multiple_classes",
    "requires_env",
    "has_class_substitution_attempt",
    "substitution_edges",
]

CLASS_FIELDS = [
    "class_name",
    "required_events",
    "control_source_events",
    "data_source_events",
    "denied_substitution_attempts",
]

COLLAPSE_FIELDS = ["substitution_edge", "events", "example_event_ids"]

RUNTIME_FIELDS = [
    "path",
    "reference_actions",
    "model_calls",
    "executed_calls",
    "runtime_binding_attempts",
    "runtime_binding_successes",
    "runtime_binding_missing_evidence",
    "runtime_binding_missing_value_proof",
    "runtime_evidence_hint_steps",
    "tool_oracle_pass_tasks",
    "tool_oracle_pass_rate",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Characterize IntentCap authority-input classes")
    parser.add_argument("--run-id", default="R220AUTHCHAR")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--trace", dest="traces", action="append", type=Path, default=None)
    parser.add_argument(
        "--runtime-summary",
        dest="runtime_summaries",
        action="append",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    trace_paths = tuple(args.traces) if args.traces else DEFAULT_TRACE_PATHS
    runtime_paths = (
        tuple(args.runtime_summaries)
        if args.runtime_summaries
        else DEFAULT_RUNTIME_SUMMARY_PATHS
    )
    result = analyze(run_id=args.run_id, trace_paths=trace_paths, runtime_paths=runtime_paths)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "authority_input_characterization_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "event_authority_characterization.csv", result["event_rows"], EVENT_FIELDS)
    _write_rows(args.output_dir / "issuer_class_summary.csv", result["class_rows"], CLASS_FIELDS)
    _write_rows(args.output_dir / "collapse_risk_summary.csv", result["collapse_rows"], COLLAPSE_FIELDS)
    _write_rows(args.output_dir / "runtime_evidence_summary.csv", result["runtime_rows"], RUNTIME_FIELDS)
    _write_rows(args.output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(
    *,
    run_id: str,
    trace_paths: tuple[Path, ...],
    runtime_paths: tuple[Path, ...],
) -> dict[str, Any]:
    event_rows: list[dict[str, Any]] = []
    for path in trace_paths:
        if not path.exists():
            continue
        for source_name, trace in _load_trace_units(path):
            event_rows.extend(_event_rows(source_name, path, trace))

    runtime_rows = [_runtime_row(path) for path in runtime_paths if path.exists()]
    class_rows = _class_rows(event_rows)
    collapse_rows = _collapse_rows(event_rows)
    input_paths = [path for path in (*trace_paths, *runtime_paths) if path.exists()]
    input_digests = [_file_digest(path) for path in input_paths]
    summary = _summary(
        run_id=run_id,
        trace_paths=trace_paths,
        runtime_paths=runtime_paths,
        event_rows=event_rows,
        class_rows=class_rows,
        collapse_rows=collapse_rows,
        runtime_rows=runtime_rows,
        input_digests=input_digests,
    )
    return {
        "summary": summary,
        "event_rows": event_rows,
        "class_rows": class_rows,
        "collapse_rows": collapse_rows,
        "runtime_rows": runtime_rows,
        "input_digests": input_digests,
    }


def _load_trace_units(path: Path) -> list[tuple[str, dict[str, Any]]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        units: list[tuple[str, dict[str, Any]]] = []
        for index, item in enumerate(payload):
            trace = item.get("trace", item)
            source = _source_name(path, item, index)
            units.append((source, trace))
        return units
    return [(_source_name(path, payload, 0), payload)]


def _source_name(path: Path, item: dict[str, Any], index: int) -> str:
    if "domain" in item and "task_id" in item:
        return f"{path.parent.name}:{item['domain']}:{item['task_id']}"
    intent = item.get("intent", {}) if isinstance(item, dict) else {}
    if "id" in intent:
        return f"{path.parent.name}:{intent['id']}"
    return f"{path.parent.name}:{path.stem}:{index}"


def _event_rows(source: str, path: Path, trace: dict[str, Any]) -> list[dict[str, Any]]:
    labels = trace.get("labels", {})
    verdicts = check_trace(trace)
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(trace.get("events", [])):
        verdict = verdicts[index]
        control_classes = _classes_for_sources(event.get("control_provenance", []), labels)
        data_classes = _classes_for_sources(event.get("data_provenance", []), labels)
        required_classes = _required_classes(event, control_classes, data_classes)
        substitution_edges = _substitution_edges(
            event=event,
            checker_allowed=bool(verdict["allowed"]),
            required_classes=required_classes,
            control_classes=control_classes,
        )
        rows.append(
            {
                "source": source,
                "source_path": str(path),
                "event_id": str(event.get("id", "")),
                "op": str(event.get("op", "")),
                "object": str(event.get("object", "")),
                "mode": str(event.get("mode", "")),
                "decision": str(event.get("decision", "")),
                "checker_allowed": bool(verdict["allowed"]),
                "required_classes": "|".join(sorted(required_classes)),
                "control_classes": "|".join(sorted(control_classes)),
                "data_classes": "|".join(sorted(data_classes)),
                "requires_multiple_classes": len(required_classes) > 1,
                "requires_env": "env" in required_classes,
                "has_class_substitution_attempt": bool(substitution_edges),
                "substitution_edges": "|".join(sorted(substitution_edges)),
            }
        )
    return rows


def _classes_for_sources(sources: Any, labels: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for source in _as_list(sources):
        result.add(_class_for_source(str(source), labels.get(str(source), {})))
    return result


def _class_for_source(source: str, label: dict[str, Any]) -> str:
    text = " ".join(
        str(part).lower()
        for part in (
            source,
            label.get("origin", ""),
            label.get("integrity", ""),
            json.dumps(label.get("allowed", {}), sort_keys=True),
        )
    )
    if any(marker in text for marker in ("tool_response", "tool_result", "script_output")):
        return "env"
    if any(marker in text for marker in ("tool_description", "tool_metadata", "schema", "mcp_tool")):
        return "tool"
    if any(marker in text for marker in ("skill", "manual", "instruction", "workflow")):
        return "instruction"
    if any(marker in text for marker in ("user_intent", "user_request", "repo_selection", "approval", "tau2_reference")):
        return "agent"
    if any(marker in text for marker in ("pdf", "uploaded", "webpage", "runtime", "file", "summary", "injection", "attacker", "poison")):
        return "env"
    if "policy" in text:
        return "instruction"
    if "trusted" in text:
        return "agent"
    return "env"


def _required_classes(
    event: dict[str, Any],
    control_classes: set[str],
    data_classes: set[str],
) -> set[str]:
    mode = str(event.get("mode", ""))
    op = str(event.get("op", ""))
    decision = str(event.get("decision", ""))
    text = " ".join((mode, op, decision, str(event.get("object", "")))).lower()
    required: set[str] = set()

    if mode in {"authorize", "sink_select", "delegate", "policy_update"}:
        required.add("agent")
    if mode == "tool_select" or op in {"tool.call", "mcp.call", "exec.run"}:
        required.update({"agent", "tool"})
    if mode in {"read", "write", "execute"} or op in {"fs.read", "fs.write", "exec.run", "net.connect"}:
        required.update({"agent", "env"})
    if op == "ctx.use":
        required.add("env")
    if "deleg" in text:
        required.update({"agent", "instruction", "env"})
    if "local" in text or "filesystem" in text or "exec" in text:
        required.update({"agent", "tool", "env"})
    if control_classes & {"instruction"}:
        required.add("instruction")
    if data_classes & {"env"} and mode in {"parameterize", "summarize", "read", "write", "execute"}:
        required.add("env")
    if not required:
        required.add("agent")
    return required


def _substitution_edges(
    *,
    event: dict[str, Any],
    checker_allowed: bool,
    required_classes: set[str],
    control_classes: set[str],
) -> set[str]:
    if checker_allowed:
        return set()
    mode = str(event.get("mode", ""))
    edges: set[str] = set()
    if mode in {"authorize", "sink_select", "policy_update", "delegate"}:
        for cls in control_classes - {"agent"}:
            edges.add(f"{cls}->agent")
    if "tool" in required_classes:
        for cls in control_classes - {"tool", "agent", "instruction"}:
            edges.add(f"{cls}->tool")
    if "instruction" in required_classes:
        for cls in control_classes - {"instruction", "agent"}:
            edges.add(f"{cls}->instruction")
    return edges


def _class_rows(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for class_name in ISSUER_CLASSES:
        rows.append(
            {
                "class_name": class_name,
                "required_events": sum(
                    1 for row in event_rows if class_name in _split(row["required_classes"])
                ),
                "control_source_events": sum(
                    1 for row in event_rows if class_name in _split(row["control_classes"])
                ),
                "data_source_events": sum(
                    1 for row in event_rows if class_name in _split(row["data_classes"])
                ),
                "denied_substitution_attempts": sum(
                    1
                    for row in event_rows
                    if not row["checker_allowed"]
                    and any(edge.startswith(f"{class_name}->") for edge in _split(row["substitution_edges"]))
                ),
            }
        )
    return rows


def _collapse_rows(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: dict[str, list[str]] = {}
    counts: Counter[str] = Counter()
    for row in event_rows:
        for edge in _split(row["substitution_edges"]):
            counts[edge] += 1
            examples.setdefault(edge, [])
            if len(examples[edge]) < 5:
                examples[edge].append(str(row["event_id"]))
    return [
        {
            "substitution_edge": edge,
            "events": count,
            "example_event_ids": "|".join(examples.get(edge, [])),
        }
        for edge, count in sorted(counts.items())
    ]


def _runtime_row(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    return {
        "path": str(path),
        "reference_actions": _int(payload.get("reference_actions")),
        "model_calls": _int(payload.get("model_calls")),
        "executed_calls": _int(payload.get("executed_calls")),
        "runtime_binding_attempts": _int(payload.get("compiler_runtime_binding_attempts")),
        "runtime_binding_successes": _int(payload.get("compiler_runtime_binding_successes")),
        "runtime_binding_missing_evidence": _int(payload.get("compiler_runtime_binding_missing_evidence")),
        "runtime_binding_missing_value_proof": _int(payload.get("compiler_runtime_binding_missing_value_proof")),
        "runtime_evidence_hint_steps": _int(payload.get("stepwise_runtime_evidence_lease_hint_steps")),
        "tool_oracle_pass_tasks": _int(payload.get("tool_oracle_pass_tasks")),
        "tool_oracle_pass_rate": float(payload.get("tool_oracle_pass_rate", 0.0) or 0.0),
    }


def _summary(
    *,
    run_id: str,
    trace_paths: tuple[Path, ...],
    runtime_paths: tuple[Path, ...],
    event_rows: list[dict[str, Any]],
    class_rows: list[dict[str, Any]],
    collapse_rows: list[dict[str, Any]],
    runtime_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    required_set_counts = Counter(row["required_classes"] for row in event_rows)
    control_set_counts = Counter(row["control_classes"] for row in event_rows)
    denied_substitutions = sum(1 for row in event_rows if row["has_class_substitution_attempt"])
    runtime_attempts = sum(row["runtime_binding_attempts"] for row in runtime_rows)
    runtime_successes = sum(row["runtime_binding_successes"] for row in runtime_rows)
    return {
        "run_id": run_id,
        "trace_paths": [str(path) for path in trace_paths if path.exists()],
        "runtime_summary_paths": [str(path) for path in runtime_paths if path.exists()],
        "events": len(event_rows),
        "checker_allowed": sum(1 for row in event_rows if row["checker_allowed"]),
        "checker_denied": sum(1 for row in event_rows if not row["checker_allowed"]),
        "events_requiring_multiple_issuer_classes": sum(
            1 for row in event_rows if row["requires_multiple_classes"]
        ),
        "events_requiring_env": sum(1 for row in event_rows if row["requires_env"]),
        "denied_events_with_class_substitution_attempt": denied_substitutions,
        "required_class_set_counts": dict(sorted(required_set_counts.items())),
        "control_class_set_counts": dict(sorted(control_set_counts.items())),
        "class_rows": class_rows,
        "collapse_rows": collapse_rows,
        "runtime_binding_attempts": runtime_attempts,
        "runtime_binding_successes": runtime_successes,
        "runtime_binding_success_rate": runtime_successes / runtime_attempts if runtime_attempts else 0.0,
        "runtime_evidence_hint_steps": sum(row["runtime_evidence_hint_steps"] for row in runtime_rows),
        "input_digests": input_digests,
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "notes": [
            "This characterization uses existing local artifacts only; it does not sync or download datasets.",
            "Issuer classes are derived from existing provenance labels and event modes, so counts are trace-level annotations rather than independent human labels.",
            "Runtime-binding rows are pilot evidence that env/runtime observer facts are used to mint one-shot leases from executed tool results.",
        ],
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _split(value: Any) -> set[str]:
    if value is None:
        return set()
    return {part for part in str(value).split("|") if part}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": _sha256(data),
        "bytes": len(data),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
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
