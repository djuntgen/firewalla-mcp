import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_list_flows_default_params():
    route = respx.get(
        "https://example.firewalla.net/v2/flows", params={"limit": "200"}
    ).mock(
        return_value=httpx.Response(
            200, json={"count": 0, "results": [], "next_cursor": None}
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.list_flows()

    assert route.called
    assert result == {"count": 0, "results": [], "next_cursor": None}


@respx.mock
def test_list_flows_with_query_and_grouping():
    route = respx.get(
        "https://example.firewalla.net/v2/flows",
        params={
            "limit": "5",
            "query": "ts:1000-2000",
            "groupBy": "device",
            "sortBy": "total:desc",
        },
    ).mock(
        return_value=httpx.Response(
            200, json={"count": 0, "results": [], "next_cursor": None}
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.list_flows(
        query="ts:1000-2000", group_by="device", sort_by="total:desc", limit=5
    )

    assert route.called


@respx.mock
def test_get_flow_trends_no_group():
    route = respx.get("https://example.firewalla.net/v2/trends/flows").mock(
        return_value=httpx.Response(200, json=[{"date": "2026-07-01", "value": 3}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    trends = client.get_flow_trends()

    assert route.called
    assert trends == [{"date": "2026-07-01", "value": 3}]


@respx.mock
def test_get_alarm_trends_with_group():
    route = respx.get(
        "https://example.firewalla.net/v2/trends/alarms", params={"group": "g1"}
    ).mock(return_value=httpx.Response(200, json=[]))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.get_alarm_trends(group="g1")

    assert route.called
