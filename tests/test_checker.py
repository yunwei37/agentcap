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
