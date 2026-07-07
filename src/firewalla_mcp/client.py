import time

import httpx

MAX_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5


class FirewallaAPIError(Exception):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Firewalla API error {status_code}: {body}")


class FirewallaNotFoundError(Exception):
    pass


class FirewallaClient:
    def __init__(self, msp_domain: str, token: str, http_client: httpx.Client | None = None):
        self._http = http_client or httpx.Client(
            base_url=f"https://{msp_domain}/v2",
            headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
            timeout=10.0,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> httpx.Response:
        last_error: FirewallaAPIError | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._http.request(method, path, params=params, json=json)
            except httpx.TransportError as exc:
                last_error = FirewallaAPIError(0, str(exc))
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                raise last_error from exc

            if response.status_code >= 500:
                last_error = FirewallaAPIError(response.status_code, response.text)
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                raise last_error

            if response.status_code >= 400:
                raise FirewallaAPIError(response.status_code, response.text)

            return response

        assert last_error is not None
        raise last_error

    def list_boxes(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._request("GET", "/boxes", params=params).json()

    def get_box(self, gid: str) -> dict:
        for box in self.list_boxes():
            if box["gid"] == gid:
                return box
        raise FirewallaNotFoundError(f"box {gid} not found")

    def list_devices(self, box: str | None = None, group: str | None = None) -> list[dict]:
        params = {}
        if box:
            params["box"] = box
        if group:
            params["group"] = group
        return self._request("GET", "/devices", params=params or None).json()

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
        return self._request("GET", "/alarms", params=params).json()

    def get_alarm(self, gid: str, aid: str) -> dict:
        return self._request("GET", f"/alarms/{gid}/{aid}").json()

    def delete_alarm(self, gid: str, aid: str) -> None:
        self._request("DELETE", f"/alarms/{gid}/{aid}")

    def list_rules(self, query: str | None = None) -> dict:
        params = {"query": query} if query else None
        return self._request("GET", "/rules", params=params).json()

    def create_rule(self, rule: dict) -> dict:
        return self._request("POST", "/rules", json=rule).json()

    def pause_rule(self, rule_id: str) -> None:
        self._request("POST", f"/rules/{rule_id}/pause")

    def resume_rule(self, rule_id: str) -> None:
        self._request("POST", f"/rules/{rule_id}/resume")

    def delete_rule(self, rule_id: str) -> None:
        self._request("DELETE", f"/rules/{rule_id}")

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
        return self._request("GET", "/flows", params=params).json()

    def get_flow_trends(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._request("GET", "/trends/flows", params=params).json()

    def get_alarm_trends(self, group: str | None = None) -> list[dict]:
        params = {"group": group} if group else None
        return self._request("GET", "/trends/alarms", params=params).json()

    def list_target_lists(self, owner: str | None = None) -> list[dict]:
        params = {"owner": owner} if owner else None
        return self._request("GET", "/target-lists", params=params).json()

    def get_target_list(self, list_id: str) -> dict:
        return self._request("GET", f"/target-lists/{list_id}").json()

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
        return self._request("POST", "/target-lists", json=body).json()

    def update_target_list(self, list_id: str, **fields) -> dict:
        return self._request("PATCH", f"/target-lists/{list_id}", json=fields).json()

    def delete_target_list(self, list_id: str) -> None:
        self._request("DELETE", f"/target-lists/{list_id}")
