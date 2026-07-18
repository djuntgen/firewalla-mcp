import time
from urllib.parse import quote

import httpx

MAX_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5
MAX_RETRY_AFTER_SECONDS = 10
MAX_ERROR_BODY_CHARS = 500

# Fields accepted when creating a rule. The MSP API has no rule-update
# endpoint, so update_rule() recreates a rule from its current state; only
# these fields are carried over (server-managed ones like id/ts/hit are dropped).
RULE_CREATE_FIELDS = frozenset(
    {
        "action",
        "target",
        "direction",
        "gid",
        "group",
        "scope",
        "notes",
        "schedule",
        "protocol",
        "status",
    }
)


def _quote(segment: str) -> str:
    return quote(segment, safe="")


def _truncate(body: str) -> str:
    if len(body) > MAX_ERROR_BODY_CHARS:
        return body[:MAX_ERROR_BODY_CHARS] + " ... (truncated)"
    return body


def _retry_after_seconds(response: httpx.Response) -> float:
    try:
        seconds = float(response.headers.get("Retry-After", ""))
    except ValueError:
        return RETRY_BACKOFF_SECONDS
    return min(max(seconds, 0.0), float(MAX_RETRY_AFTER_SECONDS))


class FirewallaError(Exception):
    pass


class FirewallaAPIError(FirewallaError):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = _truncate(body)
        super().__init__(f"Firewalla API error {status_code}: {self.body}")


class FirewallaNotFoundError(FirewallaError):
    pass


class FirewallaClient:
    def __init__(
        self,
        msp_domain: str,
        token: str,
        http_client: httpx.Client | None = None,
        timeout: float = 10.0,
    ):
        self._http = http_client or httpx.Client(
            base_url=f"https://{msp_domain}/v2",
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
        idempotent: bool = True,
    ) -> httpx.Response:
        last_error: FirewallaAPIError | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._http.request(method, path, params=params, json=json)
            except httpx.TransportError as exc:
                # A transport error (e.g. read timeout) may mean the server already
                # processed the request, so only idempotent requests are retried.
                last_error = FirewallaAPIError(0, str(exc))
                if idempotent and attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                raise last_error from exc

            if response.status_code == 429:
                # A rate-limited request was rejected before processing, so it is
                # safe to retry even non-idempotent writes.
                last_error = FirewallaAPIError(429, response.text)
                if attempt < MAX_ATTEMPTS:
                    time.sleep(_retry_after_seconds(response))
                    continue
                raise last_error

            if response.status_code >= 500:
                last_error = FirewallaAPIError(response.status_code, response.text)
                if idempotent and attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                raise last_error

            if response.status_code >= 400:
                raise FirewallaAPIError(response.status_code, response.text)

            return response

        assert last_error is not None
        raise last_error

    def _json(self, response: httpx.Response):
        try:
            return response.json()
        except ValueError as exc:
            raise FirewallaAPIError(
                response.status_code,
                f"expected JSON but got a non-JSON response: {response.text}",
            ) from exc

    def list_boxes(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._json(self._request("GET", "/boxes", params=params))

    def get_box(self, gid: str) -> dict:
        for box in self.list_boxes():
            if box["gid"] == gid:
                return box
        raise FirewallaNotFoundError(f"box {gid} not found")

    def list_devices(
        self, box: str | None = None, group: str | None = None
    ) -> list[dict]:
        params = {}
        if box:
            params["box"] = box
        if group:
            params["group"] = group
        return self._json(self._request("GET", "/devices", params=params or None))

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

    def list_alarms(
        self,
        query: str | None = None,
        group_by: str | None = None,
        sort_by: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit}
        if query:
            params["query"] = query
        if group_by:
            params["groupBy"] = group_by
        if sort_by:
            params["sortBy"] = sort_by
        if cursor:
            params["cursor"] = cursor
        return self._json(self._request("GET", "/alarms", params=params))

    def get_alarm(self, gid: str, aid: str) -> dict:
        return self._json(self._request("GET", f"/alarms/{_quote(gid)}/{_quote(aid)}"))

    def delete_alarm(self, gid: str, aid: str) -> None:
        self._request("DELETE", f"/alarms/{_quote(gid)}/{_quote(aid)}")

    def list_rules(self, query: str | None = None) -> dict:
        params = {"query": query} if query else None
        return self._json(self._request("GET", "/rules", params=params))

    def create_rule(self, rule: dict) -> dict:
        return self._json(self._request("POST", "/rules", json=rule, idempotent=False))

    def get_rule(self, rule_id: str) -> dict:
        for rule in self.list_rules().get("results", []):
            if rule.get("id") == rule_id:
                return rule
        raise FirewallaNotFoundError(f"rule {rule_id} not found")

    def update_rule(self, rule_id: str, changes: dict) -> dict:
        # The MSP API has no rule-update endpoint, so "edit" means recreate:
        # build a fresh rule from the current one plus the caller's changes,
        # create it FIRST (so a failure never loses the rule), then delete the
        # original. The new rule gets a new id.
        current = self.get_rule(rule_id)
        body = {k: v for k, v in current.items() if k in RULE_CREATE_FIELDS}
        body.update(changes)
        new_rule = self.create_rule(body)
        self.delete_rule(rule_id)
        return {"deleted_id": rule_id, "rule": new_rule}

    def pause_rule(self, rule_id: str) -> None:
        self._request("POST", f"/rules/{_quote(rule_id)}/pause")

    def resume_rule(self, rule_id: str) -> None:
        self._request("POST", f"/rules/{_quote(rule_id)}/resume")

    def delete_rule(self, rule_id: str) -> None:
        self._request("DELETE", f"/rules/{_quote(rule_id)}")

    def list_flows(
        self,
        query: str | None = None,
        group_by: str | None = None,
        sort_by: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit}
        if query:
            params["query"] = query
        if group_by:
            params["groupBy"] = group_by
        if sort_by:
            params["sortBy"] = sort_by
        if cursor:
            params["cursor"] = cursor
        return self._json(self._request("GET", "/flows", params=params))

    def get_flow_trends(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._json(self._request("GET", "/trends/flows", params=params))

    def get_alarm_trends(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._json(self._request("GET", "/trends/alarms", params=params))

    def list_target_lists(self, owner: str | None = None) -> list[dict]:
        params = {"owner": owner} if owner else None
        return self._json(self._request("GET", "/target-lists", params=params))

    def get_target_list(self, list_id: str) -> dict:
        return self._json(self._request("GET", f"/target-lists/{_quote(list_id)}"))

    def create_target_list(
        self,
        name: str,
        targets: list[str],
        owner: str | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> dict:
        body: dict = {"name": name, "targets": targets}
        if owner:
            body["owner"] = owner
        if category:
            body["category"] = category
        if notes:
            body["notes"] = notes
        return self._json(
            self._request("POST", "/target-lists", json=body, idempotent=False)
        )

    def update_target_list(self, list_id: str, **fields) -> dict:
        return self._json(
            self._request("PATCH", f"/target-lists/{_quote(list_id)}", json=fields)
        )

    def delete_target_list(self, list_id: str) -> None:
        self._request("DELETE", f"/target-lists/{_quote(list_id)}")
