import json

import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_list_rules_no_query():
    route = respx.get("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(200, json={"count": 0, "results": []})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.list_rules()

    assert route.called
    assert result == {"count": 0, "results": []}


@respx.mock
def test_list_rules_with_query():
    route = respx.get(
        "https://example.firewalla.net/v2/rules",
        params={"query": "status:paused action:allow"},
    ).mock(return_value=httpx.Response(200, json={"count": 0, "results": []}))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.list_rules(query="status:paused action:allow")

    assert route.called


@respx.mock
def test_create_rule_posts_json_body():
    route = respx.post("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(200, json={"id": "rule-1"})
    )
    client = FirewallaClient("example.firewalla.net", "tok")
    rule = {"action": "block", "target": {"type": "ip", "value": "1.2.3.4"}}

    result = client.create_rule(rule)

    assert route.called
    assert json.loads(route.calls.last.request.content) == rule
    assert result == {"id": "rule-1"}


@respx.mock
def test_pause_rule_posts_to_pause_path():
    route = respx.post("https://example.firewalla.net/v2/rules/rule-1/pause").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.pause_rule("rule-1")

    assert route.called


@respx.mock
def test_resume_rule_posts_to_resume_path():
    route = respx.post("https://example.firewalla.net/v2/rules/rule-1/resume").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.resume_rule("rule-1")

    assert route.called


@respx.mock
def test_delete_rule():
    route = respx.delete("https://example.firewalla.net/v2/rules/rule-1").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.delete_rule("rule-1")

    assert route.called
