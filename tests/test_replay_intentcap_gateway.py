import json
import subprocess
import sys
from pathlib import Path


def test_replay_intentcap_gateway_records_run_metadata(tmp_path):
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "tool_select": ["tool.choice"],
                }
            }
        },
        "leases": [
            {
                "id": "tool",
                "op": "tool.call",
                "object": "safe.tool",
                "args": {},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
            }
        ],
        "events": [
            {
                "id": "safe",
                "op": "tool.call",
                "object": "safe.tool",
                "args": {},
                "decision": "tool.choice",
                "mode": "tool_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            }
        ],
    }
    trace_path = tmp_path / "trace.json"
    output_dir = tmp_path / "out"
    trace_path.write_text(json.dumps(trace))

    script = Path(__file__).parents[1] / "scripts" / "replay_intentcap_gateway.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            str(trace_path),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "test-run",
        ],
        check=True,
        cwd=Path(__file__).parents[1],
        text=True,
        capture_output=True,
    )

    summary = json.loads((output_dir / "gateway_summary.json").read_text())
    command = (output_dir / "command.txt").read_text()

    assert json.loads(result.stdout)["run_id"] == "test-run"
    assert summary["run_id"] == "test-run"
    assert summary["attempted_events"] == 1
    assert summary["executed_events"] == 1
    assert summary["input_trace_sha256"]
    assert summary["script_sha256"]
    assert "replay_intentcap_gateway.py" in command
