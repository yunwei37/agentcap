"""Probe local llama.cpp output-protocol controls over saved tau2 prompts.

This is a small fresh-model diagnostic for the benchmark utility gate. It reads
saved R340 task-loop prompts and asks whether llama.cpp controls such as JSON
schema constrained decoding and reasoning-off flags reduce the protocol failures
identified by R344. It does not execute tau2 tools, replay traces, sync datasets,
or change leases.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_tau2_local_llm_task_gateway import (  # noqa: E402
    normalize_model_calls,
    parse_model_json,
)


DEFAULT_INPUT_DIR = Path("results/eval/R340RETAILCOMPILERFEEDBACK5")
DEFAULT_LLAMA_COMPLETION = Path(
    "/home/yunwei37/workspace/llama.cpp-latest/build/bin/llama-completion"
)
DEFAULT_LLAMA_CLI = Path("/home/yunwei37/workspace/llama.cpp-latest/build/bin/llama-cli")
DEFAULT_MODEL = Path(
    "/home/yunwei37/.cache/huggingface/hub/"
    "models--DevQuasar--Qwen.Qwen3.6-27B-GGUF/snapshots/"
    "b19fa7e8538a1a5f66452eb3b3167e026177be1d/"
    "Qwen.Qwen3.6-27B.f16.gguf.Q4_K_M.gguf"
)
ROW_FIELDS = [
    "mode",
    "prompt_path",
    "raw_output_path",
    "returncode",
    "latency_seconds",
    "stdout_chars",
    "stderr_chars",
    "empty_stdout",
    "contains_think",
    "contains_output_json_fence",
    "has_end_marker",
    "parsed_json",
    "parsed_calls",
    "mentions_actions",
    "mentions_tool",
    "likely_truncated",
]
MODE_FIELDS = [
    "mode",
    "prompts",
    "returncode_zero",
    "empty_stdout",
    "contains_think",
    "parsed_json",
    "parsed_calls_outputs",
    "likely_truncated",
    "avg_latency_seconds",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--llama-completion-bin", type=Path, default=DEFAULT_LLAMA_COMPLETION)
    parser.add_argument("--llama-cli-bin", type=Path, default=DEFAULT_LLAMA_CLI)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--prompt-glob", default="step_prompts/*.txt")
    parser.add_argument("--max-prompts", type=int, default=1)
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["completion", "completion_schema_reasoning_off"],
        choices=["completion", "completion_schema_reasoning_off", "cli_schema_reasoning_off"],
    )
    parser.add_argument("--n-predict", type=int, default=256)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--gpu-layers", type=int, default=48)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    summary = run_probe(
        run_id=args.run_id,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        llama_completion_bin=args.llama_completion_bin,
        llama_cli_bin=args.llama_cli_bin,
        model=args.model,
        prompt_glob=args.prompt_glob,
        max_prompts=args.max_prompts,
        modes=tuple(args.modes),
        n_predict=args.n_predict,
        ctx_size=args.ctx_size,
        gpu_layers=args.gpu_layers,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def run_probe(
    *,
    run_id: str,
    input_dir: Path,
    output_dir: Path,
    llama_completion_bin: Path,
    llama_cli_bin: Path,
    model: Path,
    prompt_glob: str,
    max_prompts: int,
    modes: tuple[str, ...],
    n_predict: int,
    ctx_size: int,
    gpu_layers: int,
    timeout_seconds: int,
    runner: Callable[[list[str], int], tuple[str, str, int, float]] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pre_run_git_status = _git(["status", "--short"])
    raw_dir = output_dir / "raw_outputs"
    raw_dir.mkdir(exist_ok=True)
    schema_path = output_dir / "actions_schema.json"
    schema_path.write_text(json.dumps(actions_schema(), indent=2, sort_keys=True))

    prompts = sorted(input_dir.glob(prompt_glob))[:max_prompts]
    if not prompts:
        raise FileNotFoundError(f"no prompts match {input_dir / prompt_glob}")

    runner = runner or _run_command
    rows: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    for mode in modes:
        for prompt_path in prompts:
            command = command_for_mode(
                mode=mode,
                llama_completion_bin=llama_completion_bin,
                llama_cli_bin=llama_cli_bin,
                model=model,
                prompt_path=prompt_path,
                schema_path=schema_path,
                n_predict=n_predict,
                ctx_size=ctx_size,
                gpu_layers=gpu_layers,
            )
            stdout, stderr, returncode, latency = runner(command, timeout_seconds)
            raw_path = raw_dir / f"{mode}_{prompt_path.stem}.txt"
            raw_path.write_text(_raw_payload(stdout, stderr, returncode))
            row = analyze_output(
                mode=mode,
                prompt_path=prompt_path,
                raw_path=raw_path,
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
                latency=latency,
            )
            rows.append(row)
            commands.append(
                {
                    "mode": mode,
                    "prompt_path": str(prompt_path),
                    "command": command,
                    "timeout_seconds": timeout_seconds,
                }
            )

    mode_rows = summarize_modes(rows)
    summary = build_summary(
        run_id=run_id,
        input_dir=input_dir,
        output_dir=output_dir,
        prompt_glob=prompt_glob,
        prompts=prompts,
        modes=modes,
        rows=rows,
        mode_rows=mode_rows,
        model=model,
        n_predict=n_predict,
        ctx_size=ctx_size,
        gpu_layers=gpu_layers,
        git_status=pre_run_git_status,
    )
    _write_csv(output_dir / "protocol_control_rows.csv", ROW_FIELDS, rows)
    _write_csv(output_dir / "protocol_control_mode_summary.csv", MODE_FIELDS, mode_rows)
    _write_csv(
        output_dir / "input_digests.csv",
        ["path", "bytes", "sha256"],
        [_digest_row(path) for path in prompts] + [_digest_row(schema_path)],
    )
    (output_dir / "commands.json").write_text(json.dumps(commands, indent=2, sort_keys=True))
    (output_dir / "protocol_control_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    (output_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    return summary


def actions_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["actions"],
        "properties": {
            "actions": {
                "type": "array",
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["tool", "arguments"],
                    "properties": {
                        "tool": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                },
            }
        },
    }


def command_for_mode(
    *,
    mode: str,
    llama_completion_bin: Path,
    llama_cli_bin: Path,
    model: Path,
    prompt_path: Path,
    schema_path: Path,
    n_predict: int,
    ctx_size: int,
    gpu_layers: int,
) -> list[str]:
    binary = llama_cli_bin if mode == "cli_schema_reasoning_off" else llama_completion_bin
    command = [
        str(binary),
        "-m",
        str(model),
        "-f",
        str(prompt_path),
        "-n",
        str(n_predict),
        "-c",
        str(ctx_size),
        "-ngl",
        str(gpu_layers),
        "--temp",
        "0",
        "--seed",
        "0",
        "--no-display-prompt",
        "--no-warmup",
    ]
    if mode in {"completion_schema_reasoning_off", "cli_schema_reasoning_off"}:
        command.extend(
            [
                "--json-schema-file",
                str(schema_path),
                "--reasoning",
                "off",
                "--reasoning-budget",
                "0",
            ]
        )
    if mode != "cli_schema_reasoning_off":
        command.append("--single-turn")
    return command


def analyze_output(
    *,
    mode: str,
    prompt_path: Path,
    raw_path: Path,
    stdout: str,
    stderr: str,
    returncode: int,
    latency: float,
) -> dict[str, Any]:
    parsed = parse_model_json(stdout)
    calls = normalize_model_calls(parsed)
    mentions_actions = '"actions"' in stdout or "'actions'" in stdout
    mentions_tool = '"tool"' in stdout or "'tool'" in stdout
    has_end_marker = "[end of text]" in stdout
    likely_truncated = bool(stdout) and not has_end_marker and (
        parsed is None or mentions_actions or mentions_tool
    )
    return {
        "mode": mode,
        "prompt_path": str(prompt_path),
        "raw_output_path": str(raw_path),
        "returncode": returncode,
        "latency_seconds": round(latency, 6),
        "stdout_chars": len(stdout),
        "stderr_chars": len(stderr),
        "empty_stdout": not bool(stdout),
        "contains_think": "<think>" in stdout,
        "contains_output_json_fence": "```json" in stdout,
        "has_end_marker": has_end_marker,
        "parsed_json": parsed is not None,
        "parsed_calls": len(calls),
        "mentions_actions": mentions_actions,
        "mentions_tool": mentions_tool,
        "likely_truncated": likely_truncated,
    }


def summarize_modes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_mode: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_mode.setdefault(str(row["mode"]), []).append(row)
    for mode, mode_rows in sorted(by_mode.items()):
        latencies = [float(row["latency_seconds"]) for row in mode_rows]
        out.append(
            {
                "mode": mode,
                "prompts": len(mode_rows),
                "returncode_zero": sum(1 for row in mode_rows if int(row["returncode"]) == 0),
                "empty_stdout": sum(1 for row in mode_rows if row["empty_stdout"]),
                "contains_think": sum(1 for row in mode_rows if row["contains_think"]),
                "parsed_json": sum(1 for row in mode_rows if row["parsed_json"]),
                "parsed_calls_outputs": sum(1 for row in mode_rows if int(row["parsed_calls"]) > 0),
                "likely_truncated": sum(1 for row in mode_rows if row["likely_truncated"]),
                "avg_latency_seconds": round(sum(latencies) / len(latencies), 6)
                if latencies
                else 0.0,
            }
        )
    return out


def build_summary(
    *,
    run_id: str,
    input_dir: Path,
    output_dir: Path,
    prompt_glob: str,
    prompts: list[Path],
    modes: tuple[str, ...],
    rows: list[dict[str, Any]],
    mode_rows: list[dict[str, Any]],
    model: Path,
    n_predict: int,
    ctx_size: int,
    gpu_layers: int,
    git_status: str,
) -> dict[str, Any]:
    row_counts = Counter(str(row["mode"]) for row in rows)
    constrained = [
        row
        for row in mode_rows
        if row["mode"] in {"completion_schema_reasoning_off", "cli_schema_reasoning_off"}
    ]
    best_constrained = min(
        constrained,
        key=lambda row: (
            int(row["contains_think"]),
            int(row["likely_truncated"]),
            -int(row["parsed_json"]),
            -int(row["parsed_calls_outputs"]),
        ),
        default=None,
    )
    return {
        "run_id": run_id,
        "analysis": "fresh local llama.cpp protocol-control probe over saved R340 prompts",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "prompt_glob": prompt_glob,
        "prompts": len(prompts),
        "modes": list(modes),
        "rows": len(rows),
        "rows_by_mode": dict(sorted(row_counts.items())),
        "mode_summary": mode_rows,
        "best_constrained_mode": best_constrained["mode"] if best_constrained else "",
        "protocol_control_status": _status(mode_rows),
        "model": str(model),
        "model_exists": model.exists(),
        "model_bytes": model.stat().st_size if model.exists() else 0,
        "n_predict": n_predict,
        "ctx_size": ctx_size,
        "gpu_layers": gpu_layers,
        "no_dataset_sync": True,
        "not_a_task_utility_run": True,
        "not_a_tool_execution": True,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "project_head": _git(["rev-parse", "HEAD"]),
        "git_status": git_status,
    }


def _status(mode_rows: list[dict[str, Any]]) -> str:
    baseline = next((row for row in mode_rows if row["mode"] == "completion"), None)
    constrained = [
        row
        for row in mode_rows
        if row["mode"] in {"completion_schema_reasoning_off", "cli_schema_reasoning_off"}
    ]
    if not baseline or not constrained:
        return "measured"
    best = min(
        constrained,
        key=lambda row: (
            int(row["contains_think"]),
            int(row["likely_truncated"]),
            -int(row["parsed_json"]),
            -int(row["parsed_calls_outputs"]),
        ),
    )
    improved = (
        int(best["contains_think"]) < int(baseline["contains_think"])
        or int(best["likely_truncated"]) < int(baseline["likely_truncated"])
        or int(best["parsed_json"]) > int(baseline["parsed_json"])
        or int(best["parsed_calls_outputs"]) > int(baseline["parsed_calls_outputs"])
    )
    return "schema_reasoning_control_improved" if improved else "schema_reasoning_control_not_enough"


def _run_command(command: list[str], timeout_seconds: int) -> tuple[str, str, int, float]:
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
        return completed.stdout, completed.stderr, completed.returncode, time.monotonic() - start
    except subprocess.TimeoutExpired as exc:
        return (
            exc.stdout or "",
            exc.stderr or f"timeout after {timeout_seconds}s",
            124,
            time.monotonic() - start,
        )


def _raw_payload(stdout: str, stderr: str, returncode: int) -> str:
    return (
        "STDOUT:\n"
        f"{stdout}\n"
        "STDERR:\n"
        f"{stderr}\n"
        f"RETURNCODE: {returncode}\n"
    )


def _digest_row(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
