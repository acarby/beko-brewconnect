"""Tuya Cloud API request signing and access-token lifecycle.

Implements Tuya's HMAC-SHA256 request signing scheme as documented at
https://developer.tuya.com/en/docs/iot/new-singnature. Two sign flavours
are needed:

  * "token" signing  (client_id + t + stringToSign)          -> used only
    to fetch the initial access token.
  * "business" signing (client_id + access_token + t + stringToSign) -> used
    for every authenticated call afterwards.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass

import httpx

from coffee_sdk.exceptions import AuthenticationError, TokenExpiredError

logger = logging.getLogger(__name__)

EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    expire_at: float  # unix timestamp

    @property
    def is_expired(self) -> bool:
        # refresh 60s early to avoid racing the real expiry
        return time.time() >= (self.expire_at - 60)


def _content_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest() if body else EMPTY_BODY_SHA256


def _string_to_sign(method: str, url_path_and_query: str, body: bytes) -> str:
    return "\n".join([method.upper(), _content_sha256(body), "", url_path_and_query])


def sign_request(
    client_id: str,
    secret: str,
    method: str,
    url_path_and_query: str,
    body: bytes = b"",
    access_token: str | None = None,
    t: int | None = None,
) -> tuple[str, int]:
    """Return (sign, timestamp_ms) for a Tuya Cloud API request."""
    t = t if t is not None else int(time.time() * 1000)
    str_to_sign = _string_to_sign(method, url_path_and_query, body)
    prefix = client_id + (access_token or "") + str(t)
    message = prefix + str_to_sign
    sign = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest().upper()
    return sign, t


class TuyaAuth:
    """Handles fetching and transparently refreshing Tuya Cloud access tokens."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._client_id = client_id
        self._secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._http = http_client
        self._tokens: TokenSet | None = None

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def secret(self) -> str:
        return self._secret

    async def get_valid_access_token(self) -> str:
        if self._tokens is None or self._tokens.is_expired:
            if self._tokens is not None:
                await self._refresh()
            else:
                await self._login()
        assert self._tokens is not None
        return self._tokens.access_token

    async def _login(self) -> None:
        path = "/v1.0/token?grant_type=1"
        sign, t = sign_request(self._client_id, self._secret, "GET", path)
        headers = {
            "client_id": self._client_id,
            "sign": sign,
            "t": str(t),
            "sign_method": "HMAC-SHA256",
        }
        resp = await self._http.get(self._base_url + path, headers=headers)
        data = resp.json()
        if not data.get("success"):
            raise AuthenticationError(f"Tuya login failed: {data.get('code')} {data.get('msg')}")
        result = data["result"]
        self._tokens = TokenSet(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expire_at=time.time() + result["expire_time"],
        )
        logger.info("Obtained new Tuya access token (expires in %ss)", result["expire_time"])

    async def _refresh(self) -> None:
        assert self._tokens is not None
        path = f"/v1.0/token/{self._tokens.refresh_token}"
        sign, t = sign_request(self._client_id, self._secret, "GET", path)
        headers = {
            "client_id": self._client_id,
            "sign": sign,
            "t": str(t),
            "sign_method": "HMAC-SHA256",
        }
        resp = await self._http.get(self._base_url + path, headers=headers)
        data = resp.json()
        if not data.get("success"):
            logger.warning(
                "Tuya token refresh failed (%s), falling back to full login", data.get("code")
            )
            try:
                await self._login()
            except AuthenticationError as exc:
                raise TokenExpiredError(str(exc)) from exc
            return
        result = data["result"]
        self._tokens = TokenSet(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expire_at=time.time() + result["expire_time"],
        )
        logger.info("Refreshed Tuya access token")
