"""Aggregate local multi-boundary system evidence for IntentCap.

This analyzer is intentionally read-only. It consolidates existing local result
summaries for env side effects, local model proposals, ActPlane-style lowering,
context placement, delegation, and Skill/manual instruction placement.
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


DEFAULT_OUTPUT_DIR = Path("results/eval/R225MULTIBOUNDARY")
DEFAULT_INPUTS = {
    "env_backend": Path("results/eval/R211ENVBACKEND/env_backend_summary.json"),
    "env_llm": Path("results/eval/R212ENVLLM/env_llm_backend_summary.json"),
    "actplane_lowering": Path("results/eval/R218ACTLOWER/actplane_lowering_summary.json"),
    "boundary_gateway": Path("results/eval/R222BOUNDARY/boundary_gateway_summary.json"),
    "boundary_baselines": Path("results/eval/R223BOUNDARYBASE/boundary_baseline_summary.json"),
    "skill_boundary": Path(
        "results/eval/R224SKILLBOUNDARY/skill_instruction_boundary_summary.json"
    ),
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

    result = analyze(output_dir=args.output_dir, inputs=inputs)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(*, output_dir: Path, inputs: dict[str, Path]) -> dict[str, Any]:
    summaries = {name: _read_json(path) for name, path in inputs.items()}
    rows = _rows(summaries)
    digests = [_file_digest(name, path) for name, path in sorted(inputs.items())]
    summary = _summary(rows=rows, digests=digests)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "multiboundary_system_evidence.csv", rows, ROW_FIELDS)
    _write_rows(output_dir / "input_digests.csv", digests, INPUT_DIGEST_FIELDS)
    (output_dir / "multiboundary_system_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


def _rows(summaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    env_backend = summaries["env_backend"]
    env_llm = summaries["env_llm"]
    actplane = summaries["actplane_lowering"]
    boundary = summaries["boundary_gateway"]
    baselines = summaries["boundary_baselines"]
    skill = summaries["skill_boundary"]

    return [
        {
            "row_id": "env_local_side_effects",
            "boundary": "fs/exec/write/context local env side effects",
            "source_run": str(env_backend.get("run_id", "R211ENVBACKEND")),
            "attempts": int(env_backend["events"]),
            "authorized_effects_or_placements": int(env_backend["intentcap_executed"]),
            "blocked_attempts": int(env_backend["intentcap_blocked"]),
            "unsafe_intentcap_effects_or_placements": int(env_backend["intentcap_unsafe_executed"]),
            "object_only_unsafe_accepts": int(env_backend["object_only_unsafe_executed"]),
            "no_provenance_unsafe_accepts": 0,
            "monitor_mismatches": 0,
            "scope_note": "real local fixture side effects before handler execution",
        },
        {
            "row_id": "env_llm_model_loop",
            "boundary": "local Qwen proposer before env side effects",
            "source_run": str(env_llm.get("run_id", "R212ENVLLM")),
            "attempts": int(env_llm["model_calls"]),
            "authorized_effects_or_placements": int(env_llm["intentcap_executed"]),
            "blocked_attempts": int(env_llm["intentcap_blocked_model_calls"]),
            "unsafe_intentcap_effects_or_placements": int(env_llm["intentcap_unsafe_executed"]),
            "object_only_unsafe_accepts": int(env_llm["object_only_unsafe_executed"]),
            "no_provenance_unsafe_accepts": 0,
            "monitor_mismatches": 0,
            "scope_note": "local model-loop safety, not benchmark-scale utility",
        },
        {
            "row_id": "actplane_style_env_lowering",
            "boundary": "env/OS monitor target",
            "source_run": str(actplane.get("run_id", "R218ACTLOWER")),
            "attempts": int(actplane["events"]),
            "authorized_effects_or_placements": int(actplane["monitor_allowed"]),
            "blocked_attempts": int(actplane["monitor_blocked"]),
            "unsafe_intentcap_effects_or_placements": int(actplane["unsafe_monitor_allowed"]),
            "object_only_unsafe_accepts": 0,
            "no_provenance_unsafe_accepts": 0,
            "monitor_mismatches": int(actplane["decision_mismatches"]),
            "scope_note": "deterministic lowering target, not production ActPlane integration",
        },
        {
            "row_id": "context_placement",
            "boundary": "prompt-section context placement",
            "source_run": str(boundary.get("run_id", "R222BOUNDARY")),
            "attempts": int(boundary["context_attempts"]),
            "authorized_effects_or_placements": int(boundary["context_placed"]),
            "blocked_attempts": int(boundary["context_blocked"]),
            "unsafe_intentcap_effects_or_placements": int(boundary["unsafe_context_placements"]),
            "object_only_unsafe_accepts": 0,
            "no_provenance_unsafe_accepts": 0,
            "monitor_mismatches": 0,
            "scope_note": "live local placement adapter, not production prompt builder",
        },
        {
            "row_id": "delegation_handoff",
            "boundary": "subagent capability handoff",
            "source_run": str(boundary.get("run_id", "R222BOUNDARY")),
            "attempts": int(boundary["delegation_attempts"]),
            "authorized_effects_or_placements": int(boundary["delegation_spawned"]),
            "blocked_attempts": int(boundary["delegation_blocked"]),
            "unsafe_intentcap_effects_or_placements": int(boundary["unsafe_delegations"]),
            "object_only_unsafe_accepts": int(baselines["object_only_unsafe_accepts"]),
            "no_provenance_unsafe_accepts": int(
                baselines["lease_args_no_provenance_unsafe_accepts"]
            ),
            "monitor_mismatches": 0,
            "scope_note": "delegation attenuation probe plus boundary baseline comparison",
        },
        {
            "row_id": "skill_instruction_placement",
            "boundary": "Skill/manual instruction-source placement",
            "source_run": str(skill.get("run_id", "R224SKILLBOUNDARY")),
            "attempts": int(skill["events"]),
            "authorized_effects_or_placements": int(skill["authorized_instruction_placements"])
            + int(skill["tool_result_data_uses_allowed"]),
            "blocked_attempts": int(skill["blocked_instruction_substitutions"]),
            "unsafe_intentcap_effects_or_placements": int(skill["checker_unsafe_accepts"]),
            "object_only_unsafe_accepts": int(skill["object_only_unsafe_accepts"]),
            "no_provenance_unsafe_accepts": int(
                skill["lease_args_no_provenance_unsafe_accepts"]
            ),
            "monitor_mismatches": 0,
            "scope_note": "controlled Skill instruction issuer substitution probe",
        },
    ]


def _summary(rows: list[dict[str, Any]], digests: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_id": "R225MULTIBOUNDARY",
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
            "Rows intentionally mix local live adapters and deterministic lowering targets; the scope_note field bounds each row.",
            "The result supports a system-surface claim, not benchmark-scale utility or production ActPlane integration.",
        ],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


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
