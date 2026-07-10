"""Probe tau2/tau3-bench artifacts without running model evaluations.

The goal is to establish a reproducible utility-benchmark substrate for
IntentCap. This probe parses domain data, task schemas, policy files, and tool
decorators directly from the tau2-bench repository, avoiding API keys and
dependency installation.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any


KNOWN_DOMAINS = (
    "mock",
    "airline",
    "retail",
    "telecom",
    "banking_knowledge",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe tau2-bench artifact structure")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("benchmarks/tau2-bench"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    result = probe(args.benchmark_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(result["summary"], indent=2, sort_keys=True))
    _write_rows(args.output_dir / "domain_summary.csv", result["domain_rows"])
    _write_rows(args.output_dir / "action_summary.csv", result["action_rows"])
    _write_rows(args.output_dir / "tool_summary.csv", result["tool_rows"])
    (args.output_dir / "command.txt").write_text(_command_text())

    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def probe(benchmark_dir: Path) -> dict[str, Any]:
    data_root = benchmark_dir / "data" / "tau2" / "domains"
    src_root = benchmark_dir / "src" / "tau2" / "domains"
    domains = [
        domain
        for domain in KNOWN_DOMAINS
        if (data_root / domain).exists() or (src_root / domain).exists()
    ]

    domain_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    tool_rows: list[dict[str, Any]] = []
    aggregate = Counter()
    reward_basis_counter: Counter[str] = Counter()
    tool_type_counter: Counter[str] = Counter()

    for domain in domains:
        domain_dir = data_root / domain
        src_dir = src_root / domain
        tasks = _load_json_list(domain_dir / "tasks.json")
        voice_tasks = _load_json_list(domain_dir / "tasks_voice.json")
        splits = _load_json_dict(domain_dir / "split_tasks.json")
        db_tables = _top_level_data_tables(domain_dir)
        policy_files = _policy_files(domain_dir)
        documents = list((domain_dir / "documents").glob("*.json"))
        prompt_files = list((domain_dir / "prompts").rglob("*")) if (domain_dir / "prompts").exists() else []
        prompt_files = [path for path in prompt_files if path.is_file()]

        assistant_tools = _parse_tools(src_dir / "tools.py", requestor="assistant")
        user_tools = _parse_tools(src_dir / "user_tools.py", requestor="user")
        all_tools = assistant_tools + user_tools
        for tool in all_tools:
            tool_rows.append({"domain": domain, **tool})
            tool_type_counter[f"{tool['requestor']}:{tool['tool_type']}"] += 1

        task_action_counter = Counter()
        task_reward_counter = Counter()
        action_name_counter = Counter()
        action_requestor_counter = Counter()
        tasks_with_actions = 0
        tasks_with_user_tools = 0
        tasks_with_required_documents = 0
        initialization_actions = 0

        for task in tasks:
            task_id = str(task.get("id", ""))
            criteria = task.get("evaluation_criteria", {}) or {}
            actions = criteria.get("actions", []) or []
            reward_basis = criteria.get("reward_basis", []) or []
            if actions:
                tasks_with_actions += 1
            if task.get("user_tools"):
                tasks_with_user_tools += 1
            if task.get("required_documents"):
                tasks_with_required_documents += 1
            initialization_actions += _count_initialization_actions(task)
            for basis in reward_basis:
                task_reward_counter[str(basis)] += 1
                reward_basis_counter[f"{domain}:{basis}"] += 1
            for action in actions:
                action_name = str(action.get("name", ""))
                requestor = str(action.get("requestor", "assistant"))
                task_action_counter[action_name] += 1
                action_name_counter[action_name] += 1
                action_requestor_counter[requestor] += 1
                action_rows.append(
                    {
                        "domain": domain,
                        "task_id": task_id,
                        "action_id": str(action.get("action_id", "")),
                        "requestor": requestor,
                        "name": action_name,
                        "argument_keys": "|".join(sorted(str(key) for key in (action.get("arguments") or {}))),
                        "reward_basis": "|".join(str(item) for item in reward_basis),
                    }
                )

        base_count = len(splits.get("base", [])) if splits else len(tasks)
        domain_row = {
            "domain": domain,
            "tasks": len(tasks),
            "voice_tasks": len(voice_tasks),
            "base_split_tasks": base_count,
            "split_names": "|".join(sorted(splits)),
            "tasks_with_actions": tasks_with_actions,
            "evaluation_actions": sum(task_action_counter.values()),
            "unique_evaluation_actions": len(task_action_counter),
            "initialization_actions": initialization_actions,
            "tasks_with_user_tools": tasks_with_user_tools,
            "tasks_with_required_documents": tasks_with_required_documents,
            "assistant_tools": sum(1 for tool in assistant_tools if not tool["discoverable"]),
            "assistant_discoverable_tools": sum(1 for tool in assistant_tools if tool["discoverable"]),
            "user_tools": len(user_tools),
            "read_tools": sum(1 for tool in all_tools if tool["tool_type"] == "read"),
            "write_tools": sum(1 for tool in all_tools if tool["tool_type"] == "write"),
            "generic_tools": sum(1 for tool in all_tools if tool["tool_type"] == "generic"),
            "think_tools": sum(1 for tool in all_tools if tool["tool_type"] == "think"),
            "policy_files": len(policy_files),
            "policy_heading_count": sum(_heading_count(path) for path in policy_files),
            "db_tables": "|".join(db_tables),
            "document_files": len(documents),
            "prompt_files": len(prompt_files),
            "top_actions": "|".join(f"{name}:{count}" for name, count in action_name_counter.most_common(8)),
            "action_requestors": "|".join(
                f"{name}:{count}" for name, count in sorted(action_requestor_counter.items())
            ),
            "reward_basis_counts": "|".join(
                f"{name}:{count}" for name, count in sorted(task_reward_counter.items())
            ),
        }
        domain_rows.append(domain_row)
        aggregate["tasks"] += len(tasks)
        aggregate["voice_tasks"] += len(voice_tasks)
        aggregate["base_split_tasks"] += base_count
        aggregate["evaluation_actions"] += sum(task_action_counter.values())
        aggregate["tasks_with_actions"] += tasks_with_actions
        aggregate["initialization_actions"] += initialization_actions
        aggregate["assistant_tools"] += domain_row["assistant_tools"]
        aggregate["assistant_discoverable_tools"] += domain_row["assistant_discoverable_tools"]
        aggregate["user_tools"] += len(user_tools)
        aggregate["documents"] += len(documents)

    summary = {
        "benchmark": "tau2-bench / tau3-bench",
        "benchmark_dir": str(benchmark_dir),
        "domains": len(domains),
        "domain_names": domains,
        "tasks": aggregate["tasks"],
        "voice_tasks": aggregate["voice_tasks"],
        "base_split_tasks": aggregate["base_split_tasks"],
        "evaluation_actions": aggregate["evaluation_actions"],
        "tasks_with_actions": aggregate["tasks_with_actions"],
        "initialization_actions": aggregate["initialization_actions"],
        "assistant_tools": aggregate["assistant_tools"],
        "assistant_discoverable_tools": aggregate["assistant_discoverable_tools"],
        "user_tools": aggregate["user_tools"],
        "documents": aggregate["documents"],
        "reward_basis_counts": dict(sorted(reward_basis_counter.items())),
        "tool_type_counts": dict(sorted(tool_type_counter.items())),
        "notes": [
            "This is an artifact/schema probe only; it does not run tau2 simulations or model APIs.",
            "evaluation_criteria.actions are reference trajectories for target state derivation unless ACTION is in reward_basis.",
            "Tool counts are parsed from @is_tool and @is_discoverable_tool decorators in domain tool modules.",
        ],
    }
    return {
        "summary": summary,
        "domain_rows": domain_rows,
        "action_rows": action_rows,
        "tool_rows": tool_rows,
    }


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return data if isinstance(data, dict) else {}


def _top_level_data_tables(domain_dir: Path) -> list[str]:
    tables: set[str] = set()
    for name in ("db.json", "user_db.json"):
        data = _load_json_dict(domain_dir / name)
        tables.update(str(key) for key in data)
    for name in ("db.toml", "user_db.toml"):
        path = domain_dir / name
        if path.exists():
            data = tomllib.loads(path.read_text())
            if isinstance(data, dict):
                tables.update(str(key) for key in data)
    return sorted(tables)


def _policy_files(domain_dir: Path) -> list[Path]:
    return sorted(path for path in domain_dir.glob("*.md") if "policy" in path.name or "manual" in path.name or "workflow" in path.name)


def _heading_count(path: Path) -> int:
    return sum(1 for line in path.read_text(errors="replace").splitlines() if line.lstrip().startswith("#"))


def _count_initialization_actions(task: dict[str, Any]) -> int:
    initial_state = task.get("initial_state") or {}
    if not isinstance(initial_state, dict):
        return 0
    actions = initial_state.get("initialization_actions") or []
    return len(actions) if isinstance(actions, list) else 0


def _parse_tools(path: Path, *, requestor: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    tree = ast.parse(path.read_text())
    tools: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        marker = _tool_marker(node)
        if marker is None:
            continue
        decorator, tool_type = marker
        tools.append(
            {
                "requestor": requestor,
                "name": node.name,
                "tool_type": tool_type,
                "discoverable": decorator == "is_discoverable_tool",
                "argument_count": len([arg for arg in node.args.args if arg.arg != "self"]),
                "arguments": "|".join(arg.arg for arg in node.args.args if arg.arg != "self"),
                "docstring_words": len((ast.get_docstring(node) or "").split()),
                "source_file": str(path),
            }
        )
    return sorted(tools, key=lambda item: item["name"])


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
