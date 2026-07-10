import importlib.util
from pathlib import Path


def _load_auditor():
    path = Path(__file__).parents[1] / "scripts" / "audit_agentdojo_goal_inferred.py"
    spec = importlib.util.spec_from_file_location("audit_agentdojo_goal_inferred", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_agentdojo_audit_separates_ground_truth_from_inferred_events():
    auditor = _load_auditor()
    trace = {
        "events": [
            {
                "id": "injection_task_0:0:send_email",
                "object": "send_email",
                "mode": "sink_select",
                "decision": "send_email.sink",
                "intentcap_event_type": "ground_truth",
                "agentdojo": {"injection_task": "injection_task_0"},
            },
            {
                "id": "injection_task_6:goal:0:get_unread_emails",
                "object": "get_unread_emails",
                "mode": "authorize",
                "decision": "get_unread_emails.authority",
                "intentcap_event_type": "goal_inferred",
                "agentdojo": {
                    "injection_task": "injection_task_6",
                    "inference": {
                        "official_ground_truth": False,
                        "reason": "read all unread email bodies",
                    },
                },
            },
            {
                "id": "injection_task_6:goal:1:send_email",
                "object": "send_email",
                "mode": "sink_select",
                "decision": "send_email.sink",
                "intentcap_event_type": "goal_inferred",
                "agentdojo": {
                    "injection_task": "injection_task_6",
                    "inference": {
                        "official_ground_truth": False,
                        "reason": "exfiltrate unread email bodies",
                    },
                },
            },
        ]
    }
    verdicts = [
        {"event_id": "injection_task_0:0:send_email", "allowed": False},
        {"event_id": "injection_task_6:goal:0:get_unread_emails", "allowed": False},
        {"event_id": "injection_task_6:goal:1:send_email", "allowed": False},
    ]
    gateway_decisions = [
        {"event_id": "injection_task_0:0:send_email", "action": "block"},
        {"event_id": "injection_task_6:goal:0:get_unread_emails", "action": "block"},
        {"event_id": "injection_task_6:goal:1:send_email", "action": "block"},
    ]

    task_audit, summary = auditor.audit_trace(
        trace,
        verdicts=verdicts,
        gateway_decisions=gateway_decisions,
    )

    assert [task["task_id"] for task in task_audit] == ["injection_task_0", "injection_task_6"]
    assert task_audit[0]["oracle_source"] == "benchmark_ground_truth"
    assert task_audit[0]["audit_status"] == "official_ground_truth_replay"
    assert task_audit[0]["paper_use"] == "paper-ready benchmark trajectory event"
    assert task_audit[1]["oracle_source"] == "adapter_goal_inference"
    assert task_audit[1]["audit_status"] == "goal_inferred_needs_review"
    assert task_audit[1]["paper_use"] == "adapter-only coverage; do not report as benchmark trajectory"
    assert task_audit[1]["mode_counts"] == {"authorize": 1, "sink_select": 1}
    assert task_audit[1]["events"][0]["inference_reason"] == "read all unread email bodies"

    assert summary["total_tasks"] == 2
    assert summary["tasks_with_ground_truth"] == 1
    assert summary["tasks_with_goal_inferred"] == 1
    assert summary["total_events"] == 3
    assert summary["official_ground_truth_events"] == 1
    assert summary["goal_inferred_events"] == 2
    assert summary["unknown_events"] == 0
    assert summary["paper_ready_trajectory_events"] == 1
    assert summary["adapter_only_events"] == 2
    assert summary["checker_denied_events"] == 3
    assert summary["gateway_blocked_events"] == 3
    assert summary["audit_verdict"] == "warn"
