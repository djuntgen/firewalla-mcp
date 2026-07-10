# Contributing

## Setup

```bash
uv sync
uv run pytest -v
uv run ruff check . && uv run ruff format .
```

No Firewalla credentials are needed to run the test suite — all HTTP calls are mocked with [`respx`](https://lundberg.pydantic.dev/respx/).

## Adding a tool

Each Firewalla MSP API operation is implemented in two layers:

1. `src/firewalla_mcp/client.py` — a method on `FirewallaClient` that calls `self._request(...)` and returns parsed JSON.
2. `src/firewalla_mcp/server.py` — a thin `@mcp.tool()` wrapper that calls the client method and adds a docstring for the MCP tool description.

Follow existing methods as a template. Add tests for the client method (mocking the HTTP call with `respx`) and, if you add a new tool, update the expected tool set in `tests/test_server.py`.

## Style

- TDD: write a failing test, implement, confirm it passes.
- Formatting and linting are enforced in CI (`ruff check` + `ruff format --check`).
- No dry-run/confirmation gate on write operations — that's a deliberate design choice; rely on the MCP client's own confirmation behavior.
- Retry policy: 4xx fails immediately; 429 retries once honoring `Retry-After`; 5xx/connection errors retry once — but never for non-idempotent creates (`create_rule`, `create_target_list`), which could be duplicated by a retry. Don't change this without discussion.

## Pull requests

Keep them focused — one tool or fix per PR is easiest to review. CI runs the test suite on every PR.
