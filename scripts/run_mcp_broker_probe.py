"""Run a local MCP-style JSON-RPC broker probe.

The probe models an MCP broker as a live pre-tool-call adapter. It parses
``tools/list`` and ``tools/call`` shaped JSON-RPC requests, checks every
``tools/call`` through the IntentCap checker before invoking a fake MCP server,
and compares that behavior with object-only and server-allowlist brokers.
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
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent / "src") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from intentcap.checker import CheckerSession  # noqa: E402


DEFAULT_SUITE = Path("examples/mcp_broker_jsonrpc_suite.json")
ROW_FIELDS = [
    "backend",
    "index",
    "event_id",
    "tool",
    "jsonrpc_method",
    "checker_allowed",
    "broker_allowed",
    "executed",
    "unsafe_reference_event",
    "unsafe_execution",
    "unsafe_kind",
    "reason",
    "latency_ms",
    "response",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MCP-style broker probe")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R301MCPBROKER")
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

    brokers = [
        _McpBroker("intentcap_mcp_broker", suite),
        _McpBroker("object_only_broker", suite),
        _McpBroker("server_allowlist_broker", suite),
    ]
    rows: list[dict[str, Any]] = []
    tool_lists: dict[str, list[str]] = {}
    server_states: dict[str, dict[str, Any]] = {}
    for broker in brokers:
        tool_lists[broker.backend] = broker.list_tools()
        rows.extend(broker.run())
        server_states[broker.backend] = broker.server.state()

    summary = _summary(
        run_id=run_id,
        suite_path=suite_path,
        suite_bytes=suite_bytes,
        output_dir=output_dir,
        suite=suite,
        rows=rows,
        tool_lists=tool_lists,
        server_states=server_states,
    )

    _write_rows(output_dir / "mcp_broker_rows.csv", rows)
    (output_dir / "mcp_broker_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "tool_lists.json").write_text(
        json.dumps(tool_lists, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "server_states.json").write_text(
        json.dumps(server_states, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "input_digests.csv").write_text(
        "path,sha256,bytes\n"
        f"{suite_path},{hashlib.sha256(suite_bytes).hexdigest()},{len(suite_bytes)}\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


class _McpBroker:
    def __init__(self, backend: str, suite: dict[str, Any]) -> None:
        self.backend = backend
        self.suite = suite
        self.session = CheckerSession.from_trace(suite)
        self.server = _FakeMcpServer(_server_tools(suite))
        self.leased_tools = {
            str(lease.get("object"))
            for lease in suite.get("leases", [])
            if lease.get("op") == "mcp.call"
        }

    def list_tools(self) -> list[str]:
        if self.backend in {"intentcap_mcp_broker", "object_only_broker"}:
            return sorted(tool for tool in self.server.tools if tool in self.leased_tools)
        if self.backend == "server_allowlist_broker":
            return sorted(self.server.tools)
        raise ValueError(f"unknown backend: {self.backend}")

    def run(self) -> list[dict[str, Any]]:
        rows = []
        for index, event in enumerate(self.suite.get("events", [])):
            rows.append(self._handle_event(index, event))
        return rows

    def _handle_event(self, index: int, event: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        checker_verdict = self.session.check(event)
        broker_verdict = self._authorize(event, checker_verdict)
        response: dict[str, Any] | None = None
        executed = False
        if broker_verdict["allowed"]:
            response = self.server.handle(_request(event))
            executed = response.get("error") is None
        latency_ms = (time.perf_counter() - started) * 1000.0
        unsafe = bool(event.get("unsafe_reference_event"))
        return {
            "backend": self.backend,
            "index": index,
            "event_id": str(event.get("id", "")),
            "tool": _tool_name(event),
            "jsonrpc_method": str(_request(event).get("method", "")),
            "checker_allowed": bool(checker_verdict["allowed"]),
            "broker_allowed": bool(broker_verdict["allowed"]),
            "executed": executed,
            "unsafe_reference_event": unsafe,
            "unsafe_execution": unsafe and executed,
            "unsafe_kind": str(event.get("unsafe_kind", "")),
            "reason": str(broker_verdict["reason"]),
            "latency_ms": f"{latency_ms:.3f}",
            "response": json.dumps(response or {}, sort_keys=True),
        }

    def _authorize(
        self,
        event: dict[str, Any],
        checker_verdict: dict[str, Any],
    ) -> dict[str, Any]:
        tool = _tool_name(event)
        if self.backend == "intentcap_mcp_broker":
            return checker_verdict
        if self.backend == "object_only_broker":
            allowed = str(event.get("op")) == "mcp.call" and tool in self.leased_tools
            return {
                "allowed": allowed,
                "reason": "object-only method match" if allowed else "object-only no method",
            }
        if self.backend == "server_allowlist_broker":
            allowed = str(event.get("op")) == "mcp.call" and tool in self.server.tools
            return {
                "allowed": allowed,
                "reason": "server allowlist match" if allowed else "server allowlist no method",
            }
        raise ValueError(f"unknown backend: {self.backend}")


class _FakeMcpServer:
    def __init__(self, tools: set[str]) -> None:
        self.tools = tools
        self.issues: list[dict[str, Any]] = []
        self.repositories: list[dict[str, Any]] = []
        self.oauth_scopes: list[str] = []

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("method") != "tools/call":
            return _error_response(request, "unsupported method")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return _error_response(request, "invalid params")
        tool = str(params.get("name", ""))
        args = params.get("arguments", {})
        if not isinstance(args, dict):
            return _error_response(request, "invalid arguments")
        if tool not in self.tools:
            return _error_response(request, "unknown tool")
        if tool == "github.create_issue":
            issue = {
                "repo": str(args.get("repo", "")),
                "title": str(args.get("title", "")),
                "body": str(args.get("body", "")),
            }
            self.issues.append(issue)
            return _ok_response(request, {"issue_number": len(self.issues), **issue})
        if tool == "github.create_repository":
            repo = {
                "repo": str(args.get("repo", "")),
                "private": bool(args.get("private", False)),
            }
            self.repositories.append(repo)
            return _ok_response(request, repo)
        if tool == "github.request_oauth_scope":
            scope = str(args.get("scope", ""))
            self.oauth_scopes.append(scope)
            return _ok_response(request, {"scope": scope})
        return _error_response(request, "unimplemented tool")

    def state(self) -> dict[str, Any]:
        return {
            "issues": self.issues,
            "repositories": self.repositories,
            "oauth_scopes": self.oauth_scopes,
        }


def _summary(
    *,
    run_id: str,
    suite_path: Path,
    suite_bytes: bytes,
    output_dir: Path,
    suite: dict[str, Any],
    rows: list[dict[str, Any]],
    tool_lists: dict[str, list[str]],
    server_states: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_backend = {
        backend: _backend_summary([row for row in rows if row["backend"] == backend])
        for backend in sorted({str(row["backend"]) for row in rows})
    }
    return {
        "run_id": run_id,
        "analysis": "MCP-style JSON-RPC broker probe",
        "suite_path": str(suite_path),
        "input_suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
        "events": len(suite.get("events", [])),
        "server_tool_count": len(_server_tools(suite)),
        "tool_lists": tool_lists,
        "tool_list_counts": {
            backend: len(tools)
            for backend, tools in sorted(tool_lists.items())
        },
        "backends": by_backend,
        "server_states": server_states,
        "output_dir": str(output_dir),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "no_dataset_sync": True,
        "not_a_model_run": True,
        "notes": [
            "The fake MCP server is local and deterministic.",
            "IntentCap is checked before each tools/call handler runs.",
            "This is a production-like JSON-RPC broker shape, not a deployed MCP server.",
        ],
    }


def _backend_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unsafe_kind_counts = Counter(
        str(row["unsafe_kind"])
        for row in rows
        if row["unsafe_execution"] and row["unsafe_kind"]
    )
    return {
        "events": len(rows),
        "broker_allowed": _count(rows, "broker_allowed"),
        "executed": _count(rows, "executed"),
        "checker_denied_events_executed": sum(
            1
            for row in rows
            if row["executed"] and not row["checker_allowed"]
        ),
        "unsafe_executions": _count(rows, "unsafe_execution"),
        "blocked_unsafe_events": sum(
            1
            for row in rows
            if row["unsafe_reference_event"] and not row["executed"]
        ),
        "unsafe_kind_counts": dict(sorted(unsafe_kind_counts.items())),
    }


def _server_tools(suite: dict[str, Any]) -> set[str]:
    server = suite.get("server", {})
    tools = server.get("tools", []) if isinstance(server, dict) else []
    return {str(tool) for tool in tools}


def _request(event: dict[str, Any]) -> dict[str, Any]:
    request = event.get("mcp_request", {})
    return request if isinstance(request, dict) else {}


def _tool_name(event: dict[str, Any]) -> str:
    request = _request(event)
    params = request.get("params", {})
    if isinstance(params, dict) and "name" in params:
        return str(params["name"])
    return str(event.get("object", ""))


def _ok_response(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request.get("id"), "result": result}


def _error_response(request: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {"code": -32000, "message": message},
    }


def _count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row[key])


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _command_text() -> str:
    return " ".join([sys.executable, *sys.argv]) + "\n"


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "<unavailable>"


if __name__ == "__main__":
    raise SystemExit(main())
