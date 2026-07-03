"""Replay an IntentCap trace through the gateway abstraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from intentcap.gateway import TraceGateway


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay an IntentCap JSON trace through the gateway")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace = json.loads(args.trace.read_text())
    gateway = TraceGateway(trace)
    decisions = gateway.replay()
    summary = gateway.summary(decisions)

    (args.output_dir / "gateway_decisions.json").write_text(json.dumps(decisions, indent=2, sort_keys=True))
    (args.output_dir / "gateway_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (args.output_dir / "exposed_objects.json").write_text(
        json.dumps(gateway.exposed_objects(), indent=2, sort_keys=True)
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
