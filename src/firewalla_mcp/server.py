from mcp.server.fastmcp import FastMCP

from firewalla_mcp.client import FirewallaClient
from firewalla_mcp.config import get_msp_domain, get_timeout, get_token

mcp = FastMCP("firewalla")
_client: FirewallaClient | None = None


def get_client() -> FirewallaClient:
    global _client
    if _client is None:
        _client = FirewallaClient(get_msp_domain(), get_token(), timeout=get_timeout())
    return _client


@mcp.tool()
def list_boxes(group: str | None = None) -> list[dict]:
    """List all Firewalla boxes on this MSP account, optionally filtered by group ID."""
    return get_client().list_boxes(group=group)


@mcp.tool()
def get_box(gid: str) -> dict:
    """Get a single Firewalla box by its gid."""
    return get_client().get_box(gid)


@mcp.tool()
def list_devices(box: str | None = None, group: str | None = None) -> list[dict]:
    """List devices seen on the network, optionally filtered by box gid or group ID."""
    return get_client().list_devices(box=box, group=group)


@mcp.tool()
def list_alarms(
    query: str | None = None,
    group_by: str | None = None,
    sort_by: str | None = None,
    limit: int = 200,
    cursor: str | None = None,
) -> dict:
    """List alarms. `query` supports Firewalla's search syntax, e.g. 'status:active box:<gid> type:9'."""
    return get_client().list_alarms(
        query=query, group_by=group_by, sort_by=sort_by, limit=limit, cursor=cursor
    )


@mcp.tool()
def get_alarm(gid: str, aid: str) -> dict:
    """Get a single alarm by box gid and alarm id."""
    return get_client().get_alarm(gid, aid)


@mcp.tool()
def delete_alarm(gid: str, aid: str) -> str:
    """Delete an alarm by box gid and alarm id. This is irreversible."""
    get_client().delete_alarm(gid, aid)
    return f"Deleted alarm {aid} on box {gid}"


@mcp.tool()
def list_rules(query: str | None = None) -> dict:
    """List firewall rules. `query` supports Firewalla's search syntax, e.g. 'status:paused action:allow'."""
    return get_client().list_rules(query=query)


@mcp.tool()
def create_rule(rule: dict) -> dict:
    """Create a new firewall rule.

    `rule` is a Firewalla rule object. Required fields: `action` ('block' or 'allow')
    and `target` (e.g. {"type": "domain", "value": "example.com"} or
    {"type": "ip", "value": "1.2.3.4"}). Common optional fields: `direction`
    ('bidirection', 'inbound', or 'outbound'), `gid` (box to create the rule on),
    `scope` (e.g. {"type": "device", "value": "<device gid>"} to limit the rule to
    one device; omit for network-wide), `schedule`, and `notes`.

    Example: {"action": "block", "target": {"type": "domain", "value": "example.com"},
    "direction": "bidirection", "gid": "<box gid>"}
    """
    return get_client().create_rule(rule)


@mcp.tool()
def pause_rule(rule_id: str) -> str:
    """Pause an existing firewall rule by id."""
    get_client().pause_rule(rule_id)
    return f"Paused rule {rule_id}"


@mcp.tool()
def resume_rule(rule_id: str) -> str:
    """Resume a paused firewall rule by id."""
    get_client().resume_rule(rule_id)
    return f"Resumed rule {rule_id}"


@mcp.tool()
def delete_rule(rule_id: str) -> str:
    """Delete a firewall rule by id. This is irreversible — consider pause_rule to disable it reversibly."""
    get_client().delete_rule(rule_id)
    return f"Deleted rule {rule_id}"


@mcp.tool()
def list_flows(
    query: str | None = None,
    group_by: str | None = None,
    sort_by: str | None = None,
    limit: int = 200,
    cursor: str | None = None,
) -> dict:
    """List network flows. `query` supports time-range syntax, e.g. 'ts:<begin>-<end>'."""
    return get_client().list_flows(
        query=query, group_by=group_by, sort_by=sort_by, limit=limit, cursor=cursor
    )


@mcp.tool()
def list_target_lists(owner: str | None = None) -> list[dict]:
    """List target lists, optionally filtered by owner (a box gid; omit for global/Firewalla-managed lists)."""
    return get_client().list_target_lists(owner=owner)


@mcp.tool()
def get_target_list(list_id: str) -> dict:
    """Get a single target list by id."""
    return get_client().get_target_list(list_id)


@mcp.tool()
def create_target_list(
    name: str,
    targets: list[str],
    owner: str | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create a new target list of IPs/domains."""
    return get_client().create_target_list(
        name, targets, owner=owner, category=category, notes=notes
    )


@mcp.tool()
def update_target_list(
    list_id: str,
    name: str | None = None,
    targets: list[str] | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> dict:
    """Update mutable fields of an existing target list. Only non-null fields are sent."""
    fields = {
        k: v
        for k, v in {"name": name, "targets": targets, "category": category, "notes": notes}.items()
        if v is not None
    }
    return get_client().update_target_list(list_id, **fields)


@mcp.tool()
def delete_target_list(list_id: str) -> str:
    """Delete a target list by id. This is irreversible; rules referencing it lose their targets."""
    get_client().delete_target_list(list_id)
    return f"Deleted target list {list_id}"


@mcp.tool()
def get_flow_trends(group: str | None = None) -> list[dict]:
    """Get daily blocked-flow counts, optionally scoped to a box group."""
    return get_client().get_flow_trends(group=group)


@mcp.tool()
def get_alarm_trends(group: str | None = None) -> list[dict]:
    """Get daily alarm counts, optionally scoped to a box group."""
    return get_client().get_alarm_trends(group=group)


def main() -> None:
    # Validate configuration before serving so a misconfigured environment
    # fails at startup with a clear message, not at the first tool call.
    get_msp_domain()
    get_token()
    get_timeout()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
