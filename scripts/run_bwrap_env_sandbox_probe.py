"""Run the env side-effect suite through a real bubblewrap sandbox.

This probe is stronger than the replay-only lowering target: it executes local
file/process handlers in a Linux namespace sandbox created by bubblewrap. The
sandbox is still not ActPlane/eBPF and not a production MCP broker. It is a
local OS-substrate probe showing what the env projection can and cannot enforce:
filesystem/process/network containment is OS-visible, while holder/provenance
and prompt-placement authority still require the IntentCap checker.
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

from intentcap.gateway import TraceGateway  # noqa: E402


DEFAULT_TRACE = Path("examples/env_adapter_side_effect_suite.json")

ROW_FIELDS = [
    "backend",
    "event_index",
    "event_id",
    "op",
    "object",
    "checker_allowed",
    "backend_allowed",
    "sandbox_attempted",
    "sandbox_success",
    "host_effect",
    "semantic_effect",
    "unsafe_reference_event",
    "unsafe_host_effect",
    "unsafe_semantic_effect",
    "contained_by_sandbox",
    "reason",
    "returncode",
    "elapsed_ms",
    "stdout",
    "stderr",
]
INPUT_DIGEST_FIELDS = ["input_name", "path", "sha256", "bytes"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bubblewrap env sandbox probe")
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="R298BWRAP")
    args = parser.parse_args()

    result = run_probe(trace_path=args.trace, output_dir=args.output_dir, run_id=args.run_id)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


def run_probe(*, trace_path: Path, output_dir: Path, run_id: str) -> dict[str, Any]:
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        raise RuntimeError("bubblewrap executable not found")

    trace_bytes = trace_path.read_bytes()
    trace = json.loads(trace_bytes)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    roots = {
        "intentcap_bwrap": output_dir / "intentcap_bwrap",
        "object_only_bwrap": output_dir / "object_only_bwrap",
    }
    for root in roots.values():
        _prepare_fixture(root)

    rows: list[dict[str, Any]] = []
    rows.extend(
        _run_backend(
            backend="intentcap_bwrap",
            trace=trace,
            root=roots["intentcap_bwrap"],
            bwrap=bwrap,
        )
    )
    rows.extend(
        _run_backend(
            backend="object_only_bwrap",
            trace=trace,
            root=roots["object_only_bwrap"],
            bwrap=bwrap,
        )
    )
    network_probe = _forced_network_probe(bwrap=bwrap)

    digests = [_file_digest("trace", trace_path)]
    summary = _summary(
        run_id=run_id,
        trace_path=trace_path,
        trace_bytes=trace_bytes,
        rows=rows,
        digests=digests,
        network_probe=network_probe,
        bwrap=bwrap,
        output_dir=output_dir,
    )

    _write_rows(output_dir / "bwrap_env_sandbox_rows.csv", rows, ROW_FIELDS)
    _write_rows(output_dir / "input_digests.csv", digests, INPUT_DIGEST_FIELDS)
    (output_dir / "bwrap_env_sandbox_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "command.txt").write_text(_command_text())
    return {"summary": summary, "rows": rows}


def _prepare_fixture(root: Path) -> None:
    (root / "workspace" / "invoices").mkdir(parents=True)
    (root / "workspace" / "out").mkdir(parents=True)
    (root / "skills" / "pdf").mkdir(parents=True)
    (root / "workspace" / "invoices" / "a.pdf").write_text("invoice,total\nA-001,42\n")
    (root / "workspace" / "secrets.env").write_text("TOP_SECRET=do-not-read-or-overwrite\n")
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
    bwrap: str,
) -> list[dict[str, Any]]:
    rows = []
    for index, event in enumerate(trace.get("events", [])):
        checker_decision = _checker_decision(trace, index, event)
        checker_allowed = bool(checker_decision["allowed"])
        backend_allowed, reason = _backend_decision(backend, trace, checker_decision, event)
        before = _fixture_state(root)
        completed: subprocess.CompletedProcess[str] | None = None
        elapsed_ms = 0.0
        sandbox_attempted = bool(backend_allowed and _is_os_relevant(event))
        semantic_effect = bool(backend_allowed and event.get("op") == "ctx.use")
        if sandbox_attempted:
            start = time.perf_counter()
            completed = _execute_in_bwrap(event=event, root=root, bwrap=bwrap)
            elapsed_ms = (time.perf_counter() - start) * 1000
        after = _fixture_state(root)
        host_effect = _host_effect(event, before, after)
        unsafe = not checker_allowed
        sandbox_success = bool(completed and completed.returncode == 0)
        contained = bool(
            unsafe
            and sandbox_attempted
            and not host_effect
            and event.get("op") in {"exec.run", "fs.read", "fs.write", "net.connect"}
        )
        rows.append(
            {
                "backend": backend,
                "event_index": index,
                "event_id": str(event.get("id", "")),
                "op": str(event.get("op", "")),
                "object": str(event.get("object", "")),
                "checker_allowed": checker_allowed,
                "backend_allowed": backend_allowed,
                "sandbox_attempted": sandbox_attempted,
                "sandbox_success": sandbox_success,
                "host_effect": host_effect,
                "semantic_effect": semantic_effect,
                "unsafe_reference_event": unsafe,
                "unsafe_host_effect": bool(unsafe and host_effect),
                "unsafe_semantic_effect": bool(unsafe and semantic_effect),
                "contained_by_sandbox": contained,
                "reason": reason,
                "returncode": completed.returncode if completed else "",
                "elapsed_ms": round(elapsed_ms, 3),
                "stdout": _short(completed.stdout if completed else ""),
                "stderr": _short(completed.stderr if completed else ""),
            }
        )
    return rows


def _backend_decision(
    backend: str,
    trace: dict[str, Any],
    checker_decision: dict[str, Any],
    event: dict[str, Any],
) -> tuple[bool, str]:
    if backend == "intentcap_bwrap":
        return bool(checker_decision["allowed"]), str(checker_decision["reason"])
    if backend == "object_only_bwrap":
        exposed = {(lease.get("op"), lease.get("object")) for lease in trace.get("leases", [])}
        allowed = (event.get("op"), event.get("object")) in exposed
        return allowed, "object-only match" if allowed else "object-only no matching object"
    raise ValueError(f"unknown backend: {backend}")


def _checker_decision(
    trace: dict[str, Any],
    index: int,
    event: dict[str, Any],
) -> dict[str, Any]:
    prefix = {**trace, "events": trace.get("events", [])[:index] + [event]}
    return TraceGateway(prefix).replay()[-1]


def _is_os_relevant(event: dict[str, Any]) -> bool:
    return event.get("op") in {"exec.run", "fs.read", "fs.write", "net.connect"}


def _execute_in_bwrap(
    *,
    event: dict[str, Any],
    root: Path,
    bwrap: str,
) -> subprocess.CompletedProcess[str]:
    op = event.get("op")
    if op == "exec.run":
        args = event.get("args", {})
        command = [
            "/usr/bin/python3",
            str(event.get("object", "")),
            "--input",
            str(args.get("input", "")),
            "--output",
            str(args.get("output", "")),
        ]
    elif op == "fs.read":
        path = str(event.get("args", {}).get("path", ""))
        command = [
            "/usr/bin/python3",
            "-c",
            "from pathlib import Path; import sys; data=Path(sys.argv[1]).read_bytes(); print(len(data))",
            path,
        ]
    elif op == "fs.write":
        path = str(event.get("args", {}).get("path", ""))
        command = [
            "/usr/bin/python3",
            "-c",
            (
                "from pathlib import Path; import sys; "
                "p=Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); "
                "p.write_text('written_by=bwrap\\n')"
            ),
            path,
        ]
    elif op == "net.connect":
        args = event.get("args", {})
        command = [
            "/usr/bin/python3",
            "-c",
            (
                "import socket, sys; "
                "socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=0.2)"
            ),
            str(args.get("host", "")),
            str(args.get("port", 0)),
        ]
    else:
        raise ValueError(f"unsupported bwrap op: {op}")
    return subprocess.run(
        _bwrap_base_args(root=root, bwrap=bwrap) + command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )


def _bwrap_base_args(*, root: Path, bwrap: str) -> list[str]:
    return [
        bwrap,
        "--unshare-all",
        "--die-with-parent",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/workspace",
        "--dir",
        "/workspace/invoices",
        "--ro-bind",
        str(root / "workspace" / "invoices" / "a.pdf"),
        "/workspace/invoices/a.pdf",
        "--bind",
        str(root / "workspace" / "out"),
        "/workspace/out",
        "--dir",
        "/skills",
        "--dir",
        "/skills/pdf",
        "--ro-bind",
        str(root / "skills" / "pdf" / "extract_tables.py"),
        "/skills/pdf/extract_tables.py",
    ]


def _forced_network_probe(*, bwrap: str) -> dict[str, Any]:
    start = time.perf_counter()
    completed = subprocess.run(
        [
            bwrap,
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "/usr/bin/python3",
            "-c",
            "import socket; socket.create_connection(('1.1.1.1', 443), timeout=0.2)",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    return {
        "attempted": True,
        "blocked": completed.returncode != 0,
        "returncode": completed.returncode,
        "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
        "stderr": _short(completed.stderr),
    }


def _fixture_state(root: Path) -> dict[str, Any]:
    paths = {
        "selected_output": root / "workspace" / "out" / "a.xlsx",
        "secret": root / "workspace" / "secrets.env",
        "tmp_exfil": root / "tmp" / "exfil.csv",
    }
    return {
        name: {
            "exists": path.exists(),
            "sha256": _path_sha256(path) if path.exists() else "",
            "bytes": path.stat().st_size if path.exists() else 0,
        }
        for name, path in paths.items()
    }


def _host_effect(event: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> bool:
    op = event.get("op")
    if op in {"exec.run", "fs.write"}:
        return before != after
    if op == "fs.read":
        return bool(after == before and event.get("args", {}).get("path") == "/workspace/invoices/a.pdf")
    return False


def _summary(
    *,
    run_id: str,
    trace_path: Path,
    trace_bytes: bytes,
    rows: list[dict[str, Any]],
    digests: list[dict[str, Any]],
    network_probe: dict[str, Any],
    bwrap: str,
    output_dir: Path,
) -> dict[str, Any]:
    by_backend: dict[str, dict[str, Any]] = {}
    for backend in sorted({str(row["backend"]) for row in rows}):
        backend_rows = [row for row in rows if row["backend"] == backend]
        allowed = [row for row in backend_rows if row["backend_allowed"]]
        attempted = [row for row in backend_rows if row["sandbox_attempted"]]
        by_backend[backend] = {
            "events": len(backend_rows),
            "allowed_by_backend": len(allowed),
            "sandbox_attempts": len(attempted),
            "sandbox_successes": sum(1 for row in attempted if row["sandbox_success"]),
            "unsafe_reference_events_allowed": sum(
                1 for row in allowed if row["unsafe_reference_event"]
            ),
            "unsafe_host_effects": sum(1 for row in backend_rows if row["unsafe_host_effect"]),
            "unsafe_semantic_effects": sum(
                1 for row in backend_rows if row["unsafe_semantic_effect"]
            ),
            "unsafe_events_contained_by_sandbox": sum(
                1 for row in backend_rows if row["contained_by_sandbox"]
            ),
            "mean_sandbox_elapsed_ms": round(
                sum(float(row["elapsed_ms"]) for row in attempted) / len(attempted), 3
            )
            if attempted
            else 0.0,
            "max_sandbox_elapsed_ms": max(
                [float(row["elapsed_ms"]) for row in attempted] or [0.0]
            ),
        }
    return {
        "run_id": run_id,
        "analysis": "bubblewrap namespace env sandbox probe",
        "trace_path": str(trace_path),
        "input_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "bwrap": bwrap,
        "bwrap_version": _command_output([bwrap, "--version"]),
        "strace_version": _command_output(["strace", "-V"]).splitlines()[0],
        "backends": by_backend,
        "forced_network_probe": network_probe,
        "input_digests": digests,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "project_head": _git_output(["git", "rev-parse", "HEAD"]),
        "git_status": _git_output(["git", "status", "--short", "--branch"]),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "output_dir": str(output_dir),
        "notes": [
            "This run executes local handlers under bubblewrap namespaces.",
            "It does not run a model, clone/sync/download datasets, or implement ActPlane/eBPF.",
            "Bubblewrap enforces OS-visible filesystem/process/network containment but cannot decide holder/provenance or prompt-placement authority.",
        ],
    }


def _path_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_digest(name: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "input_name": name,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _short(text: str, limit: int = 500) -> str:
    return text.replace("\n", "\\n")[:limit]


def _command_text() -> str:
    parts: list[str] = []
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        parts.append(f"PYTHONPATH={pythonpath}")
    parts.append(sys.executable)
    parts.extend(sys.argv)
    return " ".join(parts) + "\n"


def _command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except Exception:
        return ""


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
