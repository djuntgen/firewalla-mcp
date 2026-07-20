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
def list_users() -> list[dict]:
    """List the people configured on this MSP account (Firewalla "users").

    Use this to resolve a person's name to the things rules attach to. Each user
    has `name`, `affiliatedTag` (the device-GROUP id that rules are scoped to —
    e.g. scope {"type": "group", "value": "<affiliatedTag>"}), `devices` (their
    device ids), and `rules` (ids of rules already applying to them). This is the
    reliable way to answer "what rules apply to <person>" instead of guessing a
    group from device names.
    """
    return get_client().list_users()


@mcp.tool()
def list_apps() -> list[dict]:
    """List the applications this box can target in rules.

    The set is small and fixed — only these `id` values are valid as
    {"type": "app", "value": "<id>"} in a rule target. Check here before
    creating an app rule; unsupported services (e.g. most streaming platforms)
    must be blocked another way, such as an `internet` target.
    """
    return get_client().list_apps()


@mcp.tool()
def update_device(gid: str, device_id: str, name: str) -> dict:
    """Rename a device. `name` is the ONLY field the API can change (max 32
    chars; no block/pause via API). `gid` is the box id; `device_id` is a
    device `id` from list_devices."""
    return get_client().update_device(gid, device_id, name)


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
def mute_alarm(
    gid: str,
    aid: str,
    target_type: str = "alarmType",
    target_value: str | None = None,
    scope_type: str = "all",
    scope_value: str | None = None,
) -> str:
    """Mute an alarm: archives it AND tells the box to create a silence
    exception, so future traffic matching it stops raising new alarms.

    This is broader than it looks — the DEFAULTS silence this alarm's entire
    type across the whole network. Narrow it deliberately:
    `target_type`: 'alarmType' (no value — silences every alarm of this type) or
    'domain' (target_value = the domain, silences just that domain).
    `scope_type`: 'all' (network-wide) or 'device' (scope_value = device MAC).

    Use archive_alarm instead to dismiss one alarm without silencing future ones."""
    get_client().mute_alarm(
        gid,
        aid,
        target_type=target_type,
        target_value=target_value,
        scope_type=scope_type,
        scope_value=scope_value,
    )
    return f"Muted alarm {aid} on box {gid} (target={target_type}, scope={scope_type})"


@mcp.tool()
def archive_alarm(gid: str, aid: str) -> str:
    """Archive an alarm: dismiss it from the active list but KEEP the record
    (unlike delete_alarm, which is irreversible).

    Unlike mute_alarm, this does NOT stop matching traffic from raising new
    alarms later — it only clears this one."""
    get_client().archive_alarm(gid, aid)
    return f"Archived alarm {aid} on box {gid}"


@mcp.tool()
def list_rules(query: str | None = None) -> dict:
    """List firewall rules. `query` supports Firewalla's search syntax, e.g. 'status:paused action:allow'."""
    return get_client().list_rules(query=query)


@mcp.tool()
def get_rule(rule_id: str) -> dict:
    """Get a single firewall rule by id (fetched by filtering the rule list)."""
    return get_client().get_rule(rule_id)


@mcp.tool()
def update_rule(rule_id: str, changes: dict) -> dict:
    """Edit an existing firewall rule.

    Firewalla's MSP API has NO native rule-edit endpoint, so this recreates the
    rule: it builds a new rule from the current one with your `changes` applied,
    creates it, then deletes the original. **The rule id changes** — the return
    value is {"deleted_id": <old id>, "rule": <new rule with new id>}. The new
    rule is created before the old one is deleted, so a failure never leaves you
    with no rule.

    `changes` is a dict of top-level rule fields to override; each field replaces
    the existing value wholesale (no deep merge). Common example — change a rule's
    schedule to block 17:00-09:00 daily:
    {"schedule": {"cronTime": "0 17 * * *", "duration": 57600}}
    (cronTime = when the block STARTS; duration = seconds it lasts, so 57600 = 16h.)
    To clear a schedule (make it always-on), pass {"schedule": null}.
    """
    return get_client().update_rule(rule_id, changes)


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
        for k, v in {
            "name": name,
            "targets": targets,
            "category": category,
            "notes": notes,
        }.items()
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


@mcp.tool()
def get_rule_trends(group: str | None = None) -> list[dict]:
    """Get daily rule-creation counts, optionally scoped to a box group."""
    return get_client().get_rule_trends(group=group)


@mcp.tool()
def get_simple_stats(group: str | None = None) -> dict:
    """Dashboard rollup for the account (optionally one box group): online/offline
    box counts, active alarm count, rule count."""
    return get_client().get_simple_stats(group=group)


@mcp.tool()
def get_stats(
    stats_type: str, group: str | None = None, limit: int | None = None
) -> list[dict]:
    """Top-N leaderboards. `stats_type` is one of: 'topBoxesByBlockedFlows',
    'topBoxesBySecurityAlarms', 'topRegionsByBlockedFlows'. `limit` defaults to 5
    server-side. Most useful across multiple boxes."""
    return get_client().get_stats(stats_type, group=group, limit=limit)


def main() -> None:
    # Validate configuration before serving so a misconfigured environment
    # fails at startup with a clear message, not at the first tool call.
    get_msp_domain()
    get_token()
    get_timeout()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
