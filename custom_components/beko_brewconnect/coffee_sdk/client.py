"""Low-level async client for the Tuya Cloud API (Central Europe data center)."""

from __future__ import annotations

import asyncio
import logging
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

import httpx

from .auth import TuyaAuth, sign_request
from .exceptions import APIError

if TYPE_CHECKING:
    from .machine import CoffeeMachine

logger = logging.getLogger(__name__)

# Data-center base URLs, per https://developer.tuya.com/en/docs/iot/api-request
DATA_CENTERS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}

DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5


class TuyaCloudClient:
    """Signed, retrying, token-managed HTTP client for Tuya Cloud API calls.

    Usage:
        async with TuyaCloudClient(client_id, secret, region="eu") as client:
            status = await client.get(f"/v1.0/devices/{device_id}/status")
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        region: str = "eu",
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a Tuya Cloud client.

        Args:
            http_client: An existing httpx.AsyncClient to use instead of
                creating one. Pass this when embedding in an application
                (e.g. Home Assistant) that already manages a shared client
                off the event loop -- constructing httpx.AsyncClient() does
                blocking SSL cert loading, which is unsafe to do inline in
                an async context. When omitted, this instance owns and
                closes its own client.
        """
        if region not in DATA_CENTERS:
            raise ValueError(f"Unknown region {region!r}; choose one of {sorted(DATA_CENTERS)}")
        self._base_url = DATA_CENTERS[region]
        self._owns_http_client = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient(timeout=timeout)
        self._auth = TuyaAuth(client_id, client_secret, self._base_url, self._http)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    async def _request(
        self, method: str, path_and_query: str, json_body: dict | None = None
    ) -> dict[str, Any]:
        raw_body = b"" if json_body is None else _dumps(json_body)

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            token = await self._auth.get_valid_access_token()
            sign, t = sign_request(
                self._auth.client_id,
                self._auth.secret,
                method,
                path_and_query,
                raw_body,
                access_token=token,
            )
            headers = {
                "client_id": self._auth.client_id,
                "access_token": token,
                "sign": sign,
                "t": str(t),
                "sign_method": "HMAC-SHA256",
                "Content-Type": "application/json",
            }
            url = self._base_url + path_and_query
            try:
                resp = await self._http.request(
                    method, url, headers=headers, content=raw_body or None
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Tuya API request failed (attempt %s/%s): %s", attempt, MAX_RETRIES, exc
                )
                await asyncio.sleep(RETRY_BACKOFF_BASE * attempt)
                continue

            if not data.get("success", False):
                code = data.get("code", -1)
                msg = data.get("msg", "unknown error")
                # 1010/1011-ish codes indicate a stale token; refresh and retry once more.
                if code in {1010, 1011} and attempt < MAX_RETRIES:
                    logger.info("Tuya token rejected (code %s); retrying with fresh token", code)
                    continue
                raise APIError(code, msg)

            return data

        assert last_error is not None
        raise APIError(-1, f"request failed after {MAX_RETRIES} attempts: {last_error}")

    async def get(self, path_and_query: str) -> dict[str, Any]:
        return await self._request("GET", path_and_query)

    async def post(self, path_and_query: str, json_body: dict) -> dict[str, Any]:
        return await self._request("POST", path_and_query, json_body)

    def machine(self, device_id: str) -> CoffeeMachine:
        """Return a CoffeeMachine bound to this client for the given device id."""
        from .machine import CoffeeMachine

        return CoffeeMachine(self, device_id)


def _dumps(obj: dict) -> bytes:
    import json

    return json.dumps(obj, separators=(",", ":")).encode()
