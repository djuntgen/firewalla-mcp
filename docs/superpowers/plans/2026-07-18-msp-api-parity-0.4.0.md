# Firewalla MCP — MSP `/v2` API Parity (0.4.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the six documented `/v2` endpoints the wrapper lacks (`update_device`, `get_simple_stats`, `get_rule_trends`, `mute_alarm`, `archive_alarm`, `get_stats`) as client methods + MCP tools + tests, reaching API parity, and release 0.4.0.

**Architecture:** Each endpoint is one thin `client.py` method (calls `self._request(METHOD, path, params=/json=)` → `self._json(...)`) plus one `@mcp.tool()` in `server.py` delegating to `get_client()`. No new modules, no new abstractions. Tests mirror the existing `respx`-mocked style.

**Tech Stack:** Python 3, `httpx`, `mcp[cli]` (FastMCP), `respx` + `pytest` for tests, `ruff` for lint, `uv` for env/run.

## Global Constraints

- Base URL is `https://{msp_domain}/v2` (set in `FirewallaClient.__init__`); all client paths are **relative** — `/stats/simple`, NOT `/v2/stats/simple`.
- Interpolate caller-supplied path segments with the existing `_quote(...)` helper (gid, aid, device_id, stats type).
- Writes pass `idempotent=False` to `_request` (like `create_rule`). Reads use the default.
- Write MCP tools return a human-readable confirmation `str` (like `delete_alarm` → `f"Deleted alarm {aid} on box {gid}"`).
- `tests/test_server.py::test_all_tools_registered` asserts the tool set **exactly equals** `EXPECTED_TOOL_NAMES` — every task that adds a tool MUST add its name to that set in the same commit, or the suite breaks.
- Do NOT client-validate field lengths/enums the API enforces (e.g. device name ≤32) — let the API 400 surface via `FirewallaAPIError`.
- Run tests with `uv run pytest`; lint with `uv run ruff check`. Both must be green at each task's commit.
- Final version: `pyproject.toml` `0.3.0` → `0.4.0` (Task 6).

## File Structure

- Modify `src/firewalla_mcp/client.py` — add 6 methods among the existing ones (device write near `list_devices`; stats near the trends methods; rule trend near `get_alarm_trends`; alarm writes near `delete_alarm`).
- Modify `src/firewalla_mcp/server.py` — add 6 `@mcp.tool()` wrappers in the matching sections.
- Modify `tests/test_client_boxes_devices.py` — `update_device` tests.
- Create `tests/test_client_stats.py` — `get_simple_stats`, `get_stats` tests.
- Modify `tests/test_client_flows_trends.py` — `get_rule_trends` test.
- Modify `tests/test_client_alarms.py` — `mute_alarm`, `archive_alarm` tests.
- Modify `tests/test_server.py` — grow `EXPECTED_TOOL_NAMES` (+6) as tools land.
- Modify `pyproject.toml` + `CHANGELOG.md` — release 0.4.0 (Task 6).

---

### Task 1: `update_device` — rename a device (write)

**Files:**
- Modify: `src/firewalla_mcp/client.py` (add method after `list_devices`)
- Modify: `src/firewalla_mcp/server.py` (add tool after `list_devices` tool)
- Modify: `tests/test_client_boxes_devices.py`
- Modify: `tests/test_server.py` (add `"update_device"` to `EXPECTED_TOOL_NAMES`)

**Interfaces:**
- Produces: `FirewallaClient.update_device(self, gid: str, device_id: str, name: str) -> dict`; tool `update_device(gid: str, device_id: str, name: str) -> dict`.

- [ ] **Step 1: Write the failing client test**

Add `import json` to the top of `tests/test_client_boxes_devices.py` (it currently imports only `httpx`, `pytest`, `respx` — `json` is NOT present and is needed to assert the request body). Then add:
```python
@respx.mock
def test_update_device_renames():
    route = respx.patch(
        "https://example.firewalla.net/v2/boxes/box-1/devices/dev-9"
    ).mock(return_value=httpx.Response(200, json={"id": "dev-9", "name": "Matthew-PC"}))
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.update_device("box-1", "dev-9", "Matthew-PC")

    assert route.called
    assert json.loads(route.calls.last.request.content) == {"name": "Matthew-PC"}
    assert result == {"id": "dev-9", "name": "Matthew-PC"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_boxes_devices.py::test_update_device_renames -v`
Expected: FAIL — `AttributeError: 'FirewallaClient' object has no attribute 'update_device'`

- [ ] **Step 3: Implement the client method**

