"""Prepare and validate expert-oracle lease labels.

R200 turns the R199 expert-oracle manifest into a label packet: per-labeler JSON
templates, an adjudication sheet, validation reports, input digests, and command
provenance. It does not create expert labels. Templates intentionally contain
TODO placeholders; normal validation rejects those placeholders unless
``--allow-placeholders`` is set for template-shape checks.
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
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("results/eval/R199/expert_oracle_task_manifest.csv")
DEFAULT_SCHEMA = Path("results/eval/R199/expert_lease_label_schema.json")

ADJUDICATION_FIELDS = [
    "sample_id",
    "benchmark",
    "workload_family",
    "label_a_path",
    "label_b_path",
    "adjudicated_label_path",
    "status",
    "disagreement_fields",
    "notes",
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

PLACEHOLDER_MARKERS = ("TODO", "TEMPLATE")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare expert oracle labels")
    parser.add_argument("--run-id", default="R200")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--validate-label-dir",
        type=Path,
        help="Validate completed label JSON files under this directory instead of preparing templates.",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Allow TODO/TEMPLATE markers during validation. Intended only for template-shape checks.",
    )
    parser.add_argument(
        "--labeler",
        action="append",
        default=None,
        help="Labeler id to template; default: expert_a and expert_b.",
    )
    args = parser.parse_args()

    if args.output_dir is None:
        parser.error("--output-dir is required")

    if args.validate_label_dir is not None:
        result = validate_label_dir(
            label_dir=args.validate_label_dir,
            manifest_path=args.manifest,
            schema_path=args.schema,
            output_dir=args.output_dir,
            allow_placeholders=args.allow_placeholders,
        )
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        return 0 if result["summary"]["invalid_labels"] == 0 else 1

    labelers = tuple(args.labeler or ["expert_a", "expert_b"])
    result = prepare(
        run_id=args.run_id,
        manifest_path=args.manifest,
        schema_path=args.schema,
        output_dir=args.output_dir,
        labelers=labelers,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def prepare(
    *,
    run_id: str,
    manifest_path: Path,
    schema_path: Path,
    output_dir: Path,
    labelers: tuple[str, ...],
) -> dict[str, Any]:
    manifest = _read_csv(manifest_path)
    schema = json.loads(schema_path.read_text())
    sample_ids = {row["sample_id"] for row in manifest}
    output_dir.mkdir(parents=True, exist_ok=True)

    template_rows: list[dict[str, Any]] = []
    label_paths: list[Path] = []
    for labeler in labelers:
        labeler_dir = output_dir / "label_templates" / labeler
        labeler_dir.mkdir(parents=True, exist_ok=True)
        for row in manifest:
            label = build_template(row, labeler)
            path = labeler_dir / f"{row['sample_id']}.json"
            path.write_text(json.dumps(label, indent=2, sort_keys=True))
            label_paths.append(path)
            template_rows.append(
                {
                    "sample_id": row["sample_id"],
                    "labeler_id": labeler,
                    "path": str(path),
                }
            )

    adjudication_rows = _adjudication_rows(manifest, labelers, output_dir)
    validation_rows = validate_label_paths(
        label_paths,
        manifest_sample_ids=sample_ids,
        schema=schema,
        allow_placeholders=True,
    )

    input_digests = [_file_digest(manifest_path), _file_digest(schema_path)]
    summary = _summary(
        run_id=run_id,
        manifest=manifest,
        labelers=labelers,
        template_rows=template_rows,
        validation_rows=validation_rows,
        input_digests=input_digests,
    )

    _write_rows(output_dir / "adjudication_sheet.csv", adjudication_rows, ADJUDICATION_FIELDS)
    _write_rows(output_dir / "template_validation_report.csv", validation_rows, VALIDATION_FIELDS)
    _write_rows(output_dir / "input_digests.csv", input_digests, INPUT_DIGEST_FIELDS)
    (output_dir / "expert_label_packet_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "README.md").write_text(_readme(run_id, labelers))
    (output_dir / "command.txt").write_text(_command_text())

    return {
        "summary": summary,
        "template_rows": template_rows,
        "validation_rows": validation_rows,
        "adjudication_rows": adjudication_rows,
        "input_digests": input_digests,
    }


def validate_label_dir(
    *,
    label_dir: Path,
    manifest_path: Path,
    schema_path: Path,
    output_dir: Path,
    allow_placeholders: bool = False,
) -> dict[str, Any]:
    manifest = _read_csv(manifest_path)
    schema = json.loads(schema_path.read_text())
    sample_ids = {row["sample_id"] for row in manifest}
    paths = sorted(label_dir.rglob("*.json"))
    rows = validate_label_paths(
        paths,
        manifest_sample_ids=sample_ids,
        schema=schema,
        allow_placeholders=allow_placeholders,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "label_validation_report.csv", rows, VALIDATION_FIELDS)
    summary = {
        "analysis": "expert-oracle label validation",
        "label_dir": str(label_dir),
        "labels_total": len(rows),
        "invalid_labels": sum(1 for row in rows if row["status"] != "ok"),
        "allow_placeholders": allow_placeholders,
        "validation_status": dict(sorted(Counter(row["status"] for row in rows).items())),
        "report_path": str(output_dir / "label_validation_report.csv"),
        "input_digests": [_file_digest(manifest_path), _file_digest(schema_path)],
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
    }
    (output_dir / "label_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    return {"summary": summary, "validation_rows": rows}


def build_template(manifest_row: dict[str, str], labeler_id: str) -> dict[str, Any]:
    sample_id = manifest_row["sample_id"]
    benchmark = manifest_row.get("benchmark", "")
    focus = manifest_row.get("protected_decision_focus", "")
    primary_object = manifest_row.get("primary_tool_or_object", "")
    task_or_event_id = manifest_row.get("task_or_event_id", "")
    domain_or_server = manifest_row.get("domain_or_server", "")
    return {
        "sample_id": sample_id,
        "labeler_id": labeler_id,
        "intent_certificate": {
            "goal": f"TODO: describe trusted user goal for {sample_id}",
            "trusted_sources": [
                "TODO: user request / explicit selection / policy / approval source"
            ],
            "objects": [
                f"TODO: scoped object(s) for {primary_object or task_or_event_id}"
            ],
            "sinks": [
                "TODO: allowed sink(s), or [] if no external sink is authorized"
            ],
            "expiry": "task_completion",
            "benchmark": benchmark,
            "task_or_event_id": task_or_event_id,
            "domain_or_server": domain_or_server,
        },
        "allowed_context_influence": [
            {
                "source": "trusted_user_intent",
                "modes": ["authorize"],
                "decision_classes": [focus or "TODO: protected decision class"],
                "constraints": "TODO: describe why this source may control the protected decision",
            },
            {
                "source": "untrusted_context",
                "modes": ["quote", "summarize", "parameterize"],
                "decision_classes": ["TODO: data-only destinations"],
                "constraints": "TODO: forbid tool/sink/approval/delegation/policy control",
            },
        ],
        "action_leases": [
            {
                "operation": "TODO: operation or tool method",
                "object": primary_object or "TODO: object/tool/resource",
                "argument_constraints": {
                    "TODO": "replace with exact values, prefixes, schemas, or predicates"
                },
                "control_may_depend_on": ["trusted_user_intent"],
                "control_must_not_depend_on": ["untrusted_context"],
                "data_may_depend_on": ["TODO: permitted data sources"],
                "allowed_sinks": ["TODO: allowed sinks"],
                "budget": {"invocations": "TODO: integer"},
                "expiry": "task_completion",
                "delegation": "none",
            }
        ],
        "forbidden_authority": [
            "TODO: list forbidden tools, sinks, approval scopes, delegation, and policy changes"
        ],
        "confidence": "low",
        "notes": (
            "TEMPLATE: replace all TODO fields before adjudication. "
            f"Manifest context: {manifest_row.get('labeler_view', '')}"
        ),
    }


def validate_label_paths(
    paths: list[Path],
    *,
    manifest_sample_ids: set[str],
    schema: dict[str, Any],
    allow_placeholders: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(paths):
        errors: list[str] = []
        try:
            label = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            rows.append(
                {
                    "path": str(path),
                    "sample_id": "",
                    "labeler_id": "",
                    "status": "invalid_json",
                    "placeholder_count": "",
                    "errors": str(exc),
                }
            )
            continue

        errors.extend(validate_label(label, schema=schema))
        sample_id = str(label.get("sample_id", ""))
        labeler_id = str(label.get("labeler_id", ""))
        if sample_id not in manifest_sample_ids:
            errors.append(f"sample_id not in manifest: {sample_id}")
        key = (sample_id, labeler_id)
        if key in seen:
            errors.append(f"duplicate label for sample_id/labeler_id: {sample_id}/{labeler_id}")
        seen.add(key)

        placeholder_count = count_placeholders(label)
        if placeholder_count and not allow_placeholders:
            errors.append(f"placeholder markers remain: {placeholder_count}")

        rows.append(
            {
                "path": str(path),
                "sample_id": sample_id,
                "labeler_id": labeler_id,
                "status": "ok" if not errors else "invalid",
                "placeholder_count": placeholder_count,
                "errors": "; ".join(errors),
            }
        )
    return rows


def validate_label(label: dict[str, Any], *, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in schema.get("required", []):
        if field not in label:
            errors.append(f"missing required field: {field}")
    if not isinstance(label.get("sample_id"), str):
        errors.append("sample_id must be a string")
    if not isinstance(label.get("labeler_id"), str):
        errors.append("labeler_id must be a string")
    if label.get("confidence") not in {"high", "medium", "low"}:
        errors.append("confidence must be high, medium, or low")

    intent = label.get("intent_certificate")
    if not isinstance(intent, dict):
        errors.append("intent_certificate must be an object")
    else:
        for field in ["goal", "trusted_sources", "objects", "sinks", "expiry"]:
            if field not in intent:
                errors.append(f"intent_certificate missing {field}")

    influence = label.get("allowed_context_influence")
    if not isinstance(influence, list):
        errors.append("allowed_context_influence must be an array")
    else:
        for index, item in enumerate(influence):
            if not isinstance(item, dict):
                errors.append(f"allowed_context_influence[{index}] must be an object")
                continue
            for field in ["source", "modes", "decision_classes"]:
                if field not in item:
                    errors.append(f"allowed_context_influence[{index}] missing {field}")
            if "modes" in item and not isinstance(item["modes"], list):
                errors.append(f"allowed_context_influence[{index}].modes must be an array")
            if "decision_classes" in item and not isinstance(item["decision_classes"], list):
                errors.append(
                    f"allowed_context_influence[{index}].decision_classes must be an array"
                )

    leases = label.get("action_leases")
    if not isinstance(leases, list):
        errors.append("action_leases must be an array")
    else:
        for index, lease in enumerate(leases):
            if not isinstance(lease, dict):
                errors.append(f"action_leases[{index}] must be an object")
                continue
            for field in ["operation", "object", "argument_constraints", "budget", "expiry"]:
                if field not in lease:
                    errors.append(f"action_leases[{index}] missing {field}")
            if "argument_constraints" in lease and not isinstance(
                lease["argument_constraints"], dict
            ):
                errors.append(f"action_leases[{index}].argument_constraints must be an object")
            if "budget" in lease and not isinstance(lease["budget"], dict):
                errors.append(f"action_leases[{index}].budget must be an object")

    if not isinstance(label.get("forbidden_authority"), list):
        errors.append("forbidden_authority must be an array")
    allowed_top = set(schema.get("properties", {}).keys())
    extra = sorted(set(label.keys()) - allowed_top)
    for field in extra:
        errors.append(f"additional top-level field not allowed: {field}")
    return errors


def count_placeholders(value: Any) -> int:
    if isinstance(value, str):
        return int(any(marker in value for marker in PLACEHOLDER_MARKERS))
    if isinstance(value, list):
        return sum(count_placeholders(item) for item in value)
    if isinstance(value, dict):
        return sum(count_placeholders(item) for item in value.values())
    return 0


def _adjudication_rows(
    manifest: list[dict[str, str]],
    labelers: tuple[str, ...],
    output_dir: Path,
) -> list[dict[str, Any]]:
    label_a = labelers[0] if labelers else "expert_a"
    label_b = labelers[1] if len(labelers) > 1 else ""
    rows = []
    for row in manifest:
        sample_id = row["sample_id"]
        rows.append(
            {
                "sample_id": sample_id,
                "benchmark": row.get("benchmark", ""),
                "workload_family": row.get("workload_family", ""),
                "label_a_path": str(output_dir / "label_templates" / label_a / f"{sample_id}.json"),
                "label_b_path": (
                    str(output_dir / "label_templates" / label_b / f"{sample_id}.json")
                    if label_b
                    else ""
                ),
                "adjudicated_label_path": str(output_dir / "adjudicated_labels" / f"{sample_id}.json"),
                "status": "needs_independent_labels",
                "disagreement_fields": "",
                "notes": "Do not score this sample until adjudicated_label_path exists.",
            }
        )
    return rows


def _summary(
    *,
    run_id: str,
    manifest: list[dict[str, str]],
    labelers: tuple[str, ...],
    template_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    input_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts = Counter(row["status"] for row in validation_rows)
    by_benchmark = Counter(row["benchmark"] for row in manifest)
    return {
        "run_id": run_id,
        "analysis": "expert-oracle label template packet",
        "samples_total": len(manifest),
        "labelers": list(labelers),
        "templates_total": len(template_rows),
        "samples_by_benchmark": dict(sorted(by_benchmark.items())),
        "template_validation_status": dict(sorted(status_counts.items())),
        "input_digests": input_digests,
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
        "no_dataset_sync": True,
        "notes": [
            "This packet contains TODO templates and validation scaffolding, not expert labels.",
            "Default final-label validation must reject templates until placeholders are removed.",
            "Score baselines only after independent labels are adjudicated.",
        ],
        "next_step": (
            "Have at least two independent reviewers fill the templates, run validation "
            "without placeholder allowance, adjudicate disagreements, then score expert-oracle distance."
        ),
    }


def _readme(run_id: str, labelers: tuple[str, ...]) -> str:
    labeler_text = ", ".join(labelers)
    return f"""# Expert Oracle Label Packet

Run: {run_id}
Labeler templates: {labeler_text}

This directory is an input packet for E2. It does not contain expert labels.

## Files

- `label_templates/<labeler>/<sample_id>.json`: TODO-filled templates.
- `adjudication_sheet.csv`: paths and status fields for adjudication.
- `template_validation_report.csv`: schema-shape validation with placeholders allowed.

## Required Workflow

1. Each labeler independently replaces every TODO in their template.
2. Validate completed labels with `python scripts/prepare_expert_oracle_labels.py --validate-label-dir <filled-label-dir> --output-dir <validation-output-dir>`.
3. Adjudicate disagreements into `adjudicated_labels/<sample_id>.json`.
4. Score baselines only against adjudicated labels.
"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


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
