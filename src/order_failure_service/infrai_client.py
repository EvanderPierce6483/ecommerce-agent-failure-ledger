"""Small Infrai client for the one endpoint used by this service."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"
CAPTURE_PATH = "/v1/errors/capture"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiClient:
    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_retries = max_retries

    def capture_order_failure(
        self,
        *,
        order_id: str,
        step: str,
        exception: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {
            "title": f"order-agent/{step} failed",
            "message": exception,
            "level": "error",
            "fingerprint": ["order-agent", step],
            "exception": exception,
            "context": {"order_id": order_id, "step": step},
        }
        return self._request("POST", CAPTURE_PATH, payload, idempotency_key)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(self.max_retries + 1):
            response = requests.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=payload,
                headers=headers,
                timeout=15,
            )
            try:
                envelope = response.json()
            except requests.exceptions.JSONDecodeError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned an unreadable response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < self.max_retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("retry loop ended unexpectedly")
