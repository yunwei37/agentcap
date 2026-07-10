"""Aggregate local multi-boundary system evidence for IntentCap.

This analyzer is intentionally read-only. It consolidates existing local result
summaries for historical env/placement/delegation/Skill boundaries plus the
paired integrated workflow and prompt-builder assembly probes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("results/eval/R294BOUNDARYCOVERAGE")
DEFAULT_RUN_ID = "R294BOUNDARYCOVERAGE"
DEFAULT_INPUTS = {
    "legacy_multiboundary_rows": Path(
        "results/eval/R225MULTIBOUNDARY/multiboundary_system_evidence.csv"
    ),
    "legacy_multiboundary_summary": Path(
        "results/eval/R225MULTIBOUNDARY/multiboundary_system_summary.json"
    ),
    "paired_integrated": Path("results/eval/R289PAIRED/integrated_workflow_summary.json"),
    "prompt_builder": Path("results/eval/R292PROMPTBUILDER/prompt_builder_context_summary.json"),
}

ROW_FIELDS = [
    "row_id",
    "boundary",
    "source_run",
    "attempts",
    "authorized_effects_or_placements",
    "blocked_attempts",
    "unsafe_intentcap_effects_or_placements",
    "object_only_unsafe_accepts",
    "no_provenance_unsafe_accepts",
    "monitor_mismatches",
    "scope_note",
]
INPUT_DIGEST_FIELDS = ["input_name", "path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze multi-boundary system evidence")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Override an input summary path.",
    )
    args = parser.parse_args()

    inputs = dict(DEFAULT_INPUTS)
    for item in args.input:
        name, sep, value = item.partition("=")
        if not sep or not name:
            raise SystemExit(f"invalid --input override: {item!r}")
        inputs[name] = Path(value)

    result = analyze(output_dir=args.output_dir, inputs=inputs, run_id=args.run_id)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, output_dir: Path, inputs: dict[str, Path], run_id: str = DEFAULT_RUN_ID) -> dict[str, Any]:
    legacy_rows = [_normalize_legacy_row(row) for row in _read_rows(inputs["legacy_multiboundary_rows"])]
    summaries = {
        name: _read_json(path)
        for name, path in inputs.items()
        if name != "legacy_multiboundary_rows"
    }
    _validate_legacy_summary(legacy_rows, summaries["legacy_multiboundary_summary"])
    rows = _rows(legacy_rows=legacy_rows, summaries=summaries)
    digests = [_file_digest(name, path) for name, path in sorted(inputs.items())]
    summary = _summary(rows=rows, digests=digests, run_id=run_id)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "multiboundary_system_evidence.csv", rows, ROW_FIELDS)
    _write_rows(output_dir / "input_digests.csv", digests, INPUT_DIGEST_FIELDS)
    (output_dir / "multiboundary_system_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


def _rows(
    *,
    legacy_rows: list[dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    paired = summaries["paired_integrated"]
    prompt = summaries["prompt_builder"]

    rows: list[dict[str, Any]] = list(legacy_rows)
    rows.extend(
        [
        {
            "row_id": "paired_integrated_shared_session",
            "boundary": "integrated PDF-to-issue shared checker session",
            "source_run": str(paired.get("run_id", "R289PAIRED")),
            "attempts": int(paired["events"]),
            "authorized_effects_or_placements": int(paired["intentcap_effects_or_placements"]),
            "blocked_attempts": int(paired["intentcap_blocked"]),
            "unsafe_intentcap_effects_or_placements": int(
                paired["intentcap_unsafe_effects_or_placements"]
            ),
            "object_only_unsafe_accepts": int(paired["object_only_unsafe_effects_or_placements"]),
            "no_provenance_unsafe_accepts": 0,
            "monitor_mismatches": 0,
            "scope_note": "same CheckerSession across five local boundaries; not production MCP/prompt/subagent/kernel mediation",
        },
        {
            "row_id": "prompt_builder_section_assembly",
            "boundary": "section-aware prompt-builder assembly",
            "source_run": str(prompt.get("run_id", "R292PROMPTBUILDER")),
            "attempts": int(prompt["events"]),
            "authorized_effects_or_placements": int(prompt["intentcap_placed"]),
            "blocked_attempts": int(prompt["intentcap_blocked"]),
            "unsafe_intentcap_effects_or_placements": int(
                prompt["intentcap_unsafe_authority_placements"]
            ),
            "object_only_unsafe_accepts": int(prompt["object_only_unsafe_authority_placements"]),
            "no_provenance_unsafe_accepts": 0,
            "monitor_mismatches": 0,
            "scope_note": "deterministic prompt-cell placement adapter; not production prompt runtime",
        },
        ]
    )
    return rows


def _validate_legacy_summary(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    expected = _summary(rows=rows, digests=[], run_id=str(summary.get("run_id", "")))
    checks = {
        "system_boundary_rows": "system_boundary_rows",
        "total_attempts": "total_attempts",
        "authorized_effects_or_placements": "authorized_effects_or_placements",
        "blocked_attempts": "blocked_attempts",
        "unsafe_intentcap_effects_or_placements": "unsafe_intentcap_effects_or_placements",
        "object_only_unsafe_accepts_observed": "object_only_unsafe_accepts_observed",
        "no_provenance_unsafe_accepts_observed": "no_provenance_unsafe_accepts_observed",
        "monitor_mismatches": "monitor_mismatches",
        "covered_boundaries": "covered_boundaries",
    }
    mismatches = [
        name
        for name, field in checks.items()
        if summary.get(field) != expected[field]
    ]
    if mismatches:
        joined = ", ".join(mismatches)
        raise ValueError(f"legacy R225 rows do not match summary fields: {joined}")


def _summary(rows: list[dict[str, Any]], digests: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "system_boundary_rows": len(rows),
        "total_attempts": sum(int(row["attempts"]) for row in rows),
        "authorized_effects_or_placements": sum(
            int(row["authorized_effects_or_placements"]) for row in rows
        ),
        "blocked_attempts": sum(int(row["blocked_attempts"]) for row in rows),
        "unsafe_intentcap_effects_or_placements": sum(
            int(row["unsafe_intentcap_effects_or_placements"]) for row in rows
        ),
        "object_only_unsafe_accepts_observed": sum(
            int(row["object_only_unsafe_accepts"]) for row in rows
        ),
        "no_provenance_unsafe_accepts_observed": sum(
            int(row["no_provenance_unsafe_accepts"]) for row in rows
        ),
        "monitor_mismatches": sum(int(row["monitor_mismatches"]) for row in rows),
        "covered_boundaries": [row["row_id"] for row in rows],
        "input_digests": digests,
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
        "notes": [
            "This is a read-only consolidation of existing local result summaries.",
            "It does not run models, execute side effects, or sync/download datasets.",
            "Rows intentionally mix local live adapters, deterministic lowering targets, and integrated local stress cases; the scope_note field bounds each row.",
            "The result supports a system-surface claim, not benchmark-scale utility or production ActPlane integration.",
        ],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _normalize_legacy_row(row: dict[str, str]) -> dict[str, Any]:
    numeric_fields = {
        "attempts",
        "authorized_effects_or_placements",
        "blocked_attempts",
        "unsafe_intentcap_effects_or_placements",
        "object_only_unsafe_accepts",
        "no_provenance_unsafe_accepts",
        "monitor_mismatches",
    }
    normalized: dict[str, Any] = {}
    for field in ROW_FIELDS:
        value = row[field]
        normalized[field] = int(value) if field in numeric_fields else value
    return normalized


def _file_digest(name: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "input_name": name,
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
