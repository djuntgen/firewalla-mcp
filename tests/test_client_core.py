import httpx
import pytest
import respx

from firewalla_mcp.client import (
    MAX_ATTEMPTS,
    MAX_ERROR_BODY_CHARS,
    MAX_RETRY_AFTER_SECONDS,
    FirewallaAPIError,
    FirewallaClient,
    FirewallaError,
    FirewallaNotFoundError,
)


@respx.mock
def test_get_success_returns_response():
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(200, json=[{"gid": "abc"}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    response = client._request("GET", "/boxes")

    assert route.called
    assert response.json() == [{"gid": "abc"}]


@respx.mock
def test_raises_immediately_on_400_no_retry():
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(400, text="bad request")
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError) as exc_info:
        client._request("GET", "/boxes")

    assert route.call_count == 1
    assert exc_info.value.status_code == 400


@respx.mock
def test_retries_on_500_then_succeeds(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        side_effect=[httpx.Response(500, text="boom"), httpx.Response(200, json=[])]
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    response = client._request("GET", "/boxes")

    assert response.status_code == 200
    assert route.call_count == 2


@respx.mock
def test_raises_after_max_attempts_on_persistent_500(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(500, text="boom")
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError) as exc_info:
        client._request("GET", "/boxes")

    assert route.call_count == MAX_ATTEMPTS
    assert exc_info.value.status_code == 500


@respx.mock
def test_retries_then_raises_on_connection_timeout(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError):
        client._request("GET", "/boxes")

    assert route.call_count == MAX_ATTEMPTS


@respx.mock
def test_create_is_not_retried_on_500(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.post("https://example.firewalla.net/v2/rules").mock(
        return_value=httpx.Response(500, text="boom")
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError):
        client.create_rule({"action": "block"})

    assert route.call_count == 1


@respx.mock
def test_create_is_not_retried_on_transport_error(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.post("https://example.firewalla.net/v2/target-lists").mock(
        side_effect=httpx.ReadTimeout("timed out")
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError):
        client.create_target_list("blocked", ["1.2.3.4"])

    assert route.call_count == 1


@respx.mock
def test_pause_rule_post_is_still_retried(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.post("https://example.firewalla.net/v2/rules/r1/pause").mock(
        side_effect=[httpx.Response(500, text="boom"), httpx.Response(200, json={})]
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.pause_rule("r1")

    assert route.call_count == 2


@respx.mock
def test_429_is_retried_honoring_retry_after(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", sleeps.append)
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        side_effect=[
            httpx.Response(429, text="rate limited", headers={"Retry-After": "3"}),
            httpx.Response(200, json=[]),
        ]
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    assert client.list_boxes() == []
    assert route.call_count == 2
    assert sleeps == [3.0]


@respx.mock
def test_429_retry_after_is_capped(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", sleeps.append)
    respx.get("https://example.firewalla.net/v2/boxes").mock(
        side_effect=[
            httpx.Response(429, text="rate limited", headers={"Retry-After": "3600"}),
            httpx.Response(200, json=[]),
        ]
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    assert client.list_boxes() == []
    assert sleeps == [float(MAX_RETRY_AFTER_SECONDS)]


@respx.mock
def test_429_on_create_is_retried(monkeypatch):
    monkeypatch.setattr("firewalla_mcp.client.time.sleep", lambda s: None)
    route = respx.post("https://example.firewalla.net/v2/rules").mock(
        side_effect=[
            httpx.Response(429, text="rate limited"),
            httpx.Response(200, json={"id": "r1"}),
        ]
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    assert client.create_rule({"action": "block"}) == {"id": "r1"}
    assert route.call_count == 2


@respx.mock
def test_error_body_is_truncated():
    respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(400, text="x" * 10_000)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError) as exc_info:
        client.list_boxes()

    assert len(exc_info.value.body) < MAX_ERROR_BODY_CHARS + 50
    assert "truncated" in exc_info.value.body


@respx.mock
def test_non_json_2xx_raises_readable_error():
    respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(200, text="<html>gateway error</html>")
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaAPIError, match="non-JSON"):
        client.list_boxes()


@respx.mock
def test_path_params_are_url_escaped():
    route = respx.delete("https://example.firewalla.net/v2/rules/abc%2F..%2Fpause").mock(
        return_value=httpx.Response(200, json={})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.delete_rule("abc/../pause")

    assert route.called


def test_exceptions_share_common_base():
    assert issubclass(FirewallaAPIError, FirewallaError)
    assert issubclass(FirewallaNotFoundError, FirewallaError)
