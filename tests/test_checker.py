import json
from pathlib import Path

from intentcap.checker import check_trace


def test_local_pdf_wrong_sink_trace():
    trace_path = Path(__file__).parents[1] / "examples" / "local_pdf_wrong_sink.json"
    verdicts = {v["event_id"]: v for v in check_trace(json.loads(trace_path.read_text()))}

    assert verdicts["pdf_to_xlsx_cells"]["allowed"]
    assert verdicts["user_selected_repo_issue"]["allowed"]
    assert not verdicts["pdf_injected_repo_issue"]["allowed"]
    assert verdicts["pdf_injected_repo_issue"]["reason"] == "no matching lease"


def test_context_lacking_influence_mode_is_denied():
    trace = {
        "labels": {
            "uploaded_pdf_text": {
                "allowed": {
                    "summarize": ["github.issue_body"],
                }
            }
        },
        "leases": [
            {
                "id": "overbroad_repo_lease",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": {"equals": "org/repo-x"}},
                "control_may_depend_on": ["uploaded_pdf_text"],
                "data_may_depend_on": ["uploaded_pdf_text"],
            }
        ],
        "events": [
            {
                "id": "pdf_controls_repo",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo-x"},
                "decision": "github.repo",
                "mode": "sink_select",
                "control_provenance": ["uploaded_pdf_text"],
                "data_provenance": ["uploaded_pdf_text"],
            }
        ],
    }

    verdict = check_trace(trace)[0]
    assert not verdict["allowed"]
    assert "lacks influence mode" in verdict["reason"]


def test_trace_level_temporal_and_budget_conditions_are_enforced():
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "sink_select": ["repo"],
                }
            }
        },
        "leases": [
            {
                "id": "after_review",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": {"equals": "org/repo-x"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
                "temporal": {"after": ["review_complete"]},
            },
            {
                "id": "once",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": {"equals": "org/repo-y"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
                "budget": {"invocations": 1},
            },
        ],
        "events": [
            {
                "id": "too_early",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo-x"},
                "decision": "repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "first",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo-y"},
                "decision": "repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "second",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo-y"},
                "decision": "repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
        ],
    }

    too_early, first, second = check_trace(trace)

    assert not too_early["allowed"]
    assert "temporal prerequisites" in too_early["reason"]
    assert first["allowed"]
    assert not second["allowed"]
    assert "invocation budget exhausted" in second["reason"]


def test_holder_delegation_and_intent_proofs_are_enforced():
    trace = {
        "labels": {
            "trusted_user": {
                "allowed": {
                    "delegate": ["subagent.capabilities"],
                    "sink_select": ["repo"],
                    "tool_select": ["extract"],
                }
            }
        },
        "leases": [
            {
                "id": "holder",
                "holder": "pdf_skill",
                "op": "exec.run",
                "object": "/skills/pdf/extract.py",
                "args": {},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
            },
            {
                "id": "delegate",
                "op": "subagent.spawn",
                "object": "summarizer",
                "args": {},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
                "delegation": {
                    "capabilities": [
                        {"op": "ctx.use", "object": "table", "mode": "summarize"}
                    ]
                },
            },
            {
                "id": "intent",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": {"equals": "org/repo-x"}},
                "control_may_depend_on": ["trusted_user"],
                "data_may_depend_on": ["trusted_user"],
                "intent": {
                    "must_derive_from": "trusted_repo_selection",
                    "requires_approval": "fresh_issue_approval",
                },
            },
        ],
        "events": [
            {
                "id": "wrong_holder",
                "holder": "github_mcp",
                "op": "exec.run",
                "object": "/skills/pdf/extract.py",
                "args": {},
                "decision": "extract",
                "mode": "tool_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "over_delegated",
                "op": "subagent.spawn",
                "object": "summarizer",
                "args": {
                    "capabilities": [
                        {"op": "mcp.call", "object": "github.create_issue", "mode": "sink_select"}
                    ]
                },
                "decision": "subagent.capabilities",
                "mode": "delegate",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
            },
            {
                "id": "missing_proof",
                "op": "mcp.call",
                "object": "github.create_issue",
                "args": {"repo": "org/repo-x"},
                "decision": "repo",
                "mode": "sink_select",
                "control_provenance": ["trusted_user"],
                "data_provenance": ["trusted_user"],
                "proof": {"intent_sources": ["trusted_user"], "approvals": []},
            },
        ],
    }

    wrong_holder, over_delegated, missing_proof = check_trace(trace)

    assert not wrong_holder["allowed"]
    assert "does not match lease holder" in wrong_holder["reason"]
    assert not over_delegated["allowed"]
    assert "exceeds lease attenuation" in over_delegated["reason"]
    assert not missing_proof["allowed"]
    assert "missing intent derivation proof" in missing_proof["reason"]
