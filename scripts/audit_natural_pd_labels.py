"""Audit natural protected-decision owner labels.

The R221/R335 packets are author-adjudicated labeling artifacts over saved
trace rows. This audit checks that the generated labels are internally
consistent with the published field-owner protocol and, when requested, that
all selected source traces are present in the current worktree. It does not run
models, execute tools, clone repositories, sync datasets, or download data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.build_natural_pd_labeling_packet import ISSUER_CLASSES, PROTECTED_MODES


DEFAULT_PACKET_DIR = Path("results/eval/R335NATPD96")
OWNER_FIELDS = {
    "agent": "intent_or_approval_scope",
    "instruction": "workflow_procedure",
    "tool": "interface_or_sandbox_contract",
    "env": "runtime_observation",
}
REPORT_FIELDS = [
    "sample_id",
    "status",
    "checks_passed",
    "checks_failed",
    "failed_checks",
    "mode",
    "source_path",
    "required_issuers",
    "substitution_edges",
]
INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit natural protected-decision labels")
    parser.add_argument("--run-id", default="R336NATPDAUDIT")
    parser.add_argument("--packet-dir", type=Path, default=DEFAULT_PACKET_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-samples", type=int, default=1)
    parser.add_argument("--min-protected", type=int, default=1)
    parser.add_argument("--min-multiple", type=int, default=1)
    parser.add_argument("--min-env", type=int, default=0)
    parser.add_argument("--min-substitution", type=int, default=0)
    parser.add_argument("--require-existing-source", action="store_true")
    args = parser.parse_args()

    result = audit(
        run_id=args.run_id,
        packet_dir=args.packet_dir,
        output_dir=args.output_dir,
        min_samples=args.min_samples,
        min_protected=args.min_protected,
        min_multiple=args.min_multiple,
        min_env=args.min_env,
        min_substitution=args.min_substitution,
        require_existing_source=args.require_existing_source,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["audit_status"] == "ok" else 1


def audit(
    *,
    run_id: str,
    packet_dir: Path,
    output_dir: Path,
    min_samples: int,
    min_protected: int,
    min_multiple: int,
    min_env: int,
    min_substitution: int,
    require_existing_source: bool,
) -> dict[str, Any]:
    samples = _read_jsonl(packet_dir / "sample_manifest.jsonl")
    labels = {row["sample_id"]: row for row in _read_jsonl(packet_dir / "author_labels.codex.jsonl")}
    summary = _read_json(packet_dir / "natural_pd_labeling_summary.json")

    report_rows = [_audit_sample(sample, labels.get(sample["sample_id"])) for sample in samples]
    failed_rows = [row for row in report_rows if row["status"] != "ok"]
    missing_labels = sorted({sample["sample_id"] for sample in samples} - set(labels))
    extra_labels = sorted(set(labels) - {sample["sample_id"] for sample in samples})
    global_checks = _global_checks(
        packet_dir=packet_dir,
        samples=samples,
        labels=labels,
        summary=summary,
        min_samples=min_samples,
        min_protected=min_protected,
        min_multiple=min_multiple,
        min_env=min_env,
        min_substitution=min_substitution,
        require_existing_source=require_existing_source,
    )
    failed_global = [check["name"] for check in global_checks if not check["passed"]]

    source_counts = Counter(sample["source_path"] for sample in samples)
    mode_counts = Counter(sample["mode"] for sample in samples)
    required_counts = Counter("|".join(sample["derived_required_issuers"]) for sample in samples)
    protected = sum(1 for sample in samples if sample["mode"] in PROTECTED_MODES)
    multiple = sum(1 for sample in samples if len(sample["derived_required_issuers"]) > 1)
    env_required = sum(1 for sample in samples if sample["requires_env"])
    substitutions = sum(1 for sample in samples if sample["has_substitution_attempt"])

    audit_summary = {
        "run_id": run_id,
        "analysis": "natural protected-decision owner-label audit",
        "packet_dir": str(packet_dir),
        "packet_run_id": summary.get("run_id", ""),
        "audit_status": "ok"
        if not failed_rows and not missing_labels and not extra_labels and not failed_global
        else "failed",
        "samples_audited": len(samples),
        "protected_decision_labels": protected,
        "samples_requiring_multiple_issuers": multiple,
        "samples_requiring_env": env_required,
        "samples_with_substitution_attempt": substitutions,
        "source_path_counts": dict(sorted(source_counts.items())),
        "mode_counts": dict(sorted(mode_counts.items())),
        "required_issuer_set_counts": dict(sorted(required_counts.items())),
        "failed_samples": [row["sample_id"] for row in failed_rows],
        "failed_samples_count": len(failed_rows),
        "missing_labels": missing_labels,
        "extra_labels": extra_labels,
        "global_checks": global_checks,
        "failed_global_checks": failed_global,
        "failed_checks_total": sum(int(row["checks_failed"]) for row in report_rows)
        + len(failed_global)
        + len(missing_labels)
        + len(extra_labels),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "not_a_tool_execution": True,
        "limitations": [
            "This audit checks project-author labels for internal consistency.",
            "It is not blinded independent human agreement.",
            "It supports labelability and owner-boundary coverage, not natural prevalence.",
        ],
        "input_digests": _input_digests(
            packet_dir / "sample_manifest.jsonl",
            packet_dir / "author_labels.codex.jsonl",
            packet_dir / "natural_pd_labeling_summary.json",
        ),
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
        "analyzer_sha256": _sha256(Path(__file__).read_bytes()),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "natural_pd_label_audit_report.csv", report_rows, REPORT_FIELDS)
    _write_rows(output_dir / "input_digests.csv", audit_summary["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "natural_pd_label_audit_summary.json").write_text(
        json.dumps(audit_summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": audit_summary, "report_rows": report_rows}


def _audit_sample(sample: dict[str, Any], label: dict[str, Any] | None) -> dict[str, Any]:
    failed: list[str] = []
    passed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed
        if condition:
            passed += 1
        else:
            failed.append(name)

    if label is None:
        return {
            "sample_id": sample["sample_id"],
            "status": "missing_label",
            "checks_passed": 0,
            "checks_failed": 1,
            "failed_checks": "label_exists",
            "mode": sample.get("mode", ""),
            "source_path": sample.get("source_path", ""),
            "required_issuers": "|".join(sample.get("derived_required_issuers", [])),
            "substitution_edges": "|".join(sample.get("substitution_edges", [])),
        }

    required = [issuer for issuer in sample["derived_required_issuers"] if issuer in ISSUER_CLASSES]
    owner_fields = label.get("owner_fields", [])
    owner_by_class = {field.get("owner"): field.get("field") for field in owner_fields}
    unsafe = label.get("unsafe_substitutes", [])
    unsafe_edges = sorted(
        f"{item.get('from')}->{item.get('to')}" for item in unsafe if item.get("from") and item.get("to")
    )

    text = json.dumps(label, sort_keys=True)
    check("sample_id_matches", label.get("sample_id") == sample["sample_id"])
    check("placeholder_free", "TODO" not in text and "TEMPLATE" not in text)
    check("labeler_is_author_first_pass", label.get("labeler") == "codex-author-first-pass")
    check("protected_flag_matches_mode", label.get("is_protected_decision") == (sample["mode"] in PROTECTED_MODES))
    check("decision_class_matches_mode", label.get("decision_class") == (sample["mode"] or sample["decision"]))
    check("required_issuers_match_manifest", label.get("required_issuers_human") == required)
    check("env_requirement_matches_manifest", label.get("needs_env_runtime_proof") == sample["requires_env"])
    check(
        "substitution_attempt_matches_manifest",
        label.get("observed_substitution_attempt") == sample["has_substitution_attempt"],
    )
    check("one_owner_field_per_required_issuer", sorted(owner_by_class) == sorted(required))
    for issuer in required:
        check(
            f"{issuer}_owner_field_matches_protocol",
            owner_by_class.get(issuer) == OWNER_FIELDS[issuer],
        )
    check("unsafe_substitutes_match_edges", unsafe_edges == sorted(sample["substitution_edges"]))
    for item in unsafe:
        target = item.get("to")
        check(
            f"unsafe_target_{target}_field_matches_protocol",
            item.get("field") == OWNER_FIELDS.get(str(target), "unknown"),
        )

    return {
        "sample_id": sample["sample_id"],
        "status": "ok" if not failed else "failed",
        "checks_passed": passed,
        "checks_failed": len(failed),
        "failed_checks": "|".join(failed),
        "mode": sample.get("mode", ""),
        "source_path": sample.get("source_path", ""),
        "required_issuers": "|".join(sample.get("derived_required_issuers", [])),
        "substitution_edges": "|".join(sample.get("substitution_edges", [])),
    }


def _global_checks(
    *,
    packet_dir: Path,
    samples: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    min_samples: int,
    min_protected: int,
    min_multiple: int,
    min_env: int,
    min_substitution: int,
    require_existing_source: bool,
) -> list[dict[str, Any]]:
    protected = sum(1 for sample in samples if sample["mode"] in PROTECTED_MODES)
    multiple = sum(1 for sample in samples if len(sample["derived_required_issuers"]) > 1)
    env_required = sum(1 for sample in samples if sample["requires_env"])
    substitutions = sum(1 for sample in samples if sample["has_substitution_attempt"])
    selected_sources = sorted({Path(sample["source_path"]) for sample in samples})
    source_digest_paths = {
        str(item.get("path"))
        for item in summary.get("input_digests", [])
        if str(item.get("path")) != str(packet_dir / "sample_manifest.jsonl")
    }

    checks = [
        ("sample_count_matches_summary", len(samples) == summary.get("samples")),
        ("label_count_matches_summary", len(labels) == summary.get("author_first_pass_labels")),
        ("protected_count_matches_summary", protected == summary.get("protected_decision_labels")),
        ("multi_count_matches_summary", multiple == summary.get("samples_requiring_multiple_issuers")),
        ("env_count_matches_summary", env_required == summary.get("samples_requiring_env")),
        ("substitution_count_matches_summary", substitutions == summary.get("samples_with_substitution_attempt")),
        ("min_samples", len(samples) >= min_samples),
        ("min_protected", protected >= min_protected),
        ("min_multiple", multiple >= min_multiple),
        ("min_env", env_required >= min_env),
        ("min_substitution", substitutions >= min_substitution),
        ("all_selected_sources_exist", all(path.exists() for path in selected_sources)),
        (
            "selected_sources_have_digests",
            all(str(path) in source_digest_paths for path in selected_sources),
        ),
        (
            "summary_records_no_dataset_sync",
            any("does not sync" in note.lower() for note in summary.get("notes", [])),
        ),
    ]
    if require_existing_source:
        checks.append(("summary_requires_existing_source", summary.get("require_existing_source") is True))
    return [{"name": name, "passed": passed} for name, passed in checks]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _input_digests(*paths: Path) -> list[dict[str, Any]]:
    return [{"path": str(path), "sha256": _sha256(path.read_bytes()), "bytes": path.stat().st_size} for path in paths]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _git_status() -> str:
    try:
        return subprocess.check_output(["git", "status", "--short"], text=True).strip()
    except Exception:
        return "unknown"


def _command_text() -> str:
    return " ".join(["python", *(__import__("sys").argv)])


if __name__ == "__main__":
    raise SystemExit(main())