In `src/firewalla_mcp/client.py`, immediately after the `list_devices` method:
```python
    def update_device(self, gid: str, device_id: str, name: str) -> dict:
        # PATCH /boxes/{gid}/devices/{id}; `name` is the only updatable field
        # (max 32 chars, enforced server-side).
        return self._json(
            self._request(
                "PATCH",
                f"/boxes/{_quote(gid)}/devices/{_quote(device_id)}",
                json={"name": name},
                idempotent=False,
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_boxes_devices.py::test_update_device_renames -v`
Expected: PASS

- [ ] **Step 5: Add the MCP tool**

In `src/firewalla_mcp/server.py`, after the `list_devices` tool:
```python
@mcp.tool()
def update_device(gid: str, device_id: str, name: str) -> dict:
    """Rename a device. `name` is the ONLY field the API can change (max 32
    chars; no block/pause via API). `gid` is the box id; `device_id` is a
    device `id` from list_devices."""
    return get_client().update_device(gid, device_id, name)
```

- [ ] **Step 6: Register the tool name**

In `tests/test_server.py`, add `"update_device",` to the `EXPECTED_TOOL_NAMES` set.

- [ ] **Step 7: Run the full suite + lint**

Run: `uv run pytest -q && uv run ruff check`
Expected: all pass; `test_all_tools_registered` green with the new name.

- [ ] **Step 8: Commit**

```bash
git add src/firewalla_mcp/client.py src/firewalla_mcp/server.py tests/test_client_boxes_devices.py tests/test_server.py
git commit -m "feat(devices): add update_device (rename) tool"
```

---

### Task 2: `get_simple_stats` + `get_stats` — statistics reads

**Files:**
- Modify: `src/firewalla_mcp/client.py` (add both methods after `get_alarm_trends`)
- Modify: `src/firewalla_mcp/server.py` (add both tools after `get_alarm_trends` tool)
- Create: `tests/test_client_stats.py`
- Modify: `tests/test_server.py` (add `"get_simple_stats"`, `"get_stats"`)

**Interfaces:**
- Produces: `FirewallaClient.get_simple_stats(self, group: str | None = None) -> dict`; `FirewallaClient.get_stats(self, stats_type: str, group: str | None = None, limit: int | None = None) -> list[dict]`; tools of the same signatures.

- [ ] **Step 1: Write the failing client tests**

Create `tests/test_client_stats.py`:
```python
import httpx
import respx

from firewalla_mcp.client import FirewallaClient


@respx.mock
def test_get_simple_stats_no_group():
    route = respx.get("https://example.firewalla.net/v2/stats/simple").mock(
        return_value=httpx.Response(
            200, json={"onlineBoxes": 1, "offlineBoxes": 0, "alarms": 4, "rules": 12}
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.get_simple_stats()

    assert route.called
    assert result["onlineBoxes"] == 1


@respx.mock
def test_get_simple_stats_with_group():
    route = respx.get(
        "https://example.firewalla.net/v2/stats/simple", params={"group": "g1"}
    ).mock(return_value=httpx.Response(200, json={}))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.get_simple_stats(group="g1")

    assert route.called


@respx.mock
def test_get_stats_type_in_path_with_limit():
    route = respx.get(
        "https://example.firewalla.net/v2/stats/topBoxesByBlockedFlows",
        params={"limit": "3"},
    ).mock(
        return_value=httpx.Response(
            200, json=[{"meta": {"gid": "b1", "name": "Home", "model": "gold"}, "value": 9}]
        )
    )
    client = FirewallaClient("example.firewalla.net", "tok")

    result = client.get_stats("topBoxesByBlockedFlows", limit=3)

    assert route.called
    assert result[0]["value"] == 9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_client_stats.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'get_simple_stats'`

- [ ] **Step 3: Implement the client methods**

In `src/firewalla_mcp/client.py`, after `get_alarm_trends`:
```python
    def get_simple_stats(self, group: str | None = None) -> dict:
        params = {"group": group} if group else None
        return self._json(self._request("GET", "/stats/simple", params=params))

    def get_stats(
        self, stats_type: str, group: str | None = None, limit: int | None = None
    ) -> list[dict]:
        params: dict = {}
        if group:
            params["group"] = group
        if limit is not None:
            params["limit"] = limit
        return self._json(
            self._request("GET", f"/stats/{_quote(stats_type)}", params=params or None)
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_client_stats.py -v`
Expected: PASS (all 3)

- [ ] **Step 5: Add the MCP tools**

In `src/firewalla_mcp/server.py`, after the `get_alarm_trends` tool:
```python
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
```

- [ ] **Step 6: Register the tool names**

