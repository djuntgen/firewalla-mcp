import json

import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_list_target_lists_no_owner():
    route = respx.get("https://example.firewalla.net/v2/target-lists").mock(
        return_value=httpx.Response(200, json=[{"id": "tl-1"}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    lists = client.list_target_lists()

    assert route.called
    assert lists == [{"id": "tl-1"}]


@respx.mock
def test_list_target_lists_with_owner():
    route = respx.get(
        "https://example.firewalla.net/v2/target-lists", params={"owner": "box-1"}
    ).mock(return_value=httpx.Response(200, json=[]))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.list_target_lists(owner="box-1")

    assert route.called


@respx.mock
def test_get_target_list():
    route = respx.get("https://example.firewalla.net/v2/target-lists/tl-1").mock(
        return_value=httpx.Response(200, json={"id": "tl-1", "name": "My List"})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.get_target_list("tl-1")

    assert route.called
    assert result == {"id": "tl-1", "name": "My List"}


@respx.mock
def test_create_target_list_minimal():
    route = respx.post("https://example.firewalla.net/v2/target-lists").mock(
        return_value=httpx.Response(200, json={"id": "tl-1"})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.create_target_list("My List", ["1.2.3.4"])

    assert route.called
    assert json.loads(route.calls.last.request.content) == {
        "name": "My List",
        "targets": ["1.2.3.4"],
    }
    assert result == {"id": "tl-1"}


@respx.mock
def test_create_target_list_with_optional_fields():
    route = respx.post("https://example.firewalla.net/v2/target-lists").mock(
        return_value=httpx.Response(200, json={"id": "tl-1"})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.create_target_list(
        "My List", ["1.2.3.4"], owner="box-1", category="ad", notes="test"
    )

    assert json.loads(route.calls.last.request.content) == {
        "name": "My List",
        "targets": ["1.2.3.4"],
        "owner": "box-1",
        "category": "ad",
        "notes": "test",
    }


@respx.mock
def test_update_target_list_patches_json_body():
    route = respx.patch("https://example.firewalla.net/v2/target-lists/tl-1").mock(
        return_value=httpx.Response(200, json={"id": "tl-1", "name": "New Name"})
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.update_target_list("tl-1", name="New Name")

    assert route.called
    assert json.loads(route.calls.last.request.content) == {"name": "New Name"}
    assert result == {"id": "tl-1", "name": "New Name"}


@respx.mock
def test_delete_target_list():
    route = respx.delete("https://example.firewalla.net/v2/target-lists/tl-1").mock(
        return_value=httpx.Response(200)
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    client.delete_target_list("tl-1")

    assert route.called
