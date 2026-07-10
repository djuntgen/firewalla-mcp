# Security Policy

This project holds a credential (`FIREWALLA_TOKEN`) that can read and reconfigure a
firewall. Please treat vulnerabilities in it accordingly.

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Report vulnerabilities privately via
[GitHub Security Advisories](https://github.com/djuntgen/firewalla-mcp/security/advisories/new)
— please do not open a public issue for anything exploitable. You should get an
initial response within a week.

## Token handling guidance

- Resolve `FIREWALLA_TOKEN` from a secrets manager at launch (e.g. `op read`,
  `pass`, or your platform's keychain) rather than storing it in plaintext files.
- Be aware that MCP client configs (e.g. `~/.claude.json`) store `--env` values in
  plaintext; a small wrapper script that exports the token and `exec`s the server
  keeps it out of persistent config.
- The server never logs the token, and API error messages contain only the response
  status and (truncated) body.
