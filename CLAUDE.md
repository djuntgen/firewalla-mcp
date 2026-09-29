# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local stdio MCP server wrapping the **Firewalla MSP API v2** — boxes, devices, people/apps,
alarms, rules, flows, target lists, trends, and statistics — as tools for Claude Code and other
MCP clients. Public, MIT, published as `firewalla-mcp` and runnable straight from GitHub with
`uvx`. Requires Python 3.12+ and an active Firewalla MSP subscription.

Small on purpose: ~700 lines across three modules.

## Commands

```bash
uv sync
uv run pytest -v
uv run pytest tests/test_client_rules.py::test_name    # single test
uv run ruff check . && uv run ruff format --check .    # both enforced in CI
```

The suite is fully mocked with `respx` — **no Firewalla credentials or network access are
needed to run it**, and no test should ever require them.

## Architecture

Two layers, one file each. Every MSP API operation is implemented in both:

1. `src/firewalla_mcp/client.py` — a method on `FirewallaClient` that calls `self._request(...)`
   and returns parsed JSON. All HTTP behavior (auth, retries, error shaping) lives here.
2. `src/firewalla_mcp/server.py` — a thin `@mcp.tool()` wrapper calling the client method. Its
   **docstring is the MCP tool description** the model reads, so write it for that audience.

`config.py` reads `FIREWALLA_MSP_DOMAIN`, `FIREWALLA_TOKEN`, and optional `FIREWALLA_TIMEOUT`
(default 10s) from the environment at startup; a pasted `https://` prefix or trailing slash on
the domain is tolerated.

To add a tool: follow an existing method as a template, add client tests that mock the HTTP call
with `respx`, and **update the expected tool set in `tests/test_server.py`** — that test pins the
full inventory and will fail otherwise.

## Deliberate design decisions — do not change casually

**Retry policy** (`client.py`, `MAX_ATTEMPTS`/`RETRY_BACKOFF_SECONDS`/`MAX_RETRY_AFTER_SECONDS`):

- 4xx fails immediately, raising `FirewallaAPIError(status_code, body)` with the body truncated
  to `MAX_ERROR_BODY_CHARS` so failures stay readable.
- 429 retries once, honoring `Retry-After` up to 10s.
- 5xx and connection errors retry once with 0.5s backoff — **except** non-idempotent writes
  (`create_rule`, `create_target_list`, `update_device`, `mute_alarm`, `archive_alarm`), which
  are never retried so a timed-out request cannot silently duplicate or double-apply a write.
- Non-JSON responses (e.g. an HTML proxy error page) raise a readable error, not a decoder
  traceback.

`CONTRIBUTING.md` asks that this policy not be changed without discussion.

**No dry-run or confirmation gate on writes.** This is intentional — the server relies on the
MCP client's own confirmation prompts before destructive calls (`delete_rule`,
`delete_target_list`, `delete_alarm`). Don't add a server-side gate.

**`update_rule` recreates rather than edits.** The MSP API has no rule-update endpoint, so it
creates a replacement then deletes the original. The rule **id changes**, and the return value
reports both the deleted id and the new rule. Only the fields in `RULE_CREATE_FIELDS` carry
over; server-managed fields (`id`, `ts`, `hit`, …) are dropped.

## Style

TDD — write the failing test, implement, confirm it passes. Keep PRs to one tool or fix.
CI (`.github/workflows/test.yml`) runs the suite plus `ruff check` and `ruff format --check` on
every PR.

## Secrets

The token is read from the environment, never committed. `--env` values registered via
`claude mcp add` are stored in **plaintext** in the client config (`~/.claude.json`); the
documented alternative is a wrapper script that resolves the token live from a secrets manager
and `exec`s the server. See `SECURITY.md`. Examples in the docs use `op read` (1Password CLI).

`CHANGELOG.md` is maintained per release; version lives in `pyproject.toml` and is asserted by
`tests/test_version.py`.
