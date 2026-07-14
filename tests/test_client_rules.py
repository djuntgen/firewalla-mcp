import json

import httpx
import pytest
import respx

from firewalla_mcp.client import FirewallaClient, FirewallaNotFoundError


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


@respx.mock
def test_get_rule_finds_by_id():
    respx.get("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {"id": "rule-1", "action": "block"},
                    {"id": "rule-2", "action": "allow"},
                ],
            },
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    assert client.get_rule("rule-2") == {"id": "rule-2", "action": "allow"}


@respx.mock
def test_get_rule_raises_when_missing():
    respx.get("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(200, json={"count": 0, "results": []})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaNotFoundError, match="rule-9"):
        client.get_rule("rule-9")


@respx.mock
def test_update_rule_creates_replacement_then_deletes_original():
    existing = {
        "id": "rule-1",
        "action": "block",
        "direction": "bidirection",
        "gid": "box-1",
        "target": {"type": "internet"},
        "scope": {"type": "user", "value": "box-1:29"},
        "schedule": {"cronTime": "0 0 * * *", "duration": 86390},
        "status": "active",
        "ts": 1783560358.0,
        "updateTs": 1783654584.2,
        "hit": {"count": 42},
    }
    respx.get("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(200, json={"count": 1, "results": [existing]})
    )
    create = respx.post("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(200, json={"id": "rule-99", "action": "block"})
    )
    delete = respx.delete("https://example.firewalla.net/v2/rules/rule-1").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.update_rule(
        "rule-1", {"schedule": {"cronTime": "0 17 * * *", "duration": 57600}}
    )

    # New rule created before original deleted (so the rule is never lost).
    assert create.called and delete.called
    posted = json.loads(create.calls.last.request.content)
    # Server-managed fields are stripped from the recreate body.
    for stripped in ("id", "ts", "updateTs", "hit"):
        assert stripped not in posted
    # Canonical fields carried over, and the change applied.
    assert posted["action"] == "block"
    assert posted["scope"] == {"type": "user", "value": "box-1:29"}
    assert posted["target"] == {"type": "internet"}
    assert posted["schedule"] == {"cronTime": "0 17 * * *", "duration": 57600}
    assert result == {
        "deleted_id": "rule-1",
        "rule": {"id": "rule-99", "action": "block"},
    }


@respx.mock
def test_update_rule_does_not_delete_when_create_fails():
    existing = {"id": "rule-1", "action": "block", "target": {"type": "internet"}}
    respx.get("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(200, json={"count": 1, "results": [existing]})
    )
    respx.post("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(400, text="bad rule")
    )
    delete = respx.delete("https://example.firewalla.net/v2/rules/rule-1").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(Exception):
        client.update_rule("rule-1", {"notes": "x"})

    # Original must survive a failed replacement.
    assert not delete.called
