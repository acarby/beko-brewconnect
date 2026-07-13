"""coffee_sdk: Python SDK for Beko/Arcelik BrewConnect (HomeDirect) coffee machines.

Talks to the machine via the Tuya Cloud API (the same backend HomeDirect uses),
using credentials from a linked Tuya IoT Platform project rather than reverse
engineering the app's pinned MQTT channel.

Typical usage:

    import asyncio
    from coffee_sdk import login

    async def main():
        async with login(client_id, client_secret, region="eu") as client:
            machine = client.machine("bfda99b991844fcd78xgyt")
            status = await machine.status()
            print(status.work_state)
            await machine.make_espresso()

    asyncio.run(main())
"""

from __future__ import annotations

from coffee_sdk.client import TuyaCloudClient
from coffee_sdk.machine import CoffeeMachine

__all__ = ["CoffeeMachine", "TuyaCloudClient", "login"]


def login(client_id: str, client_secret: str, region: str = "eu") -> TuyaCloudClient:
    """Create a TuyaCloudClient. Use as an async context manager.

    Args:
        client_id: Tuya IoT Platform project Access ID.
        client_secret: Tuya IoT Platform project Access Secret.
        region: Tuya data center ("eu", "us", "cn", "in"). Beko/Arcelik
            HomeDirect devices are provisioned on "eu" (Central Europe DC).
    """
    return TuyaCloudClient(client_id, client_secret, region=region)
