# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-10

### Changed

- **Safer retries**: non-idempotent creates (`create_rule`, `create_target_list`) are no longer retried on 5xx or transport errors — a timed-out create may already have been processed, and a blind retry could silently create a duplicate rule or target list.
- HTTP 429 responses are now retried once, honoring `Retry-After` (capped at 10s). Safe for all methods, since a rate-limited request was rejected before processing.
- `FIREWALLA_MSP_DOMAIN` is normalized: an `http(s)://` prefix and trailing slash are stripped, and values still containing a path are rejected with a clear error.
- Configuration is validated at server startup instead of at the first tool call.
- API error bodies are truncated to 500 characters so proxy HTML error pages don't flood MCP client context.
- Non-JSON 2xx responses raise a readable `FirewallaAPIError` instead of a raw `JSONDecodeError`.
- Path parameters (`gid`, `aid`, `rule_id`, `list_id`) are URL-escaped.
- `create_rule`'s tool description documents the rule object shape with a worked example; delete tools warn that the action is irreversible.

### Added

- `FIREWALLA_TIMEOUT` environment variable (seconds, default 10).
- `FirewallaError` base class for `FirewallaAPIError` and `FirewallaNotFoundError`.
- `SECURITY.md`, Dependabot config, CI matrix (Python 3.12/3.13) with ruff lint/format checks, and full `pyproject.toml` metadata (license, URLs, classifiers, keywords).

## [0.1.0] - 2026-07-06

### Added

- Initial release: MCP server wrapping the Firewalla MSP API v2.
- Tools for boxes, devices, alarms, rules, flows, target lists, and trends (19 tools total).
- Retry handling for transient 5xx/connection errors (one retry, 0.5s backoff); 4xx errors fail immediately.
- Auth and MSP domain configured via `FIREWALLA_TOKEN` and `FIREWALLA_MSP_DOMAIN` environment variables.
