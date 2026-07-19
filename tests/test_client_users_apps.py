import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_list_users_returns_users_with_devices_and_rules():
    route = respx.get("https://example.firewalla.net/v2/users").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": "box-1:29",
                    "name": "Matt",
                    "affiliatedTag": "28",
                    "devices": ["AA:BB:CC:DD:EE:FF"],
                    "rules": ["box-1:1846"],
                },
                {"id": "box-1:31", "name": "Laura", "affiliatedTag": "30"},
            ],
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    users = client.list_users()

    assert route.called
    assert [u["name"] for u in users] == ["Matt", "Laura"]
    # affiliatedTag is the device-group id rules are scoped to.
    assert users[0]["affiliatedTag"] == "28"


@respx.mock
def test_list_apps_returns_blockable_apps():
    route = respx.get("https://example.firewalla.net/v2/apps").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "youtube", "name": "YouTube", "disabled": False},
                {"id": "netflix", "name": "Netflix", "disabled": False},
            ],
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    apps = client.list_apps()

    assert route.called
    assert [a["id"] for a in apps] == ["youtube", "netflix"]
