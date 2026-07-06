"""Build scorer-ready policy rows for expert-oracle distance analysis.

This E2 utility converts saved authority-exposure artifacts into the flattened
policy-row schema consumed by ``score_expert_oracle_policy_distance.py``. It
does not create expert labels, run models, execute benchmark tools, clone
repositories, sync datasets, or download data.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("results/eval/R199/expert_oracle_task_manifest.csv")
DEFAULT_INJECAGENT_CASE_EXPOSURE = Path("results/injecagent/R019/case_exposure.csv")
DEFAULT_MCPTOX_EVENT_EXPOSURE = Path("results/mcptox/R020/event_exposure.csv")
DEFAULT_TAU2_TASK_EXPOSURE = Path("results/tau2/R022/task_exposure.csv")

POLICY_FIELDS = [
    "sample_id",
    "benchmark",
    "workload_family",
    "task_or_event_id",
    "domain_or_server",
    "protected_decision_focus",
    "policy",
    "source_baseline",
    "source_artifact",
    "source_row_id",
    "policy_row_kind",
    "lease_operations",
    "lease_objects",
    "lease_allowed_sinks",
    "influence_modes",
    "decision_classes",
    "budget_invocations_total",
    "lease_argument_constraints_json",
    "exposure_count",
    "coverage_rate",
    "notes",
]

COUNT_FIELDS = [
    "benchmark",
    "workload_family",
    "policy",
    "rows",
]

INPUT_DIGEST_FIELDS = ["path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build expert-oracle policy rows")
    parser.add_argument("--run-id", default="R201P")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--injecagent-case-exposure", type=Path, default=DEFAULT_INJECAGENT_CASE_EXPOSURE)
    parser.add_argument("--mcptox-event-exposure", type=Path, default=DEFAULT_MCPTOX_EVENT_EXPOSURE)
    parser.add_argument("--tau2-task-exposure", type=Path, default=DEFAULT_TAU2_TASK_EXPOSURE)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = build_policy_rows(
        run_id=args.run_id,
        manifest_path=args.manifest,
        injecagent_case_exposure=args.injecagent_case_exposure,
        mcptox_event_exposure=args.mcptox_event_exposure,
        tau2_task_exposure=args.tau2_task_exposure,
    )
    write_outputs(args.output_dir, result)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["row_status"] == "ok" else 1


def build_policy_rows(
    *,
    run_id: str,
    manifest_path: Path = DEFAULT_MANIFEST,
    injecagent_case_exposure: Path = DEFAULT_INJECAGENT_CASE_EXPOSURE,
    mcptox_event_exposure: Path = DEFAULT_MCPTOX_EVENT_EXPOSURE,
    tau2_task_exposure: Path = DEFAULT_TAU2_TASK_EXPOSURE,
) -> dict[str, Any]:
    manifest_rows = _read_csv(manifest_path)
    injecagent_rows = _read_csv(injecagent_case_exposure)
    mcptox_rows = _read_csv(mcptox_event_exposure)
    tau2_rows = _read_csv(tau2_task_exposure)

    injecagent_by_case = _group_by(injecagent_rows, "case_id")
    mcptox_by_event = _group_by(mcptox_rows, "event_id")
    tau2_by_task = _group_tau2_by_task(tau2_rows)

    policy_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, str]] = []
    for manifest in manifest_rows:
        benchmark = manifest.get("benchmark", "")
        if benchmark == "InjecAgent":
            matches = injecagent_by_case.get(manifest.get("task_or_event_id", ""), [])
            policy_rows.extend(_injecagent_policy_row(manifest, row) for row in matches)
        elif benchmark == "MCPTox":
            matches = mcptox_by_event.get(manifest.get("task_or_event_id", ""), [])
            policy_rows.extend(_mcptox_policy_row(manifest, row) for row in matches)
        elif benchmark == "tau2-bench / tau3-bench":
            key = (manifest.get("domain_or_server", ""), manifest.get("task_or_event_id", ""))
            matches = tau2_by_task.get(key, [])
            policy_rows.extend(_tau2_policy_row(manifest, row) for row in matches)
        else:
            matches = []

        if not matches:
            missing_rows.append(
                {
                    "sample_id": manifest.get("sample_id", ""),
                    "benchmark": benchmark,
                    "task_or_event_id": manifest.get("task_or_event_id", ""),
                }
            )

    input_paths = [
        manifest_path,
        injecagent_case_exposure,
        mcptox_event_exposure,
        tau2_task_exposure,
    ]
    summary = _summary(run_id, manifest_rows, policy_rows, missing_rows, input_paths)
    return {
        "summary": summary,
        "policy_rows": policy_rows,
        "policy_counts": _policy_count_rows(policy_rows),
        "input_digests": [_file_digest(path) for path in input_paths],
    }


def write_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(output_dir / "expert_oracle_policy_rows.csv", result["policy_rows"], POLICY_FIELDS)
    _write_rows(output_dir / "expert_oracle_policy_row_counts.csv", result["policy_counts"], COUNT_FIELDS)
    _write_rows(output_dir / "input_digests.csv", result["input_digests"], INPUT_DIGEST_FIELDS)
    (output_dir / "expert_oracle_policy_rows_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(_command_text())


def _injecagent_policy_row(manifest: dict[str, str], exposure: dict[str, str]) -> dict[str, Any]:
    baseline = exposure.get("baseline", "")
    exact_object = manifest.get("primary_tool_or_object", "")
    domain = manifest.get("domain_or_server", "")
    object_scopes = {
        "intentcap_one_shot": [],
        "task_tool_allowlist": [],
        "toolkit_allowlist": [f"toolkit:{domain}:*"],
        "benchmark_user_tools": ["benchmark:user_tools:*"],
        "observed_trace_tools": ["observed_trace:*"],
        "catalog_all_tools": ["catalog:*"],
    }
    return _base_policy_row(
        manifest,
        exposure,
        source_artifact=str(DEFAULT_INJECAGENT_CASE_EXPOSURE),
        exact_object=exact_object,
        object_scopes=object_scopes.get(baseline, [f"unknown_scope:{baseline}"]),
        operation="tool.call",
        budget=_int(exposure.get("exposed_tools"), default=1),
        exposure_count=exposure.get("exposed_tools", ""),
        coverage_rate="",
        argument_profile={
            "mode": "exact_event_provenance"
            if baseline == "intentcap_one_shot"
            else "tool_acl_broad_arguments",
            "control_provenance_checked": baseline == "intentcap_one_shot",
            "argument_values_constrained": baseline == "intentcap_one_shot",
            "case_id": exposure.get("case_id", ""),
            "user_tool": exposure.get("user_tool", exact_object),
            "user_toolkit": exposure.get("user_toolkit", domain),
            "source_baseline": baseline,
        },
        trusted_policy=baseline == "intentcap_one_shot",
        sink_scopes=_sink_scopes(manifest, baseline),
        notes="InjecAgent case-level exposure row normalized for scorer input.",
    )


def _mcptox_policy_row(manifest: dict[str, str], exposure: dict[str, str]) -> dict[str, Any]:
    baseline = exposure.get("baseline", "")
    exact_object = manifest.get("primary_tool_or_object", "")
    server = manifest.get("domain_or_server", "")
    object_scopes = {
        "intentcap_provenance": [],
        "exact_tool_acl": [],
        "authentic_server_allowlist": [f"mcp-server:{server}:authentic:*"],
        "observed_server_allowlist": [f"mcp-server:{server}:observed:*"],
        "global_authentic_tools": ["mcp-authentic-tools:*"],
        "global_observed_tools": ["mcp-observed-tools:*"],
    }
    return _base_policy_row(
        manifest,
        exposure,
        source_artifact=str(DEFAULT_MCPTOX_EVENT_EXPOSURE),
        exact_object=exact_object,
        object_scopes=object_scopes.get(baseline, [f"unknown_scope:{baseline}"]),
        operation="mcp.call",
        budget=_int(exposure.get("exposed_tools"), default=1),
        exposure_count=exposure.get("exposed_tools", ""),
        coverage_rate="",
        argument_profile={
            "mode": "exact_event_provenance"
            if baseline == "intentcap_provenance"
            else "mcp_object_acl",
            "control_provenance_checked": baseline == "intentcap_provenance",
            "argument_event_id_checked": baseline == "intentcap_provenance",
            "argument_values_constrained": baseline == "intentcap_provenance",
            "event_id": exposure.get("event_id", ""),
            "server": exposure.get("server", server),
            "object": exposure.get("object", exact_object),
            "source_baseline": baseline,
        },
        trusted_policy=baseline == "intentcap_provenance",
        sink_scopes=_sink_scopes(manifest, baseline),
        notes="MCPTox event-level exposure row normalized for scorer input.",
    )


def _tau2_policy_row(manifest: dict[str, str], exposure: dict[str, str]) -> dict[str, Any]:
    baseline = exposure.get("baseline", "")
    domain = exposure.get("domain") or manifest.get("domain_or_server", "")
    task_id = exposure.get("task_id") or manifest.get("task_or_event_id", "")
    exact_object = f"tau2:{domain}:{task_id}:assistant_reference_actions"
    object_scopes = {
        "intentcap_reference_events": [],
        "task_reference_tools": [f"tau2:{domain}:{task_id}:reference_tools"],
        "domain_assistant_regular": [f"tau2:{domain}:assistant_regular:*"],
        "domain_assistant_all": [f"tau2:{domain}:assistant_all:*"],
        "global_assistant_regular": ["tau2:global:assistant_regular:*"],
        "global_all_tools": ["tau2:global:*"],
    }
    assistant_actions = _int(exposure.get("assistant_reference_actions"), default=1)
    exposed_tools = _int(exposure.get("exposed_tools"), default=1)
    budget = assistant_actions if baseline == "intentcap_reference_events" else max(assistant_actions, exposed_tools)
    return _base_policy_row(
        manifest,
        exposure,
        source_artifact=str(DEFAULT_TAU2_TASK_EXPOSURE),
        exact_object=exact_object,
        object_scopes=object_scopes.get(baseline, [f"unknown_scope:{baseline}"]),
        operation="tool.call",
        budget=budget,
        exposure_count=exposure.get("exposed_tools", ""),
        coverage_rate=exposure.get("coverage_rate", ""),
        argument_profile={
            "mode": "exact_reference_event_provenance"
            if baseline == "intentcap_reference_events"
            else "task_or_domain_acl",
            "control_provenance_checked": baseline == "intentcap_reference_events",
            "event_id_checked": baseline == "intentcap_reference_events",
            "argument_values_constrained": baseline
            in {"intentcap_reference_events", "task_reference_tools"},
            "domain": domain,
            "task_id": task_id,
            "assistant_reference_actions": assistant_actions,
            "assistant_reference_tools": _int(exposure.get("assistant_reference_tools")),
            "source_baseline": baseline,
        },
        trusted_policy=baseline == "intentcap_reference_events",
        sink_scopes=_tau2_sink_scopes(domain, baseline, exposure),
        notes=(
            "tau2/tau3 task-level exposure proxy; object names use a stable "
            "tau2 namespace because R022 stores counts rather than every tool object."
        ),
    )


def _base_policy_row(
    manifest: dict[str, str],
    exposure: dict[str, str],
    *,
    source_artifact: str,
    exact_object: str,
    object_scopes: list[str],
    operation: str,
    budget: int,
    exposure_count: str,
    coverage_rate: str,
    argument_profile: dict[str, Any],
    trusted_policy: bool,
    sink_scopes: list[str],
    notes: str,
) -> dict[str, Any]:
    baseline = exposure.get("baseline", "")
    focus = _decision_classes(manifest.get("protected_decision_focus", ""))
    extra_decisions = [] if trusted_policy else ["approval_scope", "delegation", "policy_update"]
    modes = {"authorize", "parameterize"}
    if not trusted_policy:
        modes.add("plan")
    if object_scopes and not trusted_policy:
        modes.add("delegate")

    return {
        "sample_id": manifest.get("sample_id", ""),
        "benchmark": manifest.get("benchmark", ""),
        "workload_family": manifest.get("workload_family", ""),
        "task_or_event_id": manifest.get("task_or_event_id", ""),
        "domain_or_server": manifest.get("domain_or_server", ""),
        "protected_decision_focus": manifest.get("protected_decision_focus", ""),
        "policy": baseline,
        "source_baseline": baseline,
        "source_artifact": source_artifact,
        "source_row_id": _source_row_id(manifest, exposure),
        "policy_row_kind": "intentcap_candidate" if trusted_policy else "baseline_exposure_proxy",
        "lease_operations": operation,
        "lease_objects": _join([exact_object, *object_scopes]),
        "lease_allowed_sinks": _join(sink_scopes),
        "influence_modes": _join(modes),
        "decision_classes": _join([*focus, "tool_arguments", *extra_decisions]),
        "budget_invocations_total": max(0, budget),
        "lease_argument_constraints_json": _stable_json([argument_profile]),
        "exposure_count": exposure_count,
        "coverage_rate": coverage_rate,
        "notes": notes,
    }


def _decision_classes(value: str) -> list[str]:
    text = value.replace("/", "|").replace(",", "|")
    return [item.strip() for item in text.split("|") if item.strip()]


def _sink_scopes(manifest: dict[str, str], baseline: str) -> list[str]:
    focus = manifest.get("protected_decision_focus", "")
    if "sink_select" not in focus:
        return []
    domain = manifest.get("domain_or_server", "")
    exact = f"sink://trusted/{domain or 'task'}"
    if baseline in {"intentcap_one_shot", "intentcap_provenance"}:
        return [exact]
    if baseline in {"toolkit_allowlist", "authentic_server_allowlist", "observed_server_allowlist"}:
        return [exact, f"sink://{domain}:*"]
    return [exact, "sink://*"]


def _tau2_sink_scopes(domain: str, baseline: str, exposure: dict[str, str]) -> list[str]:
    if _int(exposure.get("write_tool_slots")) <= 0:
        return []
    exact = f"tau2://{domain}/task-state"
    if baseline == "intentcap_reference_events":
        return [exact]
    if baseline in {"task_reference_tools", "domain_assistant_regular", "domain_assistant_all"}:
        return [exact, f"tau2://{domain}/*"]
    return [exact, "tau2://*"]


def _source_row_id(manifest: dict[str, str], exposure: dict[str, str]) -> str:
    if exposure.get("case_id"):
        return exposure["case_id"]
    if exposure.get("event_id"):
        return exposure["event_id"]
    if exposure.get("domain") or exposure.get("task_id"):
        return f"{exposure.get('domain', '')}; {exposure.get('task_id', '')}"
    return manifest.get("source_row_id", "")


def _summary(
    run_id: str,
    manifest_rows: list[dict[str, str]],
    policy_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, str]],
    input_paths: list[Path],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "analysis": "expert-oracle policy-row normalization",
        "manifest_samples": len(manifest_rows),
        "policy_rows": len(policy_rows),
        "missing_policy_samples": missing_rows,
        "missing_policy_samples_count": len(missing_rows),
        "row_status": "ok" if not missing_rows else "incomplete",
        "rows_by_benchmark": dict(sorted(Counter(row["benchmark"] for row in policy_rows).items())),
        "rows_by_policy": dict(sorted(Counter(row["policy"] for row in policy_rows).items())),
        "rows_by_kind": dict(sorted(Counter(row["policy_row_kind"] for row in policy_rows).items())),
        "no_dataset_sync": True,
        "machine": platform.platform(),
        "project_head": _git_head(),
        "git_status": _git_status(),
        "input_digests": [_file_digest(path) for path in input_paths],
        "notes": [
            "Rows are normalized policy candidates and baseline exposure proxies, not expert labels.",
            "Use with score_expert_oracle_policy_distance.py only after adjudicated expert oracle rows exist.",
            "The script reads saved R199/R019/R020/R022 local CSV artifacts only.",
        ],
    }


def _policy_count_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        key = (str(row["benchmark"]), str(row["workload_family"]), str(row["policy"]))
        grouped[key] += 1
    return [
        {
            "benchmark": benchmark,
            "workload_family": family,
            "policy": policy,
            "rows": count,
        }
        for (benchmark, family, policy), count in sorted(grouped.items())
    ]


def _group_by(rows: list[dict[str, str]], field: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get(field, "")].append(row)
    return grouped


def _group_tau2_by_task(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("domain", ""), row.get("task_id", ""))].append(row)
    return grouped


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


def _join(values: list[str] | set[str]) -> str:
    return "|".join(sorted({str(value) for value in values if str(value)}))


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


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
