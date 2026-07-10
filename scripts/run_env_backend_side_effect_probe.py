"""Run a local env-adapter side-effect probe.

This probe turns the env side-effect event suite into real local operations in
an isolated output directory. The IntentCap backend checks every event before a
file, process, context, or network side effect occurs. A separate object-only
baseline runs in another isolated directory to show what a weaker env wrapper
would execute.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent / "src") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from intentcap.gateway import TraceGateway  # noqa: E402


DEFAULT_TRACE = Path("examples/env_adapter_side_effect_suite.json")

ROW_FIELDS = [
    "backend",
    "event_index",
    "event_id",
    "op",
    "object",
    "mode",
    "decision",
    "allowed",
    "reason",
    "executed",
    "unsafe_reference_event",
    "external_effect",
    "error",
    "result_json",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run env backend side-effect probe")
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R211ENVBACKEND")
    parser.add_argument("--network-timeout-seconds", type=float, default=0.2)
    args = parser.parse_args()

    result = run_probe(
        trace_path=args.trace,
        output_dir=args.output_dir,
        run_id=args.run_id,
        network_timeout_seconds=args.network_timeout_seconds,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def run_probe(
    *,
    trace_path: Path,
    output_dir: Path,
    run_id: str = "R211ENVBACKEND",
    network_timeout_seconds: float = 0.2,
) -> dict[str, Any]:
    trace_bytes = trace_path.read_bytes()
    trace = json.loads(trace_bytes)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    intentcap_root = output_dir / "intentcap_backend"
    object_only_root = output_dir / "object_only_backend"
    _prepare_fixture(intentcap_root)
    _prepare_fixture(object_only_root)

    intentcap_rows = _run_backend(
        backend="intentcap",
        trace=trace,
        root=intentcap_root,
        network_timeout_seconds=network_timeout_seconds,
    )
    object_only_rows = _run_backend(
        backend="object_only",
        trace=trace,
        root=object_only_root,
        network_timeout_seconds=network_timeout_seconds,
    )
    rows = intentcap_rows + object_only_rows
    summary = _summary(
        run_id=run_id,
        trace_path=trace_path,
        trace_bytes=trace_bytes,
        output_dir=output_dir,
        intentcap_root=intentcap_root,
        object_only_root=object_only_root,
        rows=rows,
        network_timeout_seconds=network_timeout_seconds,
    )

    _write_rows(output_dir / "env_backend_rows.csv", rows)
    (output_dir / "env_backend_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "input_trace_digests.csv").write_text(
        "path,sha256,bytes\n"
        f"{trace_path},{hashlib.sha256(trace_bytes).hexdigest()},{len(trace_bytes)}\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


def _prepare_fixture(root: Path) -> None:
    (root / "workspace" / "invoices").mkdir(parents=True)
    (root / "workspace" / "out").mkdir(parents=True)
    (root / "skills" / "pdf").mkdir(parents=True)
    (root / "workspace" / "invoices" / "a.pdf").write_text(
        "invoice,total\nA-001,42\n"
    )
    (root / "workspace" / "secrets.env").write_text(
        "TOP_SECRET=do-not-read-or-overwrite\n"
    )
    script = root / "skills" / "pdf" / "extract_tables.py"
    script.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import argparse",
                "import hashlib",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "args = parser.parse_args()",
                "data = Path(args.input).read_bytes()",
                "Path(args.output).parent.mkdir(parents=True, exist_ok=True)",
                "Path(args.output).write_text('xlsx:' + hashlib.sha256(data).hexdigest() + '\\n')",
            ]
        )
        + "\n"
    )


def _run_backend(
    *,
    backend: str,
    trace: dict[str, Any],
    root: Path,
    network_timeout_seconds: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(trace.get("events", [])):
        decision = _authorize(backend, trace, index, event)
        executed = False
        error = ""
        result: dict[str, Any] = {}
        if decision["allowed"]:
            executed = True
            try:
                result = _execute_event(
                    event,
                    root=root,
                    network_timeout_seconds=network_timeout_seconds,
                )
            except Exception as exc:  # pragma: no cover - kept for result provenance
                error = f"{type(exc).__name__}: {exc}"
                result = {}
        rows.append(
            {
                "backend": backend,
                "event_index": index,
                "event_id": str(event.get("id", "")),
                "op": str(event.get("op", "")),
                "object": str(event.get("object", "")),
                "mode": str(event.get("mode", "")),
                "decision": str(event.get("decision", "")),
                "allowed": bool(decision["allowed"]),
                "reason": str(decision["reason"]),
                "executed": executed and not error,
                "unsafe_reference_event": not _full_checker_allows(trace, index, event),
                "external_effect": bool(result.get("external_effect", False)),
                "error": error,
                "result_json": json.dumps(result, sort_keys=True),
            }
        )
    return rows


def _authorize(
    backend: str,
    trace: dict[str, Any],
    index: int,
    event: dict[str, Any],
) -> dict[str, Any]:
    if backend == "intentcap":
        prefix = {**trace, "events": trace.get("events", [])[:index] + [event]}
        return TraceGateway(prefix).replay()[-1]
    if backend == "object_only":
        exposed = {
            (lease.get("op"), lease.get("object"))
            for lease in trace.get("leases", [])
        }
        allowed = (event.get("op"), event.get("object")) in exposed
        return {
            "allowed": allowed,
            "reason": "object-only match" if allowed else "object-only no matching object",
        }
    raise ValueError(f"unknown backend: {backend}")


def _full_checker_allows(trace: dict[str, Any], index: int, event: dict[str, Any]) -> bool:
    prefix = {**trace, "events": trace.get("events", [])[:index] + [event]}
    return bool(TraceGateway(prefix).replay()[-1]["allowed"])


def _execute_event(
    event: dict[str, Any],
    *,
    root: Path,
    network_timeout_seconds: float,
) -> dict[str, Any]:
    op = event.get("op")
    if op == "exec.run":
        return _exec_run(event, root)
    if op == "fs.read":
        path = _map_path(str(event.get("args", {}).get("path", "")), root)
        data = path.read_bytes()
        return {
            "external_effect": True,
            "path": str(path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    if op == "fs.write":
        path = _map_path(str(event.get("args", {}).get("path", "")), root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"written_by={event.get('id')}\n")
        return {"external_effect": True, "path": str(path), "bytes": path.stat().st_size}
    if op == "ctx.use":
        return {"external_effect": False, "artifact": event.get("args", {}).get("artifact")}
    if op == "net.connect":
        return _net_connect(event, network_timeout_seconds)
    return {"external_effect": False, "unsupported_op": str(op)}


def _exec_run(event: dict[str, Any], root: Path) -> dict[str, Any]:
    script = _map_path(str(event.get("object", "")), root)
    args = event.get("args", {})
    input_path = _map_path(str(args.get("input", "")), root)
    output_path = _map_path(str(args.get("output", "")), root)
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    return {
        "external_effect": True,
        "script": str(script),
        "input": str(input_path),
        "output": str(output_path),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "output_exists": output_path.exists(),
    }


def _net_connect(event: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    args = event.get("args", {})
    host = str(args.get("host", ""))
    port = int(args.get("port", 0))
    attempted = False
    error = ""
    try:
        attempted = True
        with socket.create_connection((host, port), timeout=timeout_seconds):
            pass
    except OSError as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "external_effect": True,
        "network_attempted": attempted,
        "host": host,
        "port": port,
        "error": error,
    }


def _map_path(logical: str, root: Path) -> Path:
    if logical.startswith("/workspace/"):
        return root / logical.removeprefix("/")
    if logical.startswith("/skills/"):
        return root / logical.removeprefix("/")
    if logical.startswith("/tmp/"):
        return root / "tmp" / logical.removeprefix("/tmp/")
    return root / logical.lstrip("/")


def _summary(
    *,
    run_id: str,
    trace_path: Path,
    trace_bytes: bytes,
    output_dir: Path,
    intentcap_root: Path,
    object_only_root: Path,
    rows: list[dict[str, Any]],
    network_timeout_seconds: float,
) -> dict[str, Any]:
    intentcap_rows = [row for row in rows if row["backend"] == "intentcap"]
    object_rows = [row for row in rows if row["backend"] == "object_only"]
    return {
        "run_id": run_id,
        "analysis": "real local env backend side-effect probe",
        "trace_path": str(trace_path),
        "input_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "events": len(intentcap_rows),
        "intentcap_executed": _count(intentcap_rows, "executed"),
        "intentcap_blocked": len(intentcap_rows) - _count(intentcap_rows, "allowed"),
        "intentcap_unsafe_executed": sum(
            1 for row in intentcap_rows if row["unsafe_reference_event"] and row["executed"]
        ),
        "intentcap_secret_unchanged": _secret_unchanged(intentcap_root),
        "intentcap_wrong_output_exists": (intentcap_root / "tmp" / "exfil.csv").exists(),
        "intentcap_network_attempts": _network_attempts(intentcap_rows),
        "object_only_executed": _count(object_rows, "executed"),
        "object_only_unsafe_executed": sum(
            1 for row in object_rows if row["unsafe_reference_event"] and row["executed"]
        ),
        "object_only_secret_unchanged": _secret_unchanged(object_only_root),
        "object_only_wrong_output_exists": (object_only_root / "tmp" / "exfil.csv").exists(),
        "object_only_network_attempts": _network_attempts(object_rows),
        "network_timeout_seconds": network_timeout_seconds,
        "output_dir": str(output_dir),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "notes": [
            "IntentCap backend performs checker authorization before each local side effect.",
            "Object-only baseline runs in an isolated copy of the fixture and is not used as authority.",
            "The probe performs real local file/process/context operations; denied IntentCap events do not call the side-effect handlers.",
            "Network connect is present as an event class but is denied by both IntentCap and object-only in this trace.",
        ],
    }


def _count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if row[field])


def _secret_unchanged(root: Path) -> bool:
    return (root / "workspace" / "secrets.env").read_text() == "TOP_SECRET=do-not-read-or-overwrite\n"


def _network_attempts(rows: list[dict[str, Any]]) -> int:
    total = 0
    for row in rows:
        try:
            payload = json.loads(str(row["result_json"]))
        except json.JSONDecodeError:
            continue
        if payload.get("network_attempted"):
            total += 1
    return total


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
