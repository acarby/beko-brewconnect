"""High-level API for a single Beko BrewConnect coffee machine."""

from __future__ import annotations

import logging

from coffee_sdk.client import TuyaCloudClient
from coffee_sdk.drinks import (
    AMERICANO,
    CAFFE_LATTE,
    CAPPUCCINO,
    DOUBLE_ESPRESSO,
    ESPRESSO,
    FLAT_WHITE,
    LATTE_MACCHIATO,
    DrinkCommand,
)
from coffee_sdk.exceptions import DeviceOfflineError
from coffee_sdk.models import DeviceInfo, MachineStatus

logger = logging.getLogger(__name__)


class CoffeeMachine:
    """Represents one physical coffee machine, identified by its Tuya device id."""

    def __init__(self, client: TuyaCloudClient, device_id: str) -> None:
        self._client = client
        self.device_id = device_id

    async def info(self) -> DeviceInfo:
        data = await self._client.get(f"/v1.0/devices/{self.device_id}")
        result = data["result"]
        return DeviceInfo(
            id=result["id"],
            name=result["name"],
            product_id=result["product_id"],
            product_name=result.get("product_name", ""),
            online=result["online"],
            category=result.get("category", ""),
            ip=result.get("ip"),
        )

    async def status(self) -> MachineStatus:
        """Fetch the machine's current DP status."""
        data = await self._client.get(f"/v1.0/devices/{self.device_id}/status")
        return MachineStatus.from_dp_status(data["result"])

    async def _send_commands(self, commands: list[dict]) -> None:
        logger.debug("Sending commands to %s: %s", self.device_id, commands)
        await self._client.post(f"/v1.0/devices/{self.device_id}/commands", {"commands": commands})

    async def _send_command(self, code: str, value: bool | str | int) -> None:
        await self._send_commands([{"code": code, "value": value}])

    async def _ensure_online(self) -> None:
        info = await self.info()
        if not info.online:
            raise DeviceOfflineError(f"Device {self.device_id} is reported offline")

    # -- power --------------------------------------------------------------

    async def power_on(self) -> None:
        await self._send_command("switch", True)

    async def power_off(self) -> None:
        await self._send_command("switch", False)

    async def start(self) -> None:
        """Start whichever operation (drink/clean/descale) is currently armed."""
        await self._send_command("start", True)

    async def stop(self) -> None:
        """Cancel the current operation."""
        await self._send_command("start", False)

    # -- brewing --------------------------------------------------------------

    async def brew(self, command: DrinkCommand) -> None:
        """Send a full drink recipe (drink type + modifiers) and start brewing."""
        await self._ensure_online()
        await self._send_commands(command.to_dp_commands())

    async def make_espresso(self) -> None:
        await self.brew(ESPRESSO)

    async def make_double(self) -> None:
        await self.brew(DOUBLE_ESPRESSO)

    async def make_americano(self) -> None:
        await self.brew(AMERICANO)

    async def make_latte(self) -> None:
        await self.brew(CAFFE_LATTE)

    async def make_latte_macchiato(self) -> None:
        await self.brew(LATTE_MACCHIATO)

    async def make_flat_white(self) -> None:
        await self.brew(FLAT_WHITE)

    async def make_cappuccino(self) -> None:
        await self.brew(CAPPUCCINO)

    # -- maintenance --------------------------------------------------------------

    async def clean(self) -> None:
        """Trigger the auto-clean cycle."""
        await self._send_command("auto_clean", True)

    async def rinse(self) -> None:
        await self._send_command("rinsing_clean", True)

    async def clean_milk_cup(self) -> None:
        await self._send_command("milk_cupclean", True)

    async def descale(self) -> None:
        await self._send_command("descaling", True)

    async def empty_device(self) -> None:
        await self._send_command("empty_device", True)

    # -- sensors --------------------------------------------------------------
    # NOTE: the device only exposes boolean empty/full fault flags, not
    # continuous fill-level percentages, per the Tuya DP schema.

    async def water_level_ok(self) -> bool:
        """True if the water tank is NOT reported empty."""
        status = await self.status()
        return not status.water_empty

    async def bean_level_ok(self) -> bool:
        """True if the bean container is NOT reported empty."""
        status = await self.status()
        return not status.bean_container_empty

    async def grounds_full(self) -> bool:
        status = await self.status()
        return status.grounds_full
