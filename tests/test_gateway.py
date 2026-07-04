from intentcap.gateway import TraceGateway


def test_gateway_replays_allow_and_block_decisions():
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "sink_select": ["github.repo"],
                }
            },
            "untrusted_pdf": {
                "allowed": {
                    "summarize": ["github.issue_body"],
                }
            },
        },
        "leases": [
            {
                "id": "issue_repo",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": {"equals": "org/repo"}},
                "control_may_depend_on": ["trusted_user", "untrusted_pdf"],
                "data_may_depend_on": ["trusted_user", "untrusted_pdf"],
            }
        ],
        "events": [
            {
                "id": "trusted_repo",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo"},
                "decision": "github.repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "pdf_repo",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo"},
                "decision": "github.repo",
                "mode": "sink_select",
                "control_provenance": ["untrusted_pdf"],
                "data_provenance": ["untrusted_pdf"],
            },
        ],
    }

    gateway = TraceGateway(trace)
    decisions = gateway.replay()
    summary = gateway.summary(decisions)

    assert gateway.exposed_objects() == [{"op": "mcp.call", "object": "github.create_issue"}]
    assert [decision["action"] for decision in decisions] == ["execute", "block"]
    assert summary["attempted_events"] == 2
    assert summary["executed_events"] == 1
    assert summary["blocked_events"] == 1
    assert summary["blocked_mode_counts"] == {"sink_select": 1}


def test_gateway_replay_uses_trace_level_budget_state():
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "sink_select": ["github.repo"],
                }
            }
        },
        "leases": [
            {
                "id": "one_issue",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": {"equals": "org/repo"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
                "budget": {"invocations": 1},
            }
        ],
        "events": [
            {
                "id": "first",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo"},
                "decision": "github.repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "second",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo"},
                "decision": "github.repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
        ],
    }

    decisions = TraceGateway(trace).replay()

    assert [decision["action"] for decision in decisions] == ["execute", "block"]
    assert "invocation budget exhausted" in decisions[1]["reason"]
