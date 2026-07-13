"""Binary sensor entities for Beko BrewConnect (water/beans/grounds/faults)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BrewConnectCoordinator, BrewConnectData
from .entity import BrewConnectEntity


@dataclass(frozen=True, kw_only=True)
class BrewConnectBinarySensorDescription(BinarySensorEntityDescription):
    is_on_fn: Callable[[BrewConnectData], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[BrewConnectBinarySensorDescription, ...] = (
    BrewConnectBinarySensorDescription(
        key="water_empty",
        translation_key="water_empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.status.water_empty,
    ),
    BrewConnectBinarySensorDescription(
        key="bean_container_empty",
        translation_key="bean_container_empty",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.status.bean_container_empty,
    ),
    BrewConnectBinarySensorDescription(
        key="grounds_full",
        translation_key="grounds_full",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.status.grounds_full,
    ),
    BrewConnectBinarySensorDescription(
        key="front_door_open",
        translation_key="front_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
        is_on_fn=lambda data: "Frontdoor_open" in {f.value for f in data.status.faults},
    ),
    BrewConnectBinarySensorDescription(
        key="needs_attention",
        translation_key="needs_attention",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=lambda data: data.status.needs_attention,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: BrewConnectCoordinator = entry.runtime_data
    async_add_entities(
        BrewConnectBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class BrewConnectBinarySensor(BrewConnectEntity, BinarySensorEntity):
    entity_description: BrewConnectBinarySensorDescription

    def __init__(
        self,
        coordinator: BrewConnectCoordinator,
        description: BrewConnectBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.coordinator.data)
