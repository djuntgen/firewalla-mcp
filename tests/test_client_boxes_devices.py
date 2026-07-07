import httpx
import pytest
import respx

from firewalla_mcp.client import FirewallaClient, FirewallaNotFoundError


@respx.mock
def test_list_boxes_no_params():
    route = respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(200, json=[{"gid": "box-1"}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    boxes = client.list_boxes()

    assert route.called
    assert boxes == [{"gid": "box-1"}]


@respx.mock
def test_list_boxes_with_group_param():
    route = respx.get(
        "https://example.firewalla.net/v2/boxes", params={"group": "g1"}
    ).mock(return_value=httpx.Response(200, json=[]))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.list_boxes(group="g1")

    assert route.called


@respx.mock
def test_get_box_found():
    respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(200, json=[{"gid": "box-1"}, {"gid": "box-2"}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    box = client.get_box("box-2")

    assert box == {"gid": "box-2"}


@respx.mock
def test_get_box_not_found_raises():
    respx.get("https://example.firewalla.net/v2/boxes").mock(
        return_value=httpx.Response(200, json=[{"gid": "box-1"}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    with pytest.raises(FirewallaNotFoundError):
        client.get_box("does-not-exist")


@respx.mock
def test_list_devices_no_params():
    route = respx.get("https://example.firewalla.net/v2/devices").mock(
        return_value=httpx.Response(200, json=[{"id": "aa:bb"}])
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    devices = client.list_devices()

    assert route.called
    assert devices == [{"id": "aa:bb"}]


@respx.mock
def test_list_devices_with_box_and_group():
    route = respx.get(
        "https://example.firewalla.net/v2/devices",
        params={"box": "box-1", "group": "g1"},
    ).mock(return_value=httpx.Response(200, json=[]))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.list_devices(box="box-1", group="g1")

    assert route.called
