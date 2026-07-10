"""Run a deterministic prompt-builder context placement probe.

The probe models a prompt assembler as a live adapter: every candidate prompt
cell is checked before it is written into a section. It stresses the case where
the same source is safe in a data/interface section but unsafe in an authority
section such as policy, instruction, tool routing, or delegation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent / "src") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from intentcap.checker import CheckerSession  # noqa: E402


DEFAULT_SUITE = Path("examples/prompt_builder_context_suite.json")
DEFAULT_OUTPUT_DIR = Path("results/eval/R292PROMPTBUILDER")

AUTHORITY_SECTIONS = {
    "prompt.policy_section",
    "prompt.instruction_section",
    "prompt.tool_section",
    "prompt.delegation_section",
}

ROW_FIELDS = [
    "backend",
    "index",
    "event_id",
    "pair_id",
    "pair_role",
    "object",
    "mode",
    "decision",
    "destination",
    "allowed",
    "placed",
    "authority_section",
    "unsafe_reference_event",
    "unsafe_authority_placement",
    "reason",
    "latency_ms",
    "section_size",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run prompt-builder context placement probe")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default="R292PROMPTBUILDER")
    args = parser.parse_args()

    result = run_probe(suite_path=args.suite, output_dir=args.output_dir, run_id=args.run_id)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def run_probe(*, suite_path: Path, output_dir: Path, run_id: str) -> dict[str, Any]:
    suite_bytes = suite_path.read_bytes()
    suite = json.loads(suite_bytes)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    intentcap_builder = _PromptBuilder(backend="intentcap", suite=suite)
    object_only_builder = _PromptBuilder(backend="object_only", suite=suite)
    intentcap_rows = intentcap_builder.run()
    object_rows = object_only_builder.run()
    rows = [*intentcap_rows, *object_rows]
    summary = _summary(
        run_id=run_id,
        suite_path=suite_path,
        suite_bytes=suite_bytes,
        output_dir=output_dir,
        intentcap_builder=intentcap_builder,
        object_builder=object_only_builder,
        rows=rows,
    )

    _write_rows(output_dir / "prompt_builder_context_rows.csv", rows)
    (output_dir / "prompt_builder_context_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "intentcap_prompt.json").write_text(
        json.dumps(intentcap_builder.sections, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "object_only_prompt.json").write_text(
        json.dumps(object_only_builder.sections, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "input_digests.csv").write_text(
        "path,sha256,bytes\n"
        f"{suite_path},{hashlib.sha256(suite_bytes).hexdigest()},{len(suite_bytes)}\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


class _PromptBuilder:
    def __init__(self, *, backend: str, suite: dict[str, Any]) -> None:
        self.backend = backend
        self.suite = suite
        self.session = CheckerSession.from_trace(suite)
        self.sections: dict[str, list[dict[str, Any]]] = {}
        self.exposed_objects = {
            (str(lease.get("op", "")), str(lease.get("object", "")))
            for lease in suite.get("leases", [])
        }

    def run(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, event in enumerate(self.suite.get("events", [])):
            started = time.perf_counter()
            verdict = self._authorize(event)
            placed = False
            section_size = 0
            if verdict["allowed"]:
                destination = _destination(event)
                cell = {
                    "event_id": str(event.get("id", "")),
                    "object": str(event.get("object", "")),
                    "mode": str(event.get("mode", "")),
                    "content": event.get("content", ""),
                }
                self.sections.setdefault(destination, []).append(cell)
                section_size = len(self.sections[destination])
                placed = True
            latency_ms = (time.perf_counter() - started) * 1000.0
            destination = _destination(event)
            authority_section = destination in AUTHORITY_SECTIONS
            unsafe = bool(event.get("unsafe_reference_event"))
            rows.append(
                {
                    "backend": self.backend,
                    "index": index,
                    "event_id": str(event.get("id", "")),
                    "pair_id": str(event.get("pair_id", "")),
                    "pair_role": str(event.get("pair_role", "")),
                    "object": str(event.get("object", "")),
                    "mode": str(event.get("mode", "")),
                    "decision": str(event.get("decision", "")),
                    "destination": destination,
                    "allowed": bool(verdict["allowed"]),
                    "placed": placed,
                    "authority_section": authority_section,
                    "unsafe_reference_event": unsafe,
                    "unsafe_authority_placement": unsafe and placed and authority_section,
                    "reason": str(verdict["reason"]),
                    "latency_ms": f"{latency_ms:.3f}",
                    "section_size": section_size,
                }
            )
        return rows

    def _authorize(self, event: dict[str, Any]) -> dict[str, Any]:
        if self.backend == "intentcap":
            return self.session.check(event)
        if self.backend == "object_only":
            key = (str(event.get("op", "")), str(event.get("object", "")))
            allowed = key in self.exposed_objects
            return {
                "allowed": allowed,
                "reason": "object-only prompt source match" if allowed else "object-only no source",
                "lease_id": None,
            }
        raise ValueError(f"unknown backend: {self.backend}")


def _summary(
    *,
    run_id: str,
    suite_path: Path,
    suite_bytes: bytes,
    output_dir: Path,
    intentcap_builder: _PromptBuilder,
    object_builder: _PromptBuilder,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    intentcap_rows = [row for row in rows if row["backend"] == "intentcap"]
    object_rows = [row for row in rows if row["backend"] == "object_only"]
    return {
        "run_id": run_id,
        "analysis": "prompt-builder context placement adapter",
        "suite_path": str(suite_path),
        "input_suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
        "events": len(intentcap_rows),
        "owner_classes_exercised": _owner_classes(suite=intentcap_builder.suite),
        "owner_class_count": len(_owner_classes(suite=intentcap_builder.suite)),
        "authority_sections": sorted(AUTHORITY_SECTIONS),
        "authority_section_count": len(AUTHORITY_SECTIONS),
        "intentcap_placed": _count(intentcap_rows, "placed"),
        "intentcap_blocked": len(intentcap_rows) - _count(intentcap_rows, "placed"),
        "intentcap_authority_section_placements": _authority_placements(intentcap_rows),
        "intentcap_unsafe_authority_placements": _count(
            intentcap_rows,
            "unsafe_authority_placement",
        ),
        "intentcap_blocked_unsafe_promotions": sum(
            1
            for row in intentcap_rows
            if row["unsafe_reference_event"] and not row["placed"]
        ),
        "intentcap_sections": _section_sizes(intentcap_builder.sections),
        "object_only_placed": _count(object_rows, "placed"),
        "object_only_authority_section_placements": _authority_placements(object_rows),
        "object_only_unsafe_authority_placements": _count(
            object_rows,
            "unsafe_authority_placement",
        ),
        "object_only_sections": _section_sizes(object_builder.sections),
        "paired_source_promotions": _paired_source_promotions(intentcap_rows),
        "paired_source_promotions_blocked": _paired_source_promotions_blocked(intentcap_rows),
        "object_only_paired_promotions_unsafe": _paired_source_promotions_unsafe(object_rows),
        "mean_intentcap_latency_ms": _mean_latency(intentcap_rows),
        "max_intentcap_latency_ms": _max_latency(intentcap_rows),
        "output_dir": str(output_dir),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "notes": [
            "IntentCap checks every prompt cell before writing it into a section.",
            "Object-only prompt assembly ignores destination, mode, and owner-aware lease constraints.",
            "The probe is a deterministic prompt-builder adapter, not a production prompt runtime.",
        ],
    }


def _destination(event: dict[str, Any]) -> str:
    args = event.get("args", {})
    if isinstance(args, dict) and "destination" in args:
        return str(args["destination"])
    return str(event.get("decision", ""))


def _owner_classes(*, suite: dict[str, Any]) -> list[str]:
    classes = {
        str(label.get("owner_class", ""))
        for label in suite.get("labels", {}).values()
        if isinstance(label, dict) and label.get("owner_class")
    }
    return sorted(classes)


def _count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if row[field])


def _authority_placements(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row["placed"] and row["authority_section"])


def _section_sizes(sections: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {name: len(items) for name, items in sorted(sections.items())}


def _paired_source_promotions(rows: list[dict[str, Any]]) -> int:
    pairs: dict[str, set[str]] = {}
    for row in rows:
        pair_id = str(row.get("pair_id", ""))
        role = str(row.get("pair_role", ""))
        if not pair_id or not role:
            continue
        if role in {"data_allowed", "allowed_authority"} and row.get("placed"):
            pairs.setdefault(pair_id, set()).add("source_allowed")
        if role == "control_blocked" and not row.get("placed"):
            pairs.setdefault(pair_id, set()).add("promotion_blocked")
    return sum(1 for roles in pairs.values() if {"source_allowed", "promotion_blocked"} <= roles)


def _paired_source_promotions_blocked(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if row.get("pair_role") == "control_blocked" and not row.get("placed")
    )


def _paired_source_promotions_unsafe(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if row.get("pair_role") == "control_blocked"
        and row.get("unsafe_authority_placement")
    )


def _mean_latency(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return round(sum(float(row["latency_ms"]) for row in rows) / len(rows), 3)


def _max_latency(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return round(max(float(row["latency_ms"]) for row in rows), 3)


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ROW_FIELDS, lineterminator="\n")
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


def _git_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
