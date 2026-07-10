from pathlib import Path

import scripts.run_mcp_broker_probe as probe


def test_mcp_broker_probe_blocks_jsonrpc_tool_surface_attacks(tmp_path):
    repo = Path(__file__).parents[1]
    result = probe.run_probe(
        suite_path=repo / "examples" / "mcp_broker_jsonrpc_suite.json",
        output_dir=tmp_path / "R301MCPBROKER",
        run_id="TESTMCPBROKER",
    )
    summary = result["summary"]

    assert summary["run_id"] == "TESTMCPBROKER"
    assert summary["events"] == 6
    assert summary["server_tool_count"] == 3
    assert summary["tool_list_counts"]["intentcap_mcp_broker"] == 1
    assert summary["tool_list_counts"]["object_only_broker"] == 1
    assert summary["tool_list_counts"]["server_allowlist_broker"] == 3

    intentcap = summary["backends"]["intentcap_mcp_broker"]
    assert intentcap["events"] == 6
    assert intentcap["broker_allowed"] == 1
    assert intentcap["executed"] == 1
    assert intentcap["unsafe_executions"] == 0
    assert intentcap["blocked_unsafe_events"] == 5
    assert intentcap["checker_denied_events_executed"] == 0

    object_only = summary["backends"]["object_only_broker"]
    assert object_only["broker_allowed"] == 4
    assert object_only["executed"] == 4
    assert object_only["unsafe_executions"] == 3
    assert object_only["checker_denied_events_executed"] == 3
    assert object_only["unsafe_kind_counts"]["budget_reuse"] == 1
    assert object_only["unsafe_kind_counts"]["wrong_sink"] == 1
    assert object_only["unsafe_kind_counts"]["semantic_control"] == 1

    server_allowlist = summary["backends"]["server_allowlist_broker"]
    assert server_allowlist["broker_allowed"] == 6
    assert server_allowlist["executed"] == 6
    assert server_allowlist["unsafe_executions"] == 5
    assert server_allowlist["checker_denied_events_executed"] == 5
    assert server_allowlist["unsafe_kind_counts"]["tool_surface_expansion"] == 1
    assert server_allowlist["unsafe_kind_counts"]["approval_scope_inflation"] == 1

    rows = {
        (row["backend"], row["event_id"]): row
        for row in result["rows"]
    }
    assert rows[("intentcap_mcp_broker", "wrong_repo_from_pdf_text")]["executed"] is False
    assert rows[("object_only_broker", "wrong_repo_from_pdf_text")]["unsafe_execution"] is True
    assert rows[("server_allowlist_broker", "request_full_scope_from_tool_result")][
        "unsafe_execution"
    ] is True

    output_dir = tmp_path / "R301MCPBROKER"
    assert (output_dir / "mcp_broker_rows.csv").exists()
    assert (output_dir / "mcp_broker_summary.json").exists()
    assert (output_dir / "tool_lists.json").exists()
    assert (output_dir / "server_states.json").exists()
