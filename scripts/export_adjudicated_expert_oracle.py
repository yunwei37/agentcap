"""Export adjudicated expert-oracle lease labels into scorer-ready rows.

This script advances the E2 expert-oracle gate after human labeling has
finished. It consumes only completed adjudicated label JSON files, validates
them with the R199/R200 schema, rejects TODO/TEMPLATE placeholders by default,
and writes flattened CSV/JSONL artifacts that downstream authority-distance
scorers can consume. It does not create expert labels, run models, execute
benchmark tools, clone repositories, sync datasets, or download data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("results/eval/R199/expert_oracle_task_manifest.csv")
DEFAULT_SCHEMA = Path("results/eval/R199/expert_lease_label_schema.json")

ORACLE_FIELDS = [
    "sample_id",
    "benchmark",
    "workload_family",
    "task_or_event_id",
    "domain_or_server",
    "protected_decision_focus",
    "label_path",
    "label_sha256",
    "labeler_id",
    "confidence",
    "intent_goal",
    "intent_trusted_sources",
    "intent_objects",
    "intent_sinks",
    "intent_expiry",
    "action_lease_count",
    "lease_operations",
    "lease_objects",
    "lease_argument_constraints_json",
    "lease_budgets_json",
    "lease_allowed_sinks",
    "budget_invocations_total",
    "context_rule_count",
    "influence_sources",
    "influence_modes",
    "decision_classes",
    "forbidden_authority_count",
    "forbidden_authority",
    "label_json",
]

VALIDATION_FIELDS = [
    "path",
    "sample_id",
    "labeler_id",
    "status",
    "placeholder_count",
    "errors",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export adjudicated expert oracle labels")
    parser.add_argument("--run-id", default="R201")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--label-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Export available valid labels even if some manifest samples are missing.",
    )
    args = parser.parse_args()

    result = export_adjudicated_oracle(
        run_id=args.run_id,
        manifest_path=args.manifest,
        schema_path=args.schema,
        label_dir=args.label_dir,
        output_dir=args.output_dir,
        allow_partial=args.allow_partial,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["export_status"] == "ok" else 1


def export_adjudicated_oracle(
    *,
    run_id: str,
    manifest_path: Path,
    schema_path: Path,
    label_dir: Path,
    output_dir: Path,
    allow_partial: bool = False,
) -> dict[str, Any]:
    manifest = _read_csv(manifest_path)
    schema = json.loads(schema_path.read_text())
    manifest_by_sample = {row["sample_id"]: row for row in manifest}
    sample_order = [row["sample_id"] for row in manifest]
    label_paths = sorted(label_dir.rglob("*.json"))

    validation_rows = _validate_label_paths(
        label_paths,
        manifest_sample_ids=set(manifest_by_sample),
        schema=schema,
    )
    ok_rows = [row for row in validation_rows if row["status"] == "ok"]
    sample_counts = Counter(row["sample_id"] for row in ok_rows)
    ambiguous_samples = sorted(sample for sample, count in sample_counts.items() if count > 1)
    valid_samples = set(sample_counts)
    ok_by_sample = {
        row["sample_id"]: row
        for row in ok_rows
        if sample_counts[row["sample_id"]] == 1
    }
    missing_samples = [sample for sample in sample_order if sample not in valid_samples]

    oracle_rows: list[dict[str, Any]] = []
    jsonl_records: list[dict[str, Any]] = []
    for sample_id in sample_order:
        validation_row = ok_by_sample.get(sample_id)
        if validation_row is None:
            continue
        path = Path(validation_row["path"])
        label = json.loads(path.read_text())
        manifest_row = manifest_by_sample[sample_id]
        oracle_rows.append(_oracle_row(manifest_row, label, path))
        jsonl_records.append(
            {
                "sample_id": sample_id,
                "manifest": manifest_row,
                "label": label,
                "label_path": str(path),
                "label_sha256": _file_digest(path)["sha256"],
            }
        )

    invalid_labels = sum(1 for row in validation_rows if row["status"] != "ok")
    blocking_missing = 0 if allow_partial else len(missing_samples)
    blocking_issues = invalid_labels + len(ambiguous_samples) + blocking_missing
    summary = {
        "run_id": run_id,
        "analysis": "adjudicated expert-oracle export",
        "manifest_samples_total": len(manifest),
        "label_paths_total": len(label_paths),
        "valid_label_paths": len(ok_rows),
        "invalid_labels": invalid_labels,
        "ambiguous_adjudicated_samples": ambiguous_samples,
        "ambiguous_adjudicated_samples_count": len(ambiguous_samples),
        "missing_samples": missing_samples,
        "missing_samples_count": len(missing_samples),
        "allow_partial": allow_partial,
        "exported_rows": len(oracle_rows),
        "samples_by_benchmark": dict(sorted(Counter(row["benchmark"] for row in manifest).items())),
        "exported_rows_by_benchmark": dict(
            sorted(Counter(row["benchmark"] for row in oracle_rows).items())
        ),
        "confidence_counts": dict(sorted(Counter(row["confidence"] for row in oracle_rows).items())),
        "export_status": "ok" if blocking_issues == 0 else "incomplete",
        "no_dataset_sync": True,
        "notes": [
            "This export consumes completed adjudicated labels; it does not create expert labels.",
            "Default validation rejects TODO/TEMPLATE placeholders through the R200 validator.",
            "Use these rows only after independent labeling and adjudication are complete.",
        ],
        "input_digests": [_file_digest(manifest_path), _file_digest(schema_path)],
        "label_digests": [_file_digest(path) for path in label_paths],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "adjudicated_expert_oracle.csv", oracle_rows, ORACLE_FIELDS)
    _write_jsonl(output_dir / "adjudicated_expert_oracle.jsonl", jsonl_records)
    _write_rows(output_dir / "label_validation_report.csv", validation_rows, VALIDATION_FIELDS)
    _write_rows(
        output_dir / "input_digests.csv",
        summary["input_digests"],
        INPUT_DIGEST_FIELDS,
    )
    (output_dir / "adjudicated_expert_oracle_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())

    return {
        "summary": summary,
        "oracle_rows": oracle_rows,
        "jsonl_records": jsonl_records,
        "validation_rows": validation_rows,
    }


def _oracle_row(manifest_row: dict[str, str], label: dict[str, Any], path: Path) -> dict[str, Any]:
    intent = label.get("intent_certificate", {})
    leases = label.get("action_leases", [])
    influence = label.get("allowed_context_influence", [])
    forbidden = _strings(label.get("forbidden_authority", []))

    return {
        "sample_id": label["sample_id"],
        "benchmark": manifest_row.get("benchmark", ""),
        "workload_family": manifest_row.get("workload_family", ""),
        "task_or_event_id": manifest_row.get("task_or_event_id", ""),
        "domain_or_server": manifest_row.get("domain_or_server", ""),
        "protected_decision_focus": manifest_row.get("protected_decision_focus", ""),
        "label_path": str(path),
        "label_sha256": _file_digest(path)["sha256"],
        "labeler_id": label.get("labeler_id", ""),
        "confidence": label.get("confidence", ""),
        "intent_goal": str(intent.get("goal", "")),
        "intent_trusted_sources": _join(_strings(intent.get("trusted_sources", []))),
        "intent_objects": _join(_strings(intent.get("objects", []))),
        "intent_sinks": _join(_strings(intent.get("sinks", []))),
        "intent_expiry": str(intent.get("expiry", "")),
        "action_lease_count": len(leases),
        "lease_operations": _join(str(lease.get("operation", "")) for lease in leases),
        "lease_objects": _join(str(lease.get("object", "")) for lease in leases),
        "lease_argument_constraints_json": _stable_json(
            [lease.get("argument_constraints", {}) for lease in leases]
        ),
        "lease_budgets_json": _stable_json([lease.get("budget", {}) for lease in leases]),
        "lease_allowed_sinks": _join(
            sink
            for lease in leases
            for sink in _strings(lease.get("allowed_sinks", []))
        ),
        "budget_invocations_total": _budget_invocations_total(leases),
        "context_rule_count": len(influence),
        "influence_sources": _join(str(rule.get("source", "")) for rule in influence),
        "influence_modes": _join(
            mode for rule in influence for mode in _strings(rule.get("modes", []))
        ),
        "decision_classes": _join(
            decision
            for rule in influence
            for decision in _strings(rule.get("decision_classes", []))
        ),
        "forbidden_authority_count": len(forbidden),
        "forbidden_authority": _join(forbidden),
        "label_json": _stable_json(label),
    }


def _budget_invocations_total(leases: list[dict[str, Any]]) -> str:
    total = 0
    saw_integer = False
    for lease in leases:
        value = lease.get("budget", {}).get("invocations")
        if isinstance(value, int):
            total += value
            saw_integer = True
        elif isinstance(value, str) and value.isdigit():
            total += int(value)
            saw_integer = True
    return str(total) if saw_integer else ""


def _validate_label_paths(
    paths: list[Path],
    *,
    manifest_sample_ids: set[str],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    preparer = _load_preparer()
    return preparer.validate_label_paths(
        paths,
        manifest_sample_ids=manifest_sample_ids,
        schema=schema,
        allow_placeholders=False,
    )


def _load_preparer() -> Any:
    module_name = "prepare_expert_oracle_labels"
    if module_name in sys.modules:
        return sys.modules[module_name]
    module_path = Path(__file__).with_name("prepare_expert_oracle_labels.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _join(values: Any) -> str:
    return "|".join(str(value) for value in values if str(value))


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _file_digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _git_status() -> str:
    try:
        return subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _command_text() -> str:
    return " ".join([os.path.basename(sys.executable), *sys.argv])


if __name__ == "__main__":
    raise SystemExit(main())
