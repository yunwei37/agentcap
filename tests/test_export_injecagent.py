import importlib.util
from pathlib import Path


def _load_exporter():
    path = Path(__file__).parents[1] / "scripts" / "export_injecagent_intentcap.py"
    spec = importlib.util.spec_from_file_location("export_injecagent_intentcap", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_injecagent_classifies_email_as_sink_selection():
    exporter = _load_exporter()

    decision, mode = exporter._classify_attacker_tool(
        "GmailSendEmail",
        "Physical Data",
        "data_stealing",
    )

    assert decision == "GmailSendEmail.sink"
    assert mode == "sink_select"


def test_injecagent_classifies_direct_harm_as_authorize():
    exporter = _load_exporter()

    decision, mode = exporter._classify_attacker_tool(
        "AugustSmartLockUnlockDoor",
        "Physical Harm",
        "direct_harm",
    )

    assert decision == "AugustSmartLockUnlockDoor.authority"
    assert mode == "authorize"
