import httpx
import pytest
import respx

from firewalla_mcp.client import MAX_ATTEMPTS, FirewallaAPIError, FirewallaClient


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
