"""Shared base entity for Beko BrewConnect, providing common device_info."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrewConnectCoordinator


class BrewConnectEntity(CoordinatorEntity[BrewConnectCoordinator]):
    """Base entity tying all platform entities to a single device registry entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BrewConnectCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="Beko BrewConnect",
            manufacturer="Beko / Arcelik",
            model="Full-Auto Espresso Machine (CEG7348X)",
        )
