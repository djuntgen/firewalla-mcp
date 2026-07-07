# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-06

### Added

- Initial release: MCP server wrapping the Firewalla MSP API v2.
- Tools for boxes, devices, alarms, rules, flows, target lists, and trends (19 tools total).
- Retry handling for transient 5xx/connection errors (one retry, 0.5s backoff); 4xx errors fail immediately.
- Auth and MSP domain configured via `FIREWALLA_TOKEN` and `FIREWALLA_MSP_DOMAIN` environment variables.