In `tests/test_server.py`, add `"get_simple_stats",` and `"get_stats",` to `EXPECTED_TOOL_NAMES`.

- [ ] **Step 7: Run the full suite + lint**

Run: `uv run pytest -q && uv run ruff check`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/firewalla_mcp/client.py src/firewalla_mcp/server.py tests/test_client_stats.py tests/test_server.py
git commit -m "feat(stats): add get_simple_stats and get_stats tools"
```

---

### Task 3: `get_rule_trends` — rules-per-day trend (read)

**Files:**
- Modify: `src/firewalla_mcp/client.py` (add after `get_alarm_trends`, before the stats methods from Task 2 — placement is cosmetic)
- Modify: `src/firewalla_mcp/server.py` (add after `get_alarm_trends` tool)
- Modify: `tests/test_client_flows_trends.py`
- Modify: `tests/test_server.py` (add `"get_rule_trends"`)

**Interfaces:**
- Produces: `FirewallaClient.get_rule_trends(self, group: str | None = None) -> list[dict]`; tool of the same signature. Mirrors existing `get_flow_trends`.

- [ ] **Step 1: Write the failing client test**

Add to `tests/test_client_flows_trends.py`:
```python
@respx.mock
def test_get_rule_trends_with_group():
    route = respx.get(
        "https://example.firewalla.net/v2/trends/rules", params={"group": "g1"}
    ).mock(return_value=httpx.Response(200, json=[{"ts": 1719800000, "value": 2}]))
    client = FirewallaClient("example.firewalla.net", "tok")

    trends = client.get_rule_trends(group="g1")

    assert route.called
    assert trends == [{"ts": 1719800000, "value": 2}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_client_flows_trends.py::test_get_rule_trends_with_group -v`
Expected: FAIL — no attribute `get_rule_trends`

- [ ] **Step 3: Implement the client method**

In `src/firewalla_mcp/client.py`, immediately after `get_alarm_trends`:
```python
    def get_rule_trends(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._json(self._request("GET", "/trends/rules", params=params))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_client_flows_trends.py::test_get_rule_trends_with_group -v`
Expected: PASS

- [ ] **Step 5: Add the MCP tool**

In `src/firewalla_mcp/server.py`, after the `get_alarm_trends` tool:
```python
@mcp.tool()
def get_rule_trends(group: str | None = None) -> list[dict]:
    """Get daily rule-creation counts, optionally scoped to a box group."""
    return get_client().get_rule_trends(group=group)
```

- [ ] **Step 6: Register the tool name**

In `tests/test_server.py`, add `"get_rule_trends",` to `EXPECTED_TOOL_NAMES`.

- [ ] **Step 7: Run the full suite + lint**

Run: `uv run pytest -q && uv run ruff check`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/firewalla_mcp/client.py src/firewalla_mcp/server.py tests/test_client_flows_trends.py tests/test_server.py
git commit -m "feat(trends): add get_rule_trends tool"
```

---

### Task 4: `mute_alarm` + `archive_alarm` — alarm writes

**Files:**
- Modify: `src/firewalla_mcp/client.py` (add both after `delete_alarm`)
- Modify: `src/firewalla_mcp/server.py` (add both after `delete_alarm` tool)
- Modify: `tests/test_client_alarms.py`
- Modify: `tests/test_server.py` (add `"mute_alarm"`, `"archive_alarm"`)

**Interfaces:**
- Produces: `FirewallaClient.mute_alarm(self, gid: str, aid: str, *, target_type: str = "alarmType", target_value: str | None = None, scope_type: str = "all", scope_value: str | None = None) -> None`; `FirewallaClient.archive_alarm(self, gid: str, aid: str) -> None`; tools `mute_alarm(gid, aid, target_type="alarmType", target_value=None, scope_type="all", scope_value=None) -> str` and `archive_alarm(gid, aid) -> str`.

- [ ] **Step 1: Write the failing client tests**

Add `import json` to the top of `tests/test_client_alarms.py` (it currently imports only `httpx`, `respx` — `json` is NOT present and is needed below). Then add:
```python
@respx.mock
def test_mute_alarm_default_body():
    route = respx.post(
        "https://example.firewalla.net/v2/alarms/box-1/al-7/mute"
    ).mock(return_value=httpx.Response(200, json={}))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.mute_alarm("box-1", "al-7")

    assert route.called
    assert json.loads(route.calls.last.request.content) == {
        "target": {"type": "alarmType"},
        "scope": {"type": "all"},
    }


@respx.mock
def test_mute_alarm_domain_and_device_include_values():
    route = respx.post(
        "https://example.firewalla.net/v2/alarms/box-1/al-7/mute"
    ).mock(return_value=httpx.Response(200, json={}))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.mute_alarm(
        "box-1", "al-7",
        target_type="domain", target_value="ads.example.com",
        scope_type="device", scope_value="AA:BB:CC:DD:EE:FF",
    )

    assert json.loads(route.calls.last.request.content) == {
        "target": {"type": "domain", "value": "ads.example.com"},
        "scope": {"type": "device", "value": "AA:BB:CC:DD:EE:FF"},
    }


@respx.mock
def test_archive_alarm_posts_no_body():
    route = respx.post(
        "https://example.firewalla.net/v2/alarms/box-1/al-7/archive"
    ).mock(return_value=httpx.Response(200))
    client = FirewallaClient("example.firewalla.net", "tok")

    client.archive_alarm("box-1", "al-7")

    assert route.called
    assert route.calls.last.request.content in (b"", b"null")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_client_alarms.py -k "mute or archive" -v`
Expected: FAIL — no attribute `mute_alarm` / `archive_alarm`

- [ ] **Step 3: Implement the client methods**

In `src/firewalla_mcp/client.py`, immediately after `delete_alarm`:
```python
    def mute_alarm(
        self,
        gid: str,
        aid: str,
        *,
        target_type: str = "alarmType",
        target_value: str | None = None,
        scope_type: str = "all",
        scope_value: str | None = None,
    ) -> None:
        # POST /alarms/{gid}/{aid}/mute. target.type: 'alarmType'|'domain'
        # (value required for domain); scope.type: 'all'|'device' (value =
        # device MAC, required for device).
        target: dict = {"type": target_type}
        if target_value is not None:
            target["value"] = target_value
        scope: dict = {"type": scope_type}
        if scope_value is not None:
            scope["value"] = scope_value
        self._request(
            "POST",
            f"/alarms/{_quote(gid)}/{_quote(aid)}/mute",
            json={"target": target, "scope": scope},
            idempotent=False,
        )

    def archive_alarm(self, gid: str, aid: str) -> None:
        # POST /alarms/{gid}/{aid}/archive — no body; moves the alarm to the
        # archived state (keeps the record, unlike delete_alarm).
        self._request(
            "POST",
            f"/alarms/{_quote(gid)}/{_quote(aid)}/archive",
            idempotent=False,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_client_alarms.py -k "mute or archive" -v`
Expected: PASS (all 3)

- [ ] **Step 5: Add the MCP tools**

In `src/firewalla_mcp/server.py`, after the `delete_alarm` tool:
```python
@mcp.tool()
def mute_alarm(
    gid: str,
    aid: str,
    target_type: str = "alarmType",
    target_value: str | None = None,
    scope_type: str = "all",
    scope_value: str | None = None,
) -> str:
    """Mute an alarm so its future recurrences stop alerting (without a rule).
    Defaults mute THIS alarm's whole type, network-wide. `target_type`:
    'alarmType' (no value) or 'domain' (target_value = the domain). `scope_type`:
    'all' or 'device' (scope_value = device MAC)."""
    get_client().mute_alarm(
        gid, aid,
        target_type=target_type, target_value=target_value,
        scope_type=scope_type, scope_value=scope_value,
    )
    return f"Muted alarm {aid} on box {gid} (target={target_type}, scope={scope_type})"


@mcp.tool()
def archive_alarm(gid: str, aid: str) -> str:
    """Archive an alarm: dismiss it from the active list but KEEP the record
    (unlike delete_alarm, which is irreversible)."""
    get_client().archive_alarm(gid, aid)
    return f"Archived alarm {aid} on box {gid}"
```

- [ ] **Step 6: Register the tool names**

In `tests/test_server.py`, add `"mute_alarm",` and `"archive_alarm",` to `EXPECTED_TOOL_NAMES`.

- [ ] **Step 7: Run the full suite + lint**

Run: `uv run pytest -q && uv run ruff check`
Expected: all pass.

- [ ] **Step 8: Live-route verification (spec-mandated, read-only + one safe write check)**

These endpoints are tagged "MSP 2.11.0+" with no located GA note. Before trusting the write tools, confirm the routes exist against the live MSP. The launcher `~/.local/bin/firewalla-mcp-run.sh` holds the domain + token. Run a READ first to get a real `(gid, aid)`:
```bash
cd /home/djunt/firewalla-mcp
FIREWALLA_MSP_DOMAIN="dn-k6y7bj.firewalla.net" \
FIREWALLA_TOKEN="$(op read 'op://Homelab/Firewalla PAT/password')" \
uv run python -c "
from firewalla_mcp.client import FirewallaClient
import os
c = FirewallaClient(os.environ['FIREWALLA_MSP_DOMAIN'], os.environ['FIREWALLA_TOKEN'])
a = c.list_alarms(limit=1)
print('alarms sample:', a)
"
```
Interpretation: if a real alarm exists, note its gid+aid. Do NOT mute/archive a real alarm as a test unless Dave approves (it changes live state). A `404 route not found` shape from a deliberate bad-id probe vs a `400/valid` confirms the route exists. If either route returns a route-level 404 (endpoint absent, not "alarm not found"), STOP and report — mark that tool blocked pending the 2.11.0 rollout rather than shipping a dead tool.
Expected: `list_alarms` returns; routes present. Record the outcome in the task report.

- [ ] **Step 9: Commit**

```bash
git add src/firewalla_mcp/client.py src/firewalla_mcp/server.py tests/test_client_alarms.py tests/test_server.py
git commit -m "feat(alarms): add mute_alarm and archive_alarm tools"
```

---

### Task 5: Release 0.4.0

**Files:**
- Modify: `pyproject.toml` (version)
- Modify: `src/firewalla_mcp/__init__.py` (`__version__`)
- Modify/Create: `CHANGELOG.md`

**Interfaces:**
- Consumes: all six tools from Tasks 1–4.

**Note:** `test_version.py` asserts `firewalla_mcp.__version__ == importlib.metadata.version("firewalla-mcp")`. The version is hardcoded in TWO places — `pyproject.toml` (`version = "0.3.0"`) and `src/firewalla_mcp/__init__.py` (`__version__ = "0.3.0"`) — AND the installed editable-package metadata is read from the .dist-info generated at sync time. So all three must agree: bump both files, then re-sync so the metadata updates.

- [ ] **Step 1: Bump the version in both files**

In `pyproject.toml`, change `version = "0.3.0"` to `version = "0.4.0"`.
In `src/firewalla_mcp/__init__.py`, change `__version__ = "0.3.0"` to `__version__ = "0.4.0"`.

- [ ] **Step 2: Add the changelog entry**

Prepend to `CHANGELOG.md` (create with a `# Changelog` header if it does not exist):
```markdown
## 0.4.0

- feat(devices): `update_device` — rename a device (the only API-updatable field).
- feat(stats): `get_simple_stats` (dashboard rollup) and `get_stats` (top-N leaderboards).
- feat(trends): `get_rule_trends` — completes the flows/alarms/rules trend trio.
- feat(alarms): `mute_alarm` and `archive_alarm`.
- MSP `/v2` API parity: every documented endpoint is now wrapped. Import-target-list
  and FireAI remain out of scope (portal-only, no API).
```

- [ ] **Step 3: Re-sync the editable install so metadata matches**

Run: `uv sync`
Expected: re-installs `firewalla-mcp` at 0.4.0 so `importlib.metadata.version("firewalla-mcp")` returns `0.4.0`. (Without this, `test_version.py` fails because `__version__`=0.4.0 but the stale .dist-info still reports 0.3.0.)

- [ ] **Step 4: Full suite + lint**

Run: `uv run pytest -q && uv run ruff check`
Expected: all pass — `test_dunder_version_matches_package_metadata` green with 0.4.0 on both sides.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/firewalla_mcp/__init__.py CHANGELOG.md uv.lock
git commit -m "chore(release): v0.4.0 — MSP /v2 API parity (6 new tools)"
```

---

## Self-Review notes

- **Spec coverage:** all 6 endpoints (Tasks 1–4) + version/changelog (Task 5) + live-route verification for the 2.11.0 writes (Task 4 Step 8) + `EXPECTED_TOOL_NAMES` upkeep (every task). Out-of-scope items (import, FireAI, single-device GET) are correctly NOT tasks.
- **Type consistency:** `update_device(gid, device_id, name)`, `get_simple_stats(group)`, `get_stats(stats_type, group, limit)`, `get_rule_trends(group)`, `mute_alarm(gid, aid, target_type, target_value, scope_type, scope_value)`, `archive_alarm(gid, aid)` — identical across client, server, and tests.
- **Placeholder scan:** every code step shows complete code; no TBD/`add error handling`/`similar to`.
- **Version test:** `test_version.py` asserts `__version__` == installed metadata; Task 5 bumps both `pyproject.toml` and `__init__.py` and runs `uv sync` so the .dist-info matches. Missing any of the three breaks the test.
- **Live-data caveat:** Task 4 Step 8 is the one step that touches the real MSP; it is read-only by default and defers any real-alarm mutation to Dave.
