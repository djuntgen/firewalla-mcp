# Firewalla MCP — MSP `/v2` API Parity (0.4.0)

**Goal:** Close every real gap between the documented Firewalla MSP `/v2` API and the `firewalla-mcp` wrapper by adding the six missing endpoints as client methods + MCP tools, following the existing pattern, with per-area tests.

**Status:** design approved (Dave, 2026-07-18) — build all 6.

## Context & audit result

The wrapper (v0.3.0) covers boxes, devices (list only), alarms (list/get/delete/trends), rules (full CRUD-ish + pause/resume), flows (list/trends), target-lists (full CRUD). A full audit of the documented `/v2` surface (sections: Box, Device, Alarm, Flow, Rule, Target List, Trends, Statistics) found **6 endpoints the wrapper lacks**. No param-level PARTIAL gaps exist (verified `list_alarms` already passes `groupBy`/`sortBy`/`limit`/`cursor`; `list_boxes` already passes `group`).

**Explicitly out of scope — portal-only, no `/v2` API (do not build):**
- Target-list **import** (MSP 2.8) — UI only; Firewalla disables URL import for security.
- **FireAI** search (MSP 2.9) — UI-only NL→search-syntax translator; already covered by `list_flows(query=...)` + the LLM.
- Single-device **GET** — no dedicated endpoint exists; use `list_devices` + filter.
- Groups / Users / Networks CRUD — no such `/v2` sections exist.

## Global Constraints

- **Pattern is law:** every endpoint = one thin `client.py` method calling `self._request(METHOD, path, params=/json=)` → `self._json(...)`, plus one `@mcp.tool()` in `server.py` that calls `get_client()`. No new abstractions, no new files.
- **Path segments interpolated from caller input MUST use `_quote(...)`** (existing helper) — gid, aid, device_id, list_id, stats type.
- **Writes** (`update_device`, `mute_alarm`, `archive_alarm`) pass `idempotent=False` to `_request` exactly as `create_rule`/`create_target_list` do, and their tool docstrings state the effect plainly (match the LLM-guidance tone from commit `7441a66`).
- **Tests:** mirror the existing `respx`-mocked style (`tests/test_client_<area>.py`), one test per method incl. param/body assertions; add server-tool tests to `tests/test_server.py` matching existing coverage.
- **Version:** bump `pyproject.toml` `0.3.0` → `0.4.0`; add a `CHANGELOG.md` entry.
- **Base URL** is `https://{msp_domain}/v2` (set in `FirewallaClient.__init__`); paths are relative (`/stats/simple`, not `/v2/stats/simple`).

## The six endpoints

### 1. `update_device` — rename a device (write)
- **API:** `PATCH /boxes/{gid}/devices/{id}`, body `{"name": <str>}`. `name` is the ONLY updatable field (max 32 chars). Returns the updated device object.
- **Client:** `def update_device(self, gid: str, device_id: str, name: str) -> dict:` → `self._json(self._request("PATCH", f"/boxes/{_quote(gid)}/devices/{_quote(device_id)}", json={"name": name}))`.
- **Tool:** `update_device(gid: str, device_id: str, name: str) -> dict` — docstring: "Rename a device. `name` max 32 chars; it is the only field the API can change (no block/pause via API). gid = box id, device_id from list_devices `id`."
- **Note:** length is enforced server-side (400 on violation) — do NOT client-validate; surface the API error as-is via existing `FirewallaAPIError`.

### 2. `get_simple_stats` — dashboard rollup (read)
- **API:** `GET /stats/simple`, optional query `group`. Response: `{onlineBoxes, offlineBoxes, alarms, rules}` (ints).
- **Client:** `def get_simple_stats(self, group: str | None = None) -> dict:` — params `{"group": group}` only if set (mirror `list_boxes`).
- **Tool:** `get_simple_stats(group: str | None = None) -> dict`.

### 3. `get_rule_trends` — rules-created-per-day trend (read)
- **API:** `GET /trends/rules`, optional query `group`. Response: `[{ts, value}]`. Completes the trend trio alongside existing `get_flow_trends`/`get_alarm_trends`.
- **Client:** `def get_rule_trends(self, group: str | None = None) -> list[dict]:` — identical shape to `get_flow_trends` (copy that method, swap `/trends/flows` → `/trends/rules`).
- **Tool:** `get_rule_trends(group: str | None = None) -> list[dict]`.

