import importlib.util
import sys
from pathlib import Path

from intentcap.live_gateway import LiveToolGateway


def _load_runner():
    path = Path(__file__).parents[1] / "scripts" / "run_tau2_reference_actions_live_gateway.py"
    spec = importlib.util.spec_from_file_location("run_tau2_reference_actions_live_gateway", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeToolkit:
    def __init__(self):
        self.tasks = {}
        self.calls = []

    def has_tool(self, name):
        return name in {"create_task", "update_task_status", "get_users"}

    def tool_mutates_state(self, name):
        return name != "get_users"

    def update_db(self, update_data):
        self.tasks.update(update_data.get("tasks", {}))

    def use_tool(self, tool_name, **kwargs):
        return getattr(self, tool_name)(**kwargs)

    def create_task(self, user_id, title, description=None):
        task_id = f"task_{len(self.tasks) + 1}"
        task = {
            "task_id": task_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "status": "pending",
        }
        self.tasks[task_id] = task
        args = {"user_id": user_id, "title": title}
        self.calls.append(("create_task", args))
        return {"tool": "create_task", "args": args, "task": task}

    def update_task_status(self, task_id, status):
        self.tasks[task_id]["status"] = status
        self.calls.append(("update_task_status", {"task_id": task_id, "status": status}))
        return self.tasks[task_id]

    def get_users(self):
        self.calls.append(("get_users", {}))
        return []


def test_tau2_live_gateway_runner_builds_exact_event_leases_and_executes_registered_tool():
    runner = _load_runner()
    toolkit = FakeToolkit()
    runtime = runner.TaskRuntime(
        domain="mock",
        task_id="task_0",
        assistant_tools=toolkit,
        user_tools=None,
        initialization_events=0,
        initialization_errors=[],
    )
    runner._apply_initial_state(
        runtime,
        {
            "initialization_data": {
                "agent_data": {
                    "tasks": {
                        "task_1": {"task_id": "task_1", "status": "pending"},
                    }
                }
            },
            "message_history": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "name": "create_task",
                            "arguments": {
                                "user_id": "user_1",
                                "title": "From history",
                            },
                        }
                    ],
                }
            ],
        },
    )
    assert runtime.initialization_events == 2
    assert runtime.initialization_errors == []
    assert "task_2" in toolkit.tasks

    action = runner.ReferenceAction(
        event_id="mock:task_0:update_1",
        domain="mock",
        task_id="task_0",
        action_id="update_1",
        index=0,
        name="update_task_status",
        requestor="assistant",
        args={"task_id": "task_2", "status": "completed"},
        reward_basis=("DB",),
        object_name="tau2.mock.assistant.update_task_status",
    )
    trace = runner.build_trace([action])
    callable_invocations = []
    tools = runner.build_tool_registry([action], {action.event_id: runtime}, callable_invocations)
    gateway = LiveToolGateway(trace, tools)
    records = gateway.run_events()
    summary = runner.summarize(
        trace=trace,
        records=records,
        callable_invocations=callable_invocations,
        gateway_summary=gateway.summary(records),
        registered_tools=tools,
        actions=[action],
        runtimes={action.event_id: runtime},
        unsupported_rows=[],
        user_reference_actions=0,
        task_counts={"mock": 1},
    )

    assert records[0]["executed"] is True
    assert records[0]["error"] is None
    assert toolkit.tasks["task_2"]["status"] == "completed"
    assert callable_invocations == [
        {
            "event_id": "mock:task_0:update_1",
            "domain": "mock",
            "task_id": "task_0",
            "action_id": "update_1",
            "tool": "update_task_status",
            "object": "tau2.mock.assistant.update_task_status",
            "args": {"task_id": "task_2", "status": "completed"},
        }
    ]
    assert summary["assistant_reference_actions"] == 1
    assert summary["successful_tool_events"] == 1
    assert summary["executed_with_tool_error_events"] == 0
    assert summary["user_reference_actions_excluded_from_assistant_authority"] == 0


def test_tau2_live_gateway_runner_blocks_event_id_mismatch_before_callable_execution():
    runner = _load_runner()
    toolkit = FakeToolkit()
    runtime = runner.TaskRuntime(
        domain="mock",
        task_id="task_0",
        assistant_tools=toolkit,
        user_tools=None,
        initialization_events=0,
        initialization_errors=[],
    )
    action = runner.ReferenceAction(
        event_id="mock:task_0:create_1",
        domain="mock",
        task_id="task_0",
        action_id="create_1",
        index=0,
        name="create_task",
        requestor="assistant",
        args={"user_id": "user_1", "title": "Allowed"},
        reward_basis=("ACTION",),
        object_name="tau2.mock.assistant.create_task",
    )
    trace = runner.build_trace([action])
    trace["events"][0]["args"]["_intentcap_event_id"] = "mock:task_0:attacker"
    callable_invocations = []
    tools = runner.build_tool_registry([action], {action.event_id: runtime}, callable_invocations)

    records = LiveToolGateway(trace, tools).run_events()

    assert records[0]["executed"] is False
    assert records[0]["decision"]["reason"] == "no matching lease"
    assert callable_invocations == []
