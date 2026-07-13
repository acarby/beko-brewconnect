import httpx
import pytest
import respx

from coffee_sdk import TuyaCloudClient
from coffee_sdk.exceptions import APIError

BASE = "https://openapi.tuyaeu.com"


def _token_route(mock: respx.MockRouter, access_token: str = "tok-1") -> None:
    mock.get(url__regex=rf"{BASE}/v1\.0/token\?grant_type=1").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "access_token": access_token,
                    "refresh_token": "refresh-1",
                    "expire_time": 7200,
                },
            },
        )
    )


@pytest.mark.asyncio
async def test_get_device_status():
    async with respx.mock(base_url=BASE) as mock:
        _token_route(mock)
        mock.get(url__regex=r".*/v1\.0/devices/dev123/status").mock(
            return_value=httpx.Response(
                200,
                json={"success": True, "result": [{"code": "switch", "value": True}]},
            )
        )
        async with TuyaCloudClient("id", "secret", region="eu") as client:
            data = await client.get("/v1.0/devices/dev123/status")
            assert data["result"] == [{"code": "switch", "value": True}]


@pytest.mark.asyncio
async def test_send_command():
    async with respx.mock(base_url=BASE) as mock:
        _token_route(mock)
        route = mock.post(url__regex=r".*/v1\.0/devices/dev123/commands").mock(
            return_value=httpx.Response(200, json={"success": True, "result": True})
        )
        async with TuyaCloudClient("id", "secret", region="eu") as client:
            machine = client.machine("dev123")
            await machine.power_on()
        assert route.called
        sent_body = route.calls[0].request.content
        assert b'"switch"' in sent_body
        assert b"true" in sent_body


@pytest.mark.asyncio
async def test_api_error_raised_on_failure():
    async with respx.mock(base_url=BASE) as mock:
        _token_route(mock)
        mock.get(url__regex=r".*/v1\.0/devices/dev123/status").mock(
            return_value=httpx.Response(
                200, json={"success": False, "code": 2010, "msg": "device not found"}
            )
        )
        async with TuyaCloudClient("id", "secret", region="eu") as client:
            with pytest.raises(APIError) as exc_info:
                await client.get("/v1.0/devices/dev123/status")
            assert exc_info.value.code == 2010


@pytest.mark.asyncio
async def test_stale_token_triggers_retry():
    async with respx.mock(base_url=BASE) as mock:
        _token_route(mock)
        route = mock.get(url__regex=r".*/v1\.0/devices/dev123/status")
        route.side_effect = [
            httpx.Response(200, json={"success": False, "code": 1010, "msg": "token invalid"}),
            httpx.Response(200, json={"success": True, "result": []}),
        ]
        async with TuyaCloudClient("id", "secret", region="eu") as client:
            data = await client.get("/v1.0/devices/dev123/status")
            assert data["success"] is True
