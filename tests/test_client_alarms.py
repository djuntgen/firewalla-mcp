import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_list_alarms_default_params():
    route = respx.get(
        "https://example.firewalla.net/v2/alarms", params={"limit": "200"}
    ).mock(return_value=httpx.Response(200, json={"count": 0, "results": [], "next_cursor": None}))
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.list_alarms()

    assert route.called
    assert result == {"count": 0, "results": [], "next_cursor": None}


@respx.mock
def test_list_alarms_with_query_and_paging_params():
    route = respx.get(
        "https://example.firewalla.net/v2/alarms",
        params={
            "limit": "10",
            "query": "status:active box:box-1",
            "groupBy": "type",
            "sortBy": "ts:desc",
            "cursor": "abc",
        },
    ).mock(return_value=httpx.Response(200, json={"count": 0, "results": [], "next_cursor": None}))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.list_alarms(
        query="status:active box:box-1",
        group_by="type",
        sort_by="ts:desc",
        limit=10,
        cursor="abc",
    )

    assert route.called


@respx.mock
def test_get_alarm_path_params():
    route = respx.get("https://example.firewalla.net/v2/alarms/gid-1/aid-1").mock(
        return_value=httpx.Response(200, json={"aid": "aid-1"})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    alarm = client.get_alarm("gid-1", "aid-1")

    assert route.called
    assert alarm == {"aid": "aid-1"}


@respx.mock
def test_delete_alarm_path_params():
    route = respx.delete("https://example.firewalla.net/v2/alarms/gid-1/aid-1").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.delete_alarm("gid-1", "aid-1")

    assert route.called
