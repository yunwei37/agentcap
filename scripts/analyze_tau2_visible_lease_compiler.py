"""Analyze a non-evaluation-task-JSON tau2 lease compiler probe.

This script is a non-oracle complement to the earlier tau2 exact-reference
lease experiments. It synthesizes candidate task leases from only:

* non-evaluation task JSON, excluding ``evaluation_criteria`` and ``annotations``;
* the assistant tool catalog parsed from local tau2 domain source files.

Benchmark reference actions are used only after synthesis, as an offline oracle
for coverage and residual-risk accounting. The script does not run a model,
simulator, reward function, API call, or dataset sync.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_tau2_bench import _load_json_list  # noqa: E402


DEFAULT_DOMAINS = ("airline", "retail", "telecom")
STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "call",
    "can",
    "case",
    "details",
    "do",
    "for",
    "from",
    "get",
    "has",
    "have",
    "i",
    "id",
    "if",
    "in",
    "info",
    "is",
    "it",
    "me",
    "need",
    "not",
    "of",
    "on",
    "or",
    "please",
    "proceed",
    "she",
    "that",
    "the",
    "this",
    "to",
    "tool",
    "user",
    "want",
    "with",
    "you",
}
WRITE_INTENT_TOKENS = {
    "add",
    "book",
    "cancel",
    "change",
    "disable",
    "enable",
    "exchange",
    "modify",
    "order",
    "refund",
    "remove",
    "replace",
    "reset",
    "return",
    "send",
    "transfer",
    "update",
}
TOOL_RISK = {
    "read": 1,
    "generic": 2,
    "think": 2,
    "write": 3,
    "unknown": 2,
}


@dataclass(frozen=True)
class ToolSpec:
    domain: str
    name: str
    tool_type: str
    discoverable: bool
    arguments: tuple[str, ...]
    docstring: str
    source_file: str

    @property
    def tool_id(self) -> str:
        return f"{self.domain}:assistant:{self.name}"


@dataclass(frozen=True)
class CandidateLease:
    domain: str
    task_id: str
    tool: ToolSpec
    evidence: tuple[str, ...]
    visible_arg_values: dict[str, tuple[str, ...]]

    @property
    def broad_argument_keys(self) -> tuple[str, ...]:
        return tuple(arg for arg in self.tool.arguments if not self.visible_arg_values.get(arg))


@dataclass(frozen=True)
class ReferenceAction:
    domain: str
    task_id: str
    action_id: str
    index: int
    name: str
    arguments: dict[str, Any]
    reward_basis: tuple[str, ...]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze tau2 lease compiler coverage from task JSON after removing "
            "evaluation_criteria and annotations"
        )
    )
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R070")
    parser.add_argument("--domains", nargs="*", default=list(DEFAULT_DOMAINS))
    parser.add_argument("--max-tasks-per-domain", type=int, default=5)
    args = parser.parse_args()

    result = analyze(
        benchmark_dir=args.benchmark_dir,
        run_id=args.run_id,
        domains=tuple(args.domains),
        max_tasks_per_domain=args.max_tasks_per_domain,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "visible_lease_compiler_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True)
    )
    _write_rows(args.output_dir / "candidate_leases.csv", result["candidate_leases"])
    _write_rows(args.output_dir / "reference_coverage.csv", result["reference_coverage"])
    _write_rows(args.output_dir / "task_summary.csv", result["task_summary"])
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def analyze(
    *,
    benchmark_dir: Path,
    run_id: str,
    domains: tuple[str, ...] = DEFAULT_DOMAINS,
    max_tasks_per_domain: int | None = 5,
) -> dict[str, Any]:
    data_root = benchmark_dir / "data" / "tau2" / "domains"
    src_root = benchmark_dir / "src" / "tau2" / "domains"
    domain_names = [
        domain
        for domain in domains
        if (data_root / domain / "tasks.json").exists()
    ]
    tool_catalog = {
        (tool.domain, tool.name): tool
        for domain in domain_names
        for tool in _parse_assistant_tools(src_root / domain / "tools.py", domain=domain)
    }

    task_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    coverage_counter: Counter[str] = Counter()
    domain_counters: dict[str, Counter[str]] = defaultdict(Counter)
    candidate_counts: list[int] = []
    extra_counts: list[int] = []
    risk_scores: list[int] = []
    broad_arg_counts: list[int] = []
    tasks_with_full_tool_coverage = 0
    tasks_with_full_non_eval_arg_coverage = 0
    tasks_with_refs = 0
    total_reference_actions = 0
    total_reference_tool_slots = 0

    for domain in domain_names:
        raw_tasks = _load_json_list(data_root / domain / "tasks.json")
        if max_tasks_per_domain is not None:
            raw_tasks = raw_tasks[:max_tasks_per_domain]
        domain_tools = [
            tool for (tool_domain, _name), tool in sorted(tool_catalog.items())
            if tool_domain == domain
        ]
        for raw_task in raw_tasks:
            task_id = str(raw_task.get("id", ""))
            public_text = _public_task_text(raw_task)
            visible_tokens = _tokens(public_text)
            visible_values = _visible_values_by_arg(public_text)
            candidates = synthesize_candidate_leases(
                domain=domain,
                task_id=task_id,
                tools=domain_tools,
                public_text=public_text,
                visible_tokens=visible_tokens,
                visible_values=visible_values,
            )
            candidate_by_name = {candidate.tool.name: candidate for candidate in candidates}
            reference_actions = _assistant_reference_actions(domain, task_id, raw_task)
            reference_tool_names = {action.name for action in reference_actions}
            selected_names = {candidate.tool.name for candidate in candidates}
            extra_tools = selected_names - reference_tool_names
            task_risk = sum(_candidate_risk(candidate) for candidate in candidates)
            task_broad_args = sum(len(candidate.broad_argument_keys) for candidate in candidates)
            tool_covered = 0
            non_eval_arg_covered = 0
            runtime_or_broad = 0
            missing = 0

            for candidate in candidates:
                candidate_rows.append(
                    {
                        "run_id": run_id,
                        "domain": domain,
                        "task_id": task_id,
                        "tool": candidate.tool.name,
                        "tool_type": candidate.tool.tool_type,
                        "discoverable": candidate.tool.discoverable,
                        "arguments": "|".join(candidate.tool.arguments),
                        "non_eval_arg_values_json": json.dumps(
                            {
                                key: list(values)
                                for key, values in sorted(candidate.visible_arg_values.items())
                                if values
                            },
                            sort_keys=True,
                        ),
                        "broad_argument_keys": "|".join(candidate.broad_argument_keys),
                        "evidence": "|".join(candidate.evidence),
                        "candidate_risk": _candidate_risk(candidate),
                    }
                )

            for action in reference_actions:
                total_reference_actions += 1
                domain_counters[domain]["reference_actions"] += 1
                candidate = candidate_by_name.get(action.name)
                if candidate is None:
                    coverage_class = "missing_tool"
                    missing += 1
                    domain_counters[domain]["missing_tool"] += 1
                    missing_candidate_keys = sorted(action.arguments)
                else:
                    missing_candidate_keys = _candidate_missing_argument_keys(
                        candidate,
                        action.arguments,
                    )
                    if not missing_candidate_keys:
                        coverage_class = "tool_and_non_eval_json_args"
                        tool_covered += 1
                        non_eval_arg_covered += 1
                        domain_counters[domain]["tool_covered"] += 1
                        domain_counters[domain]["tool_and_non_eval_json_args"] += 1
                    else:
                        coverage_class = "tool_only_runtime_or_broad_args_needed"
                        tool_covered += 1
                        runtime_or_broad += 1
                        domain_counters[domain]["tool_covered"] += 1
                        domain_counters[domain]["tool_only_runtime_or_broad_args_needed"] += 1
                coverage_counter[coverage_class] += 1
                coverage_rows.append(
                    {
                        "run_id": run_id,
                        "domain": domain,
                        "task_id": task_id,
                        "action_id": action.action_id,
                        "index": action.index,
                        "tool": action.name,
                        "args_json": json.dumps(action.arguments, sort_keys=True),
                        "candidate_tool_selected": candidate is not None,
                        "complete_non_eval_json_arguments": not missing_candidate_keys,
                        "missing_candidate_argument_keys": "|".join(missing_candidate_keys),
                        "coverage_class": coverage_class,
                        "reward_basis": "|".join(action.reward_basis),
                    }
                )

            if reference_actions:
                tasks_with_refs += 1
            if reference_actions and tool_covered == len(reference_actions):
                tasks_with_full_tool_coverage += 1
            if reference_actions and non_eval_arg_covered == len(reference_actions):
                tasks_with_full_non_eval_arg_coverage += 1

            candidate_counts.append(len(candidates))
            extra_counts.append(len(extra_tools))
            risk_scores.append(task_risk)
            broad_arg_counts.append(task_broad_args)
            total_reference_tool_slots += len(reference_tool_names)
            task_rows.append(
                {
                    "run_id": run_id,
                    "domain": domain,
                    "task_id": task_id,
                    "public_text_sha256": hashlib.sha256(public_text.encode()).hexdigest(),
                    "candidate_tools": len(candidates),
                    "candidate_tool_names": "|".join(sorted(selected_names)),
                    "reference_actions": len(reference_actions),
                    "reference_tools": len(reference_tool_names),
                    "reference_tool_names": "|".join(sorted(reference_tool_names)),
                    "tool_covered_reference_actions": tool_covered,
                    "tool_and_non_eval_json_arg_reference_actions": non_eval_arg_covered,
                    "tool_only_runtime_or_broad_arg_reference_actions": runtime_or_broad,
                    "missing_tool_reference_actions": missing,
                    "extra_tools": len(extra_tools),
                    "extra_tool_names": "|".join(sorted(extra_tools)),
                    "broad_argument_keys": task_broad_args,
                    "candidate_risk": task_risk,
                }
            )

    summary = {
        "run_id": run_id,
        "benchmark": "tau2-bench",
        "benchmark_dir": str(benchmark_dir),
        "domains": domain_names,
        "max_tasks_per_domain": max_tasks_per_domain,
        "tasks_evaluated": len(task_rows),
        "tasks_with_assistant_reference_actions": tasks_with_refs,
        "assistant_reference_actions": total_reference_actions,
        "reference_tool_slots_total": total_reference_tool_slots,
        "candidate_tool_slots_total": sum(candidate_counts),
        "extra_tool_slots_total": sum(extra_counts),
        "mean_candidate_tools_per_task": _mean(candidate_counts),
        "mean_extra_tools_per_task": _mean(extra_counts),
        "mean_candidate_risk_per_task": _mean(risk_scores),
        "mean_broad_argument_keys_per_task": _mean(broad_arg_counts),
        "tasks_with_full_tool_coverage": tasks_with_full_tool_coverage,
        "tasks_with_full_non_eval_json_arg_coverage": tasks_with_full_non_eval_arg_coverage,
        "coverage_class_counts": dict(sorted(coverage_counter.items())),
        "tool_coverage_rate": (
            (
                coverage_counter["tool_and_non_eval_json_args"]
                + coverage_counter["tool_only_runtime_or_broad_args_needed"]
            )
            / total_reference_actions
            if total_reference_actions
            else 1.0
        ),
        "non_eval_json_argument_coverage_rate": (
            coverage_counter["tool_and_non_eval_json_args"] / total_reference_actions
            if total_reference_actions
            else 1.0
        ),
        "domain_counts": {
            domain: dict(sorted(counter.items()))
            for domain, counter in sorted(domain_counters.items())
        },
        "input_boundary": [
            "non-evaluation task JSON after removing evaluation_criteria and annotations",
            "assistant tool names, argument names, tool types, and docstrings parsed from local tau2 source",
        ],
        "notes": [
            "This is a first non-evaluation-task-JSON lease compiler probe; it does not run the model, simulator, reward, or recovery loop.",
            "Reference actions are used only after synthesis to score coverage and overexposure.",
            "tool_and_non_eval_json_args means the candidate lease constrains all reference arguments using values extracted from the non-evaluation task JSON.",
            "tool_only_runtime_or_broad_args_needed means the tool was selected, but at least one reference argument would require runtime state, a fresh user answer, or a broader placeholder lease.",
            "missing_tool means this simple deterministic compiler did not select the reference tool from non-evaluation task JSON and tool schema evidence.",
        ],
    }
    return {
        "summary": summary,
        "candidate_leases": candidate_rows,
        "reference_coverage": coverage_rows,
        "task_summary": task_rows,
    }


def synthesize_candidate_leases(
    *,
    domain: str,
    task_id: str,
    tools: list[ToolSpec],
    public_text: str,
    visible_tokens: set[str],
    visible_values: dict[str, tuple[str, ...]],
) -> list[CandidateLease]:
    candidates: list[CandidateLease] = []
    for tool in tools:
        evidence = _tool_evidence(tool, public_text, visible_tokens, visible_values)
        if not evidence:
            continue
        values_for_args = {
            arg: visible_values.get(arg, ())
            for arg in tool.arguments
        }
        candidates.append(
            CandidateLease(
                domain=domain,
                task_id=task_id,
                tool=tool,
                evidence=tuple(sorted(evidence)),
                visible_arg_values=values_for_args,
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.tool.name)


def _tool_evidence(
    tool: ToolSpec,
    public_text: str,
    visible_tokens: set[str],
    visible_values: dict[str, tuple[str, ...]],
) -> set[str]:
    lower_text = public_text.lower()
    evidence: set[str] = set()
    normalized_tool_name = tool.name.replace("_", " ").lower()
    if tool.name.lower() in lower_text or normalized_tool_name in lower_text:
        evidence.add("explicit_tool_name")

    grounded_args = [
        arg for arg in tool.arguments
        if visible_values.get(arg)
    ]
    for arg in grounded_args:
        evidence.add(f"visible_arg:{arg}")

    tool_tokens = _tool_tokens(tool)
    overlap = sorted((tool_tokens & visible_tokens) - STOPWORDS)
    if len(overlap) >= 2:
        evidence.add(f"schema_token_overlap:{','.join(overlap[:5])}")
    elif len(overlap) == 1 and grounded_args:
        evidence.add(f"schema_token_overlap:{overlap[0]}")

    if tool.tool_type == "write":
        write_overlap = sorted((tool_tokens & visible_tokens & WRITE_INTENT_TOKENS) - STOPWORDS)
        if write_overlap:
            evidence.add(f"write_intent:{','.join(write_overlap[:5])}")

    if tool.tool_type == "read" and grounded_args:
        evidence.add("read_for_grounded_identifier")

    return evidence


def _parse_assistant_tools(path: Path, *, domain: str) -> list[ToolSpec]:
    if not path.exists():
        return []
    tree = ast.parse(path.read_text())
    tools: list[ToolSpec] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        marker = _tool_marker(node)
        if marker is None:
            continue
        decorator, tool_type = marker
        tools.append(
            ToolSpec(
                domain=domain,
                name=node.name,
                tool_type=tool_type,
                discoverable=decorator == "is_discoverable_tool",
                arguments=tuple(arg.arg for arg in node.args.args if arg.arg != "self"),
                docstring=ast.get_docstring(node) or "",
                source_file=str(path),
            )
        )
    return sorted(tools, key=lambda tool: tool.name)


def _tool_marker(node: ast.FunctionDef) -> tuple[str, str] | None:
    for decorator in node.decorator_list:
        name, args, kwargs = _decorator_name_args_and_kwargs(decorator)
        if name not in {"is_tool", "is_discoverable_tool"}:
            continue
        return name, _tool_type_from_args(args, kwargs)
    return None


def _decorator_name_args_and_kwargs(decorator: ast.AST) -> tuple[str, list[ast.AST], dict[str, ast.AST]]:
    if isinstance(decorator, ast.Name):
        return decorator.id, [], {}
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name):
            kwargs = {
                str(keyword.arg): keyword.value
                for keyword in decorator.keywords
                if keyword.arg is not None
            }
            return func.id, list(decorator.args), kwargs
    return "", [], {}


def _tool_type_from_args(args: list[ast.AST], kwargs: dict[str, ast.AST]) -> str:
    tool_type_node = kwargs.get("tool_type")
    if tool_type_node is None and args:
        tool_type_node = args[0]
    if tool_type_node is None:
        return "read"
    if isinstance(tool_type_node, ast.Attribute):
        return tool_type_node.attr.lower()
    if isinstance(tool_type_node, ast.Name):
        return tool_type_node.id.lower()
    if isinstance(tool_type_node, ast.Constant):
        return str(tool_type_node.value).lower()
    return "unknown"


def _assistant_reference_actions(domain: str, task_id: str, raw_task: dict[str, Any]) -> list[ReferenceAction]:
    criteria = raw_task.get("evaluation_criteria") or {}
    actions: list[ReferenceAction] = []
    for index, action in enumerate(criteria.get("actions") or []):
        if not isinstance(action, dict):
            continue
        if str(action.get("requestor", "assistant")) != "assistant":
            continue
        actions.append(
            ReferenceAction(
                domain=domain,
                task_id=task_id,
                action_id=str(action.get("action_id", index)),
                index=index,
                name=str(action.get("name", "")),
                arguments=dict(action.get("arguments") or {}),
                reward_basis=tuple(str(item) for item in (criteria.get("reward_basis") or [])),
            )
        )
    return actions


def _public_task_text(raw_task: dict[str, Any]) -> str:
    public_task = {
        key: value
        for key, value in raw_task.items()
        if key not in {"evaluation_criteria", "annotations"}
    }
    return json.dumps(public_task, sort_keys=True, default=str)


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    raw_tokens = re.findall(r"[A-Za-z]+[A-Za-z0-9]*|\d+", normalized.lower())
    tokens: set[str] = set()
    for token in raw_tokens:
        for part in token.split("_"):
            if len(part) >= 3 and part not in STOPWORDS:
                tokens.add(part)
    return tokens


def _tool_tokens(tool: ToolSpec) -> set[str]:
    text = " ".join([tool.name.replace("_", " "), " ".join(tool.arguments), tool.docstring])
    return _tokens(text)


def _visible_values_by_arg(text: str) -> dict[str, tuple[str, ...]]:
    extractors = {
        "customer_id": [r"\bC\d{3,}\b"],
        "line_id": [r"\bL\d{3,}\b"],
        "order_id": [r"#[A-Z]\d{5,}\b"],
        "reservation_id": [r"\b[A-Z0-9]{6}\b"],
        "user_id": [r"\b[a-z]+_[a-z]+_\d{3,}\b"],
        "product_id": [r"\b\d{7,12}\b"],
        "item_id": [r"\b\d{7,12}\b"],
        "new_item_id": [r"\b\d{7,12}\b"],
        "variant_id": [r"\b\d{7,12}\b"],
        "payment_method_id": [r"\b(?:gift_card|credit_card|certificate)_\d{3,}\b"],
        "payment_id": [r"\b(?:gift_card|credit_card|certificate)_\d{3,}\b"],
        "phone_number": [r"\+?\d[\d .()-]{7,}\d"],
        "dob": [r"\b\d{4}-\d{2}-\d{2}\b"],
        "date": [r"\b\d{4}-\d{2}-\d{2}\b"],
        "zip": [r"\b\d{5}(?:-\d{4})?\b"],
        "email": [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"],
        "first_name": [r"\b[A-Z][a-z]{2,}\b"],
        "last_name": [r"\b[A-Z][a-z]{2,}\b"],
        "full_name": [r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b"],
    }
    values: dict[str, tuple[str, ...]] = {}
    for arg, patterns in extractors.items():
        found: set[str] = set()
        for pattern in patterns:
            found.update(match.group(0) for match in re.finditer(pattern, text))
        if found:
            values[arg] = tuple(sorted(found))
    return values


def _missing_grounded_argument_keys(arguments: dict[str, Any], visible_text: str) -> list[str]:
    return [
        key
        for key, value in sorted(arguments.items())
        if not _value_is_grounded(value, visible_text)
    ]


def _candidate_missing_argument_keys(
    candidate: CandidateLease,
    arguments: dict[str, Any],
) -> list[str]:
    return [
        key
        for key, value in sorted(arguments.items())
        if not _candidate_arg_values_cover(candidate.visible_arg_values.get(key, ()), value)
    ]


def _candidate_arg_values_cover(candidate_values: tuple[str, ...], reference_value: Any) -> bool:
    if not candidate_values:
        return False
    if isinstance(reference_value, str):
        return reference_value in candidate_values
    if isinstance(reference_value, bool) or reference_value is None:
        return json.dumps(reference_value) in candidate_values
    if isinstance(reference_value, int | float):
        return str(reference_value) in candidate_values
    return False


def _value_is_grounded(value: Any, visible_text: str) -> bool:
    if isinstance(value, str):
        return bool(value) and value in visible_text
    if isinstance(value, bool) or value is None:
        return json.dumps(value) in visible_text
    if isinstance(value, int | float):
        return str(value) in visible_text
    if isinstance(value, list):
        return bool(value) and all(_value_is_grounded(item, visible_text) for item in value)
    if isinstance(value, dict):
        return bool(value) and all(_value_is_grounded(item, visible_text) for item in value.values())
    return False


def _candidate_risk(candidate: CandidateLease) -> int:
    base = TOOL_RISK.get(candidate.tool.tool_type, TOOL_RISK["unknown"])
    broad_arg_penalty = len(candidate.broad_argument_keys)
    discoverable_penalty = 1 if candidate.tool.discoverable else 0
    return base + broad_arg_penalty + discoverable_penalty


def _mean(values: list[int]) -> float:
    return statistics.fmean(values) if values else 0.0


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
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
