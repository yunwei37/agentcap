"""Run a local LLM as a non-evaluation-task-JSON tau2 lease compiler.

The model sees tau2 task JSON after removing ``evaluation_criteria`` and
``annotations``, plus assistant tool schemas. It proposes candidate tool leases,
but reference actions are used only after the fact to score coverage. The
script does not execute tools, run the tau2 simulator, call reward functions,
use APIs, or sync datasets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_tau2_visible_lease_compiler import (  # noqa: E402
    DEFAULT_DOMAINS,
    _assistant_reference_actions,
    _load_json_list,
    _parse_assistant_tools,
    _public_task_text,
)
from run_local_llm_lease_corpus import (  # noqa: E402
    DEFAULT_LLAMA_BIN,
    DEFAULT_MODEL,
    _llama_command,
    _run_llama,
)


TASK_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "prompt_path",
    "raw_output_path",
    "schema_path",
    "parse_ok",
    "returncode",
    "latency_seconds",
    "model_lease_count",
    "valid_lease_count",
    "invalid_tool_count",
    "candidate_tools",
    "reference_actions",
    "tool_covered_reference_actions",
    "tool_and_non_eval_json_arg_reference_actions",
    "tool_only_runtime_or_broad_arg_reference_actions",
    "missing_tool_reference_actions",
    "prompt_sha256",
    "raw_output_sha256",
]
LEASE_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "tool",
    "valid_tool",
    "tool_type",
    "arguments",
    "argument_policy_json",
    "intent_evidence",
]
COVERAGE_FIELDS = [
    "run_id",
    "domain",
    "task_id",
    "action_id",
    "index",
    "tool",
    "args_json",
    "candidate_tool_selected",
    "complete_non_eval_json_arguments",
    "missing_candidate_argument_keys",
    "coverage_class",
    "reward_basis",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run local Qwen/llama.cpp as a tau2 lease compiler over task JSON "
            "with evaluation_criteria and annotations removed"
        )
    )
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R071")
    parser.add_argument("--domains", nargs="*", default=list(DEFAULT_DOMAINS))
    parser.add_argument("--max-tasks-per-domain", type=int, default=5)
    parser.add_argument("--llama-bin", type=Path, default=DEFAULT_LLAMA_BIN)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--n-predict", type=int, default=1024)
    parser.add_argument("--ctx-size", type=int, default=8192)
    parser.add_argument("--gpu-layers", type=int, default=999)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument(
        "--json-schema-constrained",
        action="store_true",
        help=(
            "Write a per-task JSON schema and pass it to llama.cpp with "
            "--json-schema-file. The schema constrains the output shape, tool "
            "names, policy modes, and legal argument keys."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_experiment(
        benchmark_dir=args.benchmark_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
        domains=tuple(args.domains),
        max_tasks_per_domain=args.max_tasks_per_domain,
        llama_bin=args.llama_bin,
        model=args.model,
        n_predict=args.n_predict,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        timeout_seconds=args.timeout_seconds,
        json_schema_constrained=args.json_schema_constrained,
        dry_run=args.dry_run,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def run_experiment(
    *,
    benchmark_dir: Path,
    output_dir: Path,
    run_id: str,
    domains: tuple[str, ...] = DEFAULT_DOMAINS,
    max_tasks_per_domain: int | None = 5,
    llama_bin: Path = DEFAULT_LLAMA_BIN,
    model: Path = DEFAULT_MODEL,
    n_predict: int = 1024,
    ctx_size: int = 8192,
    gpu_layers: int = 999,
    timeout_seconds: int = 180,
    json_schema_constrained: bool = False,
    dry_run: bool = False,
    runner: Callable[[list[str], int], tuple[str, str, int, float]] | None = None,
) -> dict[str, Any]:
    data_root = benchmark_dir / "data" / "tau2" / "domains"
    src_root = benchmark_dir / "src" / "tau2" / "domains"
    domain_names = [
        domain
        for domain in domains
        if (data_root / domain / "tasks.json").exists()
    ]
    tools_by_domain = {
        domain: _parse_assistant_tools(src_root / domain / "tools.py", domain=domain)
        for domain in domain_names
    }
    runner = runner or _run_llama

    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir = output_dir / "prompts"
    raw_dir = output_dir / "raw_outputs"
    schema_dir = output_dir / "schemas"
    prompt_dir.mkdir(exist_ok=True)
    raw_dir.mkdir(exist_ok=True)
    if json_schema_constrained:
        schema_dir.mkdir(exist_ok=True)

    task_rows: list[dict[str, Any]] = []
    lease_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    coverage_counter: Counter[str] = Counter()
    domain_counters: dict[str, Counter[str]] = defaultdict(Counter)

    for domain in domain_names:
        raw_tasks = _load_json_list(data_root / domain / "tasks.json")
        if max_tasks_per_domain is not None:
            raw_tasks = raw_tasks[:max_tasks_per_domain]
        for raw_task in raw_tasks:
            task_id = str(raw_task.get("id", ""))
            prompt = build_prompt(
                domain=domain,
                raw_task=raw_task,
                tools=tools_by_domain[domain],
            )
            safe_task_id = _safe_id(domain, task_id)
            prompt_path = prompt_dir / f"{safe_task_id}.txt"
            raw_path = raw_dir / f"{safe_task_id}.txt"
            schema_path = schema_dir / f"{safe_task_id}.json" if json_schema_constrained else None
            prompt_path.write_text(prompt)
            if schema_path is not None:
                schema_path.write_text(
                    json.dumps(
                        build_output_json_schema(tools_by_domain[domain]),
                        indent=2,
                        sort_keys=True,
                    )
                )
            if dry_run:
                stdout, stderr, returncode, latency = "", "", 0, 0.0
            else:
                command = _llama_command(
                    llama_bin=llama_bin,
                    model=model,
                    prompt_path=prompt_path,
                    n_predict=n_predict,
                    ctx_size=ctx_size,
                    gpu_layers=gpu_layers,
                )
                if schema_path is not None:
                    command.extend(["--json-schema-file", str(schema_path)])
                stdout, stderr, returncode, latency = runner(command, timeout_seconds)
            raw_payload = _raw_payload(stdout, stderr, returncode)
            raw_path.write_text(raw_payload)
            parsed = None if dry_run else parse_model_json(stdout)
            evaluated = evaluate_task(
                run_id=run_id,
                domain=domain,
                task_id=task_id,
                raw_task=raw_task,
                tools=tools_by_domain[domain],
                parsed=parsed,
            )
            task_row = {
                **evaluated["task_row"],
                "prompt_path": str(prompt_path),
                "raw_output_path": str(raw_path),
                "schema_path": str(schema_path) if schema_path is not None else "",
                "parse_ok": parsed is not None,
                "returncode": returncode,
                "latency_seconds": round(latency, 6),
                "prompt_sha256": _sha256(prompt.encode()),
                "raw_output_sha256": _sha256(raw_payload.encode()),
            }
            task_rows.append(task_row)
            lease_rows.extend(evaluated["lease_rows"])
            coverage_rows.extend(evaluated["coverage_rows"])
            records.append(
                {
                    "run_id": run_id,
                    "domain": domain,
                    "task_id": task_id,
                    "prompt_path": str(prompt_path),
                    "raw_output_path": str(raw_path),
                    "schema_path": str(schema_path) if schema_path is not None else "",
                    "parsed_model_json": parsed,
                    "task_row": task_row,
                }
            )
            for row in evaluated["coverage_rows"]:
                coverage_counter[str(row["coverage_class"])] += 1
                domain_counters[domain][str(row["coverage_class"])] += 1
                domain_counters[domain]["reference_actions"] += 1

    summary = summarize(
        run_id=run_id,
        benchmark_dir=benchmark_dir,
        domains=domain_names,
        max_tasks_per_domain=max_tasks_per_domain,
        task_rows=task_rows,
        coverage_counter=coverage_counter,
        domain_counters=domain_counters,
        llama_bin=llama_bin,
        model=model,
        n_predict=n_predict,
        ctx_size=ctx_size,
        gpu_layers=gpu_layers,
        timeout_seconds=timeout_seconds,
        json_schema_constrained=json_schema_constrained,
        dry_run=dry_run,
    )

    (output_dir / "llm_visible_lease_compiler_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    _write_rows(output_dir / "task_results.csv", task_rows, TASK_FIELDS)
    _write_rows(output_dir / "lease_results.csv", lease_rows, LEASE_FIELDS)
    _write_rows(output_dir / "reference_coverage.csv", coverage_rows, COVERAGE_FIELDS)
    with (output_dir / "samples.jsonl").open("w") as file:
        for record in records:
            file.write(json.dumps(record, sort_keys=True) + "\n")
    (output_dir / "command.txt").write_text(_command_text())
    return {
        "summary": summary,
        "task_rows": task_rows,
        "lease_rows": lease_rows,
        "coverage_rows": coverage_rows,
        "records": records,
    }


def build_prompt(*, domain: str, raw_task: dict[str, Any], tools: list[Any]) -> str:
    public_task = {
        key: value
        for key, value in raw_task.items()
        if key not in {"evaluation_criteria", "annotations"}
    }
    payload = {
        "domain": domain,
        "task": public_task,
        "available_tools": [
            {
                "name": tool.name,
                "tool_type": tool.tool_type,
                "arguments": list(tool.arguments),
                "description": tool.docstring,
            }
            for tool in tools
        ],
        "output_schema": {
            "leases": [
                {
                    "tool": "tool_name",
                    "intent_evidence": "short reason from non-evaluation task JSON",
                    "argument_policy": {
                        "arg_name": {
                            "mode": "equals_any | runtime_from_prior_tool | ask_user | unconstrained",
                            "values": ["literal values from the non-evaluation task JSON if mode is equals_any"],
                        }
                    },
                }
            ]
        },
    }
    return (
        "JSON-only tau2 IntentCap lease compiler. /no_think\n"
        "First output character must be { and the last must be }. Do not write "
        "<think>, markdown, prose, explanations, plans, or comments.\n"
        "Synthesize the smallest set of assistant tool-call capability leases "
        "needed for the tau2 task JSON. Use only input.available_tools. "
        "Do not invent tool names or argument keys. Prefer exact task-JSON values "
        "when they appear in the non-evaluation task JSON. If an argument must "
        "come from a prior tool result, mark it runtime_from_prior_tool. If no assistant tool is needed, "
        "return {\"leases\":[]}.\n"
        "Input JSON:\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n"
        "Output JSON only:\n"
    )


def build_output_json_schema(tools: list[Any]) -> dict[str, Any]:
    tool_names = sorted(tool.name for tool in tools)
    argument_names = sorted({arg for tool in tools for arg in tool.arguments})
    value_schema: dict[str, Any] = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "integer"},
            {"type": "boolean"},
            {"type": "null"},
        ]
    }
    policy_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "values"],
        "properties": {
            "mode": {
                "type": "string",
                "enum": [
                    "equals_any",
                    "runtime_from_prior_tool",
                    "ask_user",
                    "unconstrained",
                ],
            },
            "values": {
                "type": "array",
                "items": value_schema,
            },
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["leases"],
        "properties": {
            "leases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["tool", "intent_evidence", "argument_policy"],
                    "properties": {
                        "tool": {
                            "type": "string",
                            "enum": tool_names,
                        },
                        "intent_evidence": {
                            "type": "string",
                        },
                        "argument_policy": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                arg: policy_schema for arg in argument_names
                            },
                        },
                    },
                },
            },
        },
    }


def parse_model_json(text: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "")
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("leases"), list):
            return value
    return None


def evaluate_task(
    *,
    run_id: str,
    domain: str,
    task_id: str,
    raw_task: dict[str, Any],
    tools: list[Any],
    parsed: dict[str, Any] | None,
) -> dict[str, Any]:
    tools_by_name = {tool.name: tool for tool in tools}
    public_text = _public_task_text(raw_task)
    model_leases = parsed.get("leases", []) if parsed else []
    valid_tools: set[str] = set()
    valid_leases_by_tool: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid_tool_count = 0
    lease_rows: list[dict[str, Any]] = []
    for lease in model_leases:
        if not isinstance(lease, dict):
            invalid_tool_count += 1
            continue
        tool_name = str(lease.get("tool", ""))
        tool = tools_by_name.get(tool_name)
        valid = tool is not None
        if valid:
            valid_tools.add(tool_name)
            valid_leases_by_tool[tool_name].append(lease)
        else:
            invalid_tool_count += 1
        argument_policy = lease.get("argument_policy")
        lease_rows.append(
            {
                "run_id": run_id,
                "domain": domain,
                "task_id": task_id,
                "tool": tool_name,
                "valid_tool": valid,
                "tool_type": tool.tool_type if tool else "",
                "arguments": "|".join(tool.arguments) if tool else "",
                "argument_policy_json": json.dumps(argument_policy if isinstance(argument_policy, dict) else {}, sort_keys=True),
                "intent_evidence": str(lease.get("intent_evidence", "")),
            }
        )

    coverage_rows: list[dict[str, Any]] = []
    reference_actions = _assistant_reference_actions(domain, task_id, raw_task)
    tool_covered = 0
    visible_arg_covered = 0
    runtime_or_broad = 0
    missing = 0
    for action in reference_actions:
        selected_leases = valid_leases_by_tool.get(action.name, [])
        selected = bool(selected_leases)
        if not selected:
            coverage_class = "missing_tool"
            missing_candidate_keys = sorted(action.arguments)
            missing += 1
        else:
            missing_candidate_keys = _best_missing_argument_keys(
                selected_leases,
                action.arguments,
            )
        if selected and not missing_candidate_keys:
            coverage_class = "tool_and_non_eval_json_args"
            tool_covered += 1
            visible_arg_covered += 1
        elif selected:
            coverage_class = "tool_only_runtime_or_broad_args_needed"
            tool_covered += 1
            runtime_or_broad += 1
        coverage_rows.append(
            {
                "run_id": run_id,
                "domain": domain,
                "task_id": task_id,
                "action_id": action.action_id,
                "index": action.index,
                "tool": action.name,
                "args_json": json.dumps(action.arguments, sort_keys=True),
                "candidate_tool_selected": selected,
                "complete_non_eval_json_arguments": not missing_candidate_keys,
                "missing_candidate_argument_keys": "|".join(missing_candidate_keys),
                "coverage_class": coverage_class,
                "reward_basis": "|".join(action.reward_basis),
            }
        )

    task_row = {
        "run_id": run_id,
        "domain": domain,
        "task_id": task_id,
        "model_lease_count": len(model_leases),
        "valid_lease_count": len(valid_tools),
        "invalid_tool_count": invalid_tool_count,
        "candidate_tools": "|".join(sorted(valid_tools)),
        "reference_actions": len(reference_actions),
        "tool_covered_reference_actions": tool_covered,
        "tool_and_non_eval_json_arg_reference_actions": visible_arg_covered,
        "tool_only_runtime_or_broad_arg_reference_actions": runtime_or_broad,
        "missing_tool_reference_actions": missing,
    }
    return {
        "task_row": task_row,
        "lease_rows": lease_rows,
        "coverage_rows": coverage_rows,
    }


def _best_missing_argument_keys(
    leases: list[dict[str, Any]],
    arguments: dict[str, Any],
) -> list[str]:
    if not arguments:
        return []
    candidates = [
        _lease_missing_argument_keys(lease, arguments)
        for lease in leases
    ]
    return min(candidates, key=len) if candidates else sorted(arguments)


def _lease_missing_argument_keys(
    lease: dict[str, Any],
    arguments: dict[str, Any],
) -> list[str]:
    policy = lease.get("argument_policy")
    if not isinstance(policy, dict):
        return sorted(arguments)
    return [
        key
        for key, value in sorted(arguments.items())
        if not _argument_policy_covers_reference_value(policy.get(key), value)
    ]


def _argument_policy_covers_reference_value(policy: Any, reference_value: Any) -> bool:
    if not isinstance(policy, dict):
        return False
    if str(policy.get("mode", "")) != "equals_any":
        return False
    values = policy.get("values")
    if not isinstance(values, list):
        return False
    return _policy_values_cover(values, reference_value)


def _policy_values_cover(values: list[Any], reference_value: Any) -> bool:
    if isinstance(reference_value, str):
        return reference_value in {str(value) for value in values}
    if isinstance(reference_value, bool) or reference_value is None:
        return reference_value in values or json.dumps(reference_value) in {
            str(value) for value in values
        }
    if isinstance(reference_value, int | float):
        return reference_value in values or str(reference_value) in {str(value) for value in values}
    return False


def summarize(
    *,
    run_id: str,
    benchmark_dir: Path,
    domains: list[str],
    max_tasks_per_domain: int | None,
    task_rows: list[dict[str, Any]],
    coverage_counter: Counter[str],
    domain_counters: dict[str, Counter[str]],
    llama_bin: Path,
    model: Path,
    n_predict: int,
    ctx_size: int,
    gpu_layers: int,
    timeout_seconds: int,
    json_schema_constrained: bool,
    dry_run: bool,
) -> dict[str, Any]:
    reference_actions = sum(int(row["reference_actions"]) for row in task_rows)
    tool_covered = (
        coverage_counter["tool_and_non_eval_json_args"]
        + coverage_counter["tool_only_runtime_or_broad_args_needed"]
    )
    return {
        "run_id": run_id,
        "benchmark": "tau2-bench",
        "benchmark_dir": str(benchmark_dir),
        "domains": domains,
        "max_tasks_per_domain": max_tasks_per_domain,
        "tasks_evaluated": len(task_rows),
        "tasks_with_assistant_reference_actions": sum(
            1 for row in task_rows if int(row["reference_actions"]) > 0
        ),
        "assistant_reference_actions": reference_actions,
        "parse_ok_tasks": sum(1 for row in task_rows if row["parse_ok"]),
        "returncode_nonzero_tasks": sum(1 for row in task_rows if int(row["returncode"]) != 0),
        "candidate_tool_slots_total": sum(
            len(str(row["candidate_tools"]).split("|")) if row["candidate_tools"] else 0
            for row in task_rows
        ),
        "model_lease_slots_total": sum(int(row["model_lease_count"]) for row in task_rows),
        "invalid_tool_slots_total": sum(int(row["invalid_tool_count"]) for row in task_rows),
        "tool_coverage_rate": tool_covered / reference_actions if reference_actions else 1.0,
        "non_eval_json_argument_coverage_rate": (
            coverage_counter["tool_and_non_eval_json_args"] / reference_actions
            if reference_actions
            else 1.0
        ),
        "coverage_class_counts": dict(sorted(coverage_counter.items())),
        "domain_counts": {
            domain: dict(sorted(counter.items()))
            for domain, counter in sorted(domain_counters.items())
        },
        "mean_latency_seconds": _mean_float([float(row["latency_seconds"]) for row in task_rows]),
        "llama_bin": str(llama_bin),
        "model": str(model),
        "model_sha256": _file_digest(model),
        "n_predict": n_predict,
        "ctx_size": ctx_size,
        "gpu_layers": gpu_layers,
        "timeout_seconds": timeout_seconds,
        "json_schema_constrained": json_schema_constrained,
        "dry_run": dry_run,
        "machine": platform.platform(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "notes": [
            "The local LLM sees non-evaluation task JSON after removing evaluation_criteria and annotations, plus assistant tool schemas; evaluation_criteria.actions are post-hoc scoring labels.",
            "Generated leases are not trusted authority and no tau2 tools are executed in this run.",
            "tool_and_non_eval_json_args requires the generated argument_policy to cover all reference arguments with equals_any values from the non-evaluation task JSON.",
            "tool_only_runtime_or_broad_args_needed indicates that a selected tool still needs runtime state, user response, or a broader argument placeholder.",
            "This corpus is a lease-compiler frontend probe, not an end-to-end tau2 utility or reward run.",
            "json_schema_constrained uses llama.cpp --json-schema-file to constrain output shape/tool names/argument keys, but deterministic post-hoc scoring still decides coverage.",
        ],
    }


def _raw_payload(stdout: str, stderr: str, returncode: int) -> str:
    return json.dumps(
        {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
        },
        indent=2,
        sort_keys=True,
    )


def _write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _safe_id(domain: str, task_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_id).strip("_") or "task"
    return f"{domain}_{safe}"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mean_float(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _git_output(args: list[str]) -> str:
    completed = subprocess.run(
        args,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.stdout.strip()


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
