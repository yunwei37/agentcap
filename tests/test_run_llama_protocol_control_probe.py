import json

from scripts import run_llama_protocol_control_probe as probe


def test_protocol_control_probe_compares_completion_and_schema_modes(tmp_path):
    input_dir = tmp_path / "R340"
    prompt_dir = input_dir / "step_prompts"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "retail_0_step_1.txt").write_text("Return actions JSON only.\n")

    seen_commands = []

    def fake_runner(command, timeout_seconds):
        seen_commands.append(command)
        if "--json-schema-file" in command:
            schema_path = command[command.index("--json-schema-file") + 1]
            schema = json.loads(open(schema_path, encoding="utf-8").read())
            assert schema["required"] == ["actions"]
            assert "--reasoning" in command
            assert "off" in command
            return ('{"actions":[{"tool":"get_order_details","arguments":{"order_id":"#1"}}]}', "", 0, 2.0)
        return ('<think>reasoning</think>\n{"actions":', "", 0, 1.0)

    summary = probe.run_probe(
        run_id="T346",
        input_dir=input_dir,
        output_dir=tmp_path / "out",
        llama_completion_bin=tmp_path / "llama-completion",
        llama_cli_bin=tmp_path / "llama-cli",
        model=tmp_path / "model.gguf",
        prompt_glob="step_prompts/*.txt",
        max_prompts=1,
        modes=("completion", "completion_schema_reasoning_off"),
        n_predict=64,
        ctx_size=2048,
        gpu_layers=1,
        timeout_seconds=10,
        runner=fake_runner,
    )

    assert len(seen_commands) == 2
    assert summary["rows"] == 2
    assert summary["protocol_control_status"] == "schema_reasoning_control_improved"
    assert summary["mode_summary"][0]["contains_think"] == 1
    assert summary["mode_summary"][1]["contains_think"] == 0
    assert summary["mode_summary"][1]["parsed_calls_outputs"] == 1
    assert (tmp_path / "out" / "protocol_control_summary.json").exists()
    assert (tmp_path / "out" / "protocol_control_rows.csv").exists()


def test_cli_schema_mode_uses_llama_cli_without_single_turn(tmp_path):
    command = probe.command_for_mode(
        mode="cli_schema_reasoning_off",
        llama_completion_bin=tmp_path / "llama-completion",
        llama_cli_bin=tmp_path / "llama-cli",
        model=tmp_path / "model.gguf",
        prompt_path=tmp_path / "prompt.txt",
        schema_path=tmp_path / "schema.json",
        n_predict=32,
        ctx_size=1024,
        gpu_layers=8,
    )

    assert str(tmp_path / "llama-cli") == command[0]
    assert "--json-schema-file" in command
    assert "--reasoning" in command
    assert "--reasoning-budget" in command
    assert "--single-turn" not in command
