import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_get_simple_stats_no_group():
    route = respx.get("https://example.firewalla.net/v2/stats/simple").mock(
        return_value=httpx.Response(
            200, json={"onlineBoxes": 1, "offlineBoxes": 0, "alarms": 4, "rules": 12}
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.get_simple_stats()

    assert route.called
    assert result["onlineBoxes"] == 1


@respx.mock
def test_get_simple_stats_with_group():
    route = respx.get(
        "https://example.firewalla.net/v2/stats/simple", params={"group": "g1"}
    ).mock(return_value=httpx.Response(200, json={}))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.get_simple_stats(group="g1")

    assert route.called


@respx.mock
def test_get_stats_type_in_path_with_limit():
    route = respx.get(
        "https://example.firewalla.net/v2/stats/topBoxesByBlockedFlows",
        params={"limit": "3"},
    ).mock(
        return_value=httpx.Response(
            200, json=[{"meta": {"gid": "b1", "name": "Home", "model": "gold"}, "value": 9}]
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.get_stats("topBoxesByBlockedFlows", limit=3)

    assert route.called
    assert result[0]["value"] == 9


@respx.mock
def test_get_stats_with_group():
    route = respx.get(
        "https://example.firewalla.net/v2/stats/topBoxesBySecurityAlarms",
        params={"group": "g1"},
    ).mock(return_value=httpx.Response(200, json=[]))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.get_stats("topBoxesBySecurityAlarms", group="g1")

    assert route.called