### 4. `mute_alarm` — silence an alarm (write)
- **API:** `POST /alarms/{gid}/{aid}/mute`, body `{"target": {"type": ...}, "scope": {"type": ...}}`.
  - `target.type` ∈ `"alarmType"` (default; mutes this alarm's type) | `"domain"` (requires `target.value` = domain).
  - `scope.type` ∈ `"all"` (default; network-wide) | `"device"` (requires `scope.value` = device MAC).
- **Client:** `def mute_alarm(self, gid: str, aid: str, *, target_type: str = "alarmType", target_value: str | None = None, scope_type: str = "all", scope_value: str | None = None) -> None:` — builds nested body, adds `value` keys only when provided; `self._request("POST", f"/alarms/{_quote(gid)}/{_quote(aid)}/mute", json=body, idempotent=False)`.
- **Tool:** `mute_alarm(gid, aid, target_type="alarmType", target_value=None, scope_type="all", scope_value=None) -> str` — flat params (nested objects are awkward for the LLM); returns a confirmation string like the other write tools. Docstring gives the two enums and when `value` is required. Default call `mute_alarm(gid, aid)` = mute this alarm's type network-wide (the common case).

### 5. `archive_alarm` — dismiss but keep record (write)
- **API:** `POST /alarms/{gid}/{aid}/archive`, no body. 200 empty on success.
- **Client:** `def archive_alarm(self, gid: str, aid: str) -> None:` → `self._request("POST", f"/alarms/{_quote(gid)}/{_quote(aid)}/archive", idempotent=False)`.
- **Tool:** `archive_alarm(gid, aid) -> str` — returns confirmation. Docstring contrasts with `delete_alarm` (archive keeps the record; delete is irreversible).

### 6. `get_stats` — top-N leaderboards (read)
- **API:** `GET /stats/{type}`, `type` ∈ `topBoxesByBlockedFlows` | `topBoxesBySecurityAlarms` | `topRegionsByBlockedFlows`. Query `group` (optional), `limit` (optional, default 5). Response `[{meta: {gid, name, model}, value}]`.
- **Client:** `def get_stats(self, stats_type: str, group: str | None = None, limit: int | None = None) -> list[dict]:` — path `f"/stats/{_quote(stats_type)}"`, params for group/limit when set.
- **Tool:** `get_stats(stats_type: str, group: str | None = None, limit: int | None = None) -> list[dict]` — docstring lists the three valid `stats_type` values and notes it's fleet-oriented (most useful across multiple boxes).

## Verification before writing the two 2.11.0 write tools

`mute`/`archive` are tagged "MSP 2.11.0+" and no GA release note was found, though the wrapper already ships `DELETE /rules/{id}` (same tag), so they are almost certainly live. **During implementation, before finalizing `mute_alarm`/`archive_alarm`, run one read-only confirmation against the live MSP** (e.g. confirm an alarm exists via `list_alarms`, then confirm the endpoints respond — a 400/valid-shape rather than 404-route-missing). If either route is genuinely absent, mark that tool blocked and surface it rather than shipping a dead tool.

## Testing

Per area, mirroring `tests/test_client_*.py` (`respx`-mocked routes, assert route called + params/body + return):
- `tests/test_client_boxes_devices.py` (extend — existing device tests live here): `update_device` — asserts PATCH path + `{"name": ...}` body + returns updated object.
- `tests/test_client_stats.py` (new): `get_simple_stats` (with/without group), `get_stats` (type in path, limit/group params).
- `tests/test_client_alarms.py` (extend): `mute_alarm` — default body `{target:{type:alarmType}, scope:{type:all}}`; domain+device variant includes `value`s; `archive_alarm` — POST to `/archive`, no body.
- `tests/test_client_flows_trends.py` (extend): `get_rule_trends` hits `/trends/rules`.
- `tests/test_server.py` (extend): each new tool is registered and delegates to the client (mirror existing tool tests).

**Acceptance:** `uv run pytest` green; `uv run ruff check` clean; all six tools listed by the server; three writes carry `idempotent=False`; version 0.4.0.

## Out of scope / deferred
Import target list, FireAI, single-device GET, groups/users/networks (all non-existent as `/v2` API). The undocumented `GET /boxes/{gid}` the wrapper already relies on is left as-is (not a parity gap; flag only if Firewalla ever removes it).
