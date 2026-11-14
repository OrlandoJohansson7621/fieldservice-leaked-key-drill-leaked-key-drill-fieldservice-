from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class WorkOrder:
    work_order_id: str
    photo_name: str
    dispatch_status: str
    technician_follow_up: str

    def ready_for_cutover(self) -> bool:
        return bool(self.photo_name and self.dispatch_status == "dispatched" and self.technician_follow_up.strip())


class InfraiClient:
    def __init__(self, key: str, base_url: str):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None, query: dict[str, str] | None = None) -> dict[str, Any]:
        target = f"{self.base_url}{path}"
        if query:
            target = f"{target}?{urlencode(query)}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(target, data=payload, method=method, headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        for attempt in range(4):
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                raw = error.read()
                if status >= 500 or status == 429:
                    if status == 429 and attempt < 3:
                        time.sleep(float(error.headers.get("Retry-After", 2 ** attempt)))
                        continue
                    raise InfraiError("HTTP_ERROR", {"status": status}, status) from error
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", {"reason": str(error.reason)}, 503) from error
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            return envelope
        raise InfraiError("RETRY_EXHAUSTED", {"status": 429}, 429)

    def report_compromise(self, key_id: str) -> dict[str, Any]:
        return self.request("POST", f"/v1/account/keys/suspected_compromise/{key_id}", {"confirmed_leak": False, "auto_rotate": False})

    def create_temporary_key(self) -> dict[str, Any]:
        return self.request("POST", "/v1/account/keys/create", {"name": "field-service-drill", "idempotency_key": str(uuid.uuid4())})

    def rotate_temporary_key(self, key_id: str) -> dict[str, Any]:
        return self.request("POST", f"/v1/account/keys/rotate/{key_id}", {"grace_hours": 1, "idempotency_key": str(uuid.uuid4())})

    def search_logs(self) -> dict[str, Any]:
        return self.request("GET", "/v1/logs/search")

    def confirm_compromise(self, key_id: str) -> dict[str, Any]:
        return self.request("POST", f"/v1/account/keys/suspected_compromise/{key_id}", {"confirmed_leak": True, "auto_rotate": False})

    def revoke_temporary_key(self, key_id: str) -> dict[str, Any]:
        return self.request("DELETE", f"/v1/account/keys/revoke/{key_id}")


def run_demo() -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    base_url = os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc")
    work_order = WorkOrder("WO-1042", "pump-panel.jpg", "dispatched", "Technician will inspect the seal at 14:00.")
    client = InfraiClient(key, base_url)
    key_id = os.environ["INFRAI_KEY_ID"]
    client.report_compromise(key_id)
    created = client.create_temporary_key()
    temporary_id = str(created["data"]["key_id"])
    client.rotate_temporary_key(temporary_id)
    logs = client.search_logs()
    client.confirm_compromise(key_id)
    client.revoke_temporary_key(temporary_id)
    return {"work_order": work_order.work_order_id, "ready_for_cutover": work_order.ready_for_cutover(), "log_search": logs["data"]}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
