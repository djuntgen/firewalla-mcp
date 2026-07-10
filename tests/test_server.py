import asyncio

import httpx
import pytest

from firewalla_mcp import server
from firewalla_mcp.server import mcp

EXPECTED_TOOL_NAMES = {
    "list_boxes",
    "get_box",
    "list_devices",
    "list_alarms",
    "get_alarm",
    "delete_alarm",
    "list_rules",
    "create_rule",
    "pause_rule",
    "resume_rule",
    "delete_rule",
    "list_flows",
    "list_target_lists",
    "get_target_list",
    "create_target_list",
    "update_target_list",
    "delete_target_list",
    "get_flow_trends",
    "get_alarm_trends",
}


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    tool_names = {t.name for t in tools}

    assert tool_names == EXPECTED_TOOL_NAMES


def test_main_fails_fast_on_missing_config(monkeypatch):
    monkeypatch.delenv("FIREWALLA_TOKEN", raising=False)
    monkeypatch.delenv("FIREWALLA_MSP_DOMAIN", raising=False)
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: pytest.fail("server must not start"))

    with pytest.raises(RuntimeError, match="FIREWALLA_"):
        server.main()


def test_main_starts_server_when_configured(monkeypatch):
    monkeypatch.setenv("FIREWALLA_TOKEN", "tok")
    monkeypatch.setenv("FIREWALLA_MSP_DOMAIN", "example.firewalla.net")
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))

    server.main()

    assert calls == [{"transport": "stdio"}]


def test_get_client_uses_configured_timeout(monkeypatch):
    monkeypatch.setenv("FIREWALLA_TOKEN", "tok")
    monkeypatch.setenv("FIREWALLA_MSP_DOMAIN", "example.firewalla.net")
    monkeypatch.setenv("FIREWALLA_TIMEOUT", "42")
    monkeypatch.setattr(server, "_client", None)

    client = server.get_client()

    assert client._http.timeout == httpx.Timeout(42.0)


def test_write_tool_docstrings_guide_the_llm():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}

    for name in ("delete_rule", "delete_alarm", "delete_target_list"):
        assert "irreversible" in tools[name].description.lower()
    assert '"target"' in tools["create_rule"].description
    assert '"action"' in tools["create_rule"].description
