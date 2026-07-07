# firewalla-mcp

[![Tests](https://github.com/djuntgen/firewalla-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/djuntgen/firewalla-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local [MCP](https://modelcontextprotocol.io) server exposing the [Firewalla MSP API](https://docs.firewalla.net/) — boxes, alarms, rules, devices, flows, target lists, and trends — as tools for Claude Code and other MCP-compatible clients.

Full read/write: list and inspect your Firewalla boxes, alarms, devices, and flows, and create/pause/resume/delete firewall rules and target lists, all from natural-language requests to your AI assistant.

## Prerequisites

- An MSP-managed Firewalla box, and an MSP API personal access token (Firewalla MSP dashboard → Settings → API)
- [`uv`](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Setup

```bash
git clone https://github.com/djuntgen/firewalla-mcp.git
cd firewalla-mcp
uv sync
```

The server reads two environment variables at startup:

| Variable | Description |
|---|---|
| `FIREWALLA_MSP_DOMAIN` | Your MSP domain, e.g. `your-alias.firewalla.net` |
| `FIREWALLA_TOKEN` | Your Firewalla MSP API personal access token |

Export them however fits your workflow — a `.env` file loaded by your shell, a secrets manager, or directly:

```bash
export FIREWALLA_MSP_DOMAIN="your-alias.firewalla.net"
export FIREWALLA_TOKEN="$(op read 'op://Vault/Firewalla PAT/password')"  # example using 1Password CLI
```

## Register with Claude Code

```bash
claude mcp add firewalla --env FIREWALLA_MSP_DOMAIN="your-alias.firewalla.net" --env FIREWALLA_TOKEN="your-token" -- uv run --project /path/to/firewalla-mcp firewalla-mcp
```

This registers the server at local scope (machine-specific, not committed to a shared `.mcp.json`).

## Tools

One tool per Firewalla MSP API v2 operation:

| Category | Tools |
|---|---|
| Boxes | `list_boxes`, `get_box` |
| Devices | `list_devices` |
| Alarms | `list_alarms`, `get_alarm`, `delete_alarm` |
| Rules | `list_rules`, `create_rule`, `pause_rule`, `resume_rule`, `delete_rule` |
| Flows | `list_flows` |
| Target Lists | `list_target_lists`, `get_target_list`, `create_target_list`, `update_target_list`, `delete_target_list` |
| Trends | `get_flow_trends`, `get_alarm_trends` |

Full read/write — there is no server-side dry-run gate on writes. Rely on your MCP client's normal confirmation prompts before destructive actions (`delete_rule`, `delete_target_list`, `delete_alarm`).

## Error handling

HTTP 4xx responses fail immediately. HTTP 5xx responses and connection errors are retried once (0.5s backoff) before failing, raising `FirewallaAPIError(status_code, body)`.

## Development

```bash
uv sync
uv run pytest -v
```

Tests are fully mocked (`respx`) — no real Firewalla API calls or credentials are needed to run the suite. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
