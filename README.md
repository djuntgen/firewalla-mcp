# firewalla-mcp

[![Tests](https://github.com/djuntgen/firewalla-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/djuntgen/firewalla-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local [MCP](https://modelcontextprotocol.io) server exposing the [Firewalla MSP API](https://docs.firewalla.net/) — boxes, alarms, rules, devices, flows, target lists, and trends — as tools for Claude Code and other MCP-compatible clients.

Full read/write: list and inspect your Firewalla boxes, alarms, devices, and flows, and create/pause/resume/delete firewall rules and target lists, all from natural-language requests to your AI assistant.

## Prerequisites

- A Firewalla box managed by [Firewalla MSP](https://firewalla.com/msp) (the MSP API requires an active MSP subscription), and an MSP API personal access token (MSP dashboard → Settings → API)
- [`uv`](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Configuration

The server reads its configuration from environment variables at startup:

| Variable | Required | Description |
|---|---|---|
| `FIREWALLA_MSP_DOMAIN` | yes | Your MSP domain, e.g. `your-alias.firewalla.net` (a pasted `https://` prefix or trailing slash is tolerated) |
| `FIREWALLA_TOKEN` | yes | Your Firewalla MSP API personal access token |
| `FIREWALLA_TIMEOUT` | no | HTTP timeout in seconds (default `10`) |

Resolve the token from a secrets manager rather than storing it in plaintext:

```bash
export FIREWALLA_MSP_DOMAIN="your-alias.firewalla.net"
export FIREWALLA_TOKEN="$(op read 'op://Vault/Firewalla PAT/password')"  # example using 1Password CLI
```

## Register with Claude Code

No clone needed — run straight from GitHub with `uvx`:

```bash
claude mcp add firewalla \
  --env FIREWALLA_MSP_DOMAIN="your-alias.firewalla.net" \
  --env FIREWALLA_TOKEN="$(op read 'op://Vault/Firewalla PAT/password')" \
  -- uvx --from git+https://github.com/djuntgen/firewalla-mcp firewalla-mcp
```

Or from a local clone:

```bash
git clone https://github.com/djuntgen/firewalla-mcp.git && cd firewalla-mcp && uv sync
claude mcp add firewalla \
  --env FIREWALLA_MSP_DOMAIN="your-alias.firewalla.net" \
  --env FIREWALLA_TOKEN="$(op read 'op://Vault/Firewalla PAT/password')" \
  -- uv run --project /path/to/firewalla-mcp firewalla-mcp
```

This registers the server at local scope (machine-specific, not committed to a shared `.mcp.json`).

> **Note on token storage:** `--env` values are stored in plaintext in your MCP client's
> config file (e.g. `~/.claude.json`). To keep the token out of persistent config
> entirely, register a small wrapper script as the command instead — it exports the
> variables (resolving the token live from your secrets manager) and `exec`s
> `uvx --from git+https://github.com/djuntgen/firewalla-mcp firewalla-mcp`.
> See [SECURITY.md](SECURITY.md).

## Tools

One tool per Firewalla MSP API v2 operation:

| Category | Tools |
|---|---|
| Boxes | `list_boxes`, `get_box` |
| Devices | `list_devices`, `update_device` (rename a device — the only API-updatable field) |
| Alarms | `list_alarms`, `get_alarm`, `delete_alarm`, `mute_alarm` (mute an alarm's future recurrences, by type or domain, network-wide or per-device), `archive_alarm` (archive an alarm — dismiss but keep the record) |
| Rules | `list_rules`, `get_rule`, `create_rule`, `update_rule`, `pause_rule`, `resume_rule`, `delete_rule` |
| Flows | `list_flows` |
| Target Lists | `list_target_lists`, `get_target_list`, `create_target_list`, `update_target_list`, `delete_target_list` |
| Trends | `get_flow_trends`, `get_alarm_trends`, `get_rule_trends` (daily rule-creation counts) |
| Statistics | `get_simple_stats` (dashboard rollup: online/offline box counts, alarm count, rule count), `get_stats` (top-N leaderboards: topBoxesByBlockedFlows, topBoxesBySecurityAlarms, topRegionsByBlockedFlows) |

Full read/write — there is no server-side dry-run gate on writes. Rely on your MCP client's normal confirmation prompts before destructive actions (`delete_rule`, `delete_target_list`, `delete_alarm`).

> **`update_rule` note:** Firewalla's MSP API has no rule-edit endpoint, so `update_rule` recreates the rule (create replacement → delete original). The rule **id changes**, and the returned value reports both the deleted id and the new rule.

## Error handling

- HTTP 4xx responses fail immediately (no retry), raising `FirewallaAPIError(status_code, body)`; error bodies are truncated to keep failures readable.
- HTTP 429 (rate limited) is retried once, honoring `Retry-After` up to 10s.
- HTTP 5xx and connection errors are retried once (0.5s backoff) — **except** for non-idempotent writes (`create_rule`, `create_target_list`, `update_device`, `mute_alarm`, `archive_alarm`), which are never retried, so a timed-out request can't silently duplicate or double-apply a write.
- Non-JSON responses (e.g. an HTML error page from a proxy) raise a readable error instead of a decoder traceback.

## Development

```bash
uv sync
uv run pytest -v
uv run ruff check . && uv run ruff format --check .
```

Tests are fully mocked (`respx`) — no real Firewalla API calls or credentials are needed to run the suite. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
