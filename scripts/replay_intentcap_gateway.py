"""Replay an IntentCap trace through the gateway abstraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from intentcap.gateway import TraceGateway


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay an IntentCap JSON trace through the gateway")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace_bytes = args.trace.read_bytes()
    trace = json.loads(trace_bytes)
    gateway = TraceGateway(trace)
    decisions = gateway.replay()
    summary = {
        **gateway.summary(decisions),
        "run_id": args.run_id,
        "trace_path": str(args.trace),
        "input_trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }

    (args.output_dir / "gateway_decisions.json").write_text(json.dumps(decisions, indent=2, sort_keys=True))
    (args.output_dir / "gateway_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (args.output_dir / "exposed_objects.json").write_text(
        json.dumps(gateway.exposed_objects(), indent=2, sort_keys=True)
    )
    (args.output_dir / "command.txt").write_text(_command_text())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


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
