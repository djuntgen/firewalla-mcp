import asyncio

from firewalla_mcp.server import mcp

EXPECTED_TOOL_NAMES = {
    "list_boxes",
    "get_box",
    "list_devices",
    "list_alarms",
    "get_alarm",
    "delete_alarm",
    "list_rules",
    "create_rule",
    "pause_rule",
    "resume_rule",
    "delete_rule",
    "list_flows",
    "list_target_lists",
    "get_target_list",
    "create_target_list",
    "update_target_list",
    "delete_target_list",
    "get_flow_trends",
    "get_alarm_trends",
}


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    tool_names = {t.name for t in tools}

    assert tool_names == EXPECTED_TOOL_NAMES
