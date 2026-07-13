"""Sensor entities for Beko BrewConnect."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coffee_sdk.models import Drink
from .coordinator import BrewConnectCoordinator, BrewConnectData
from .entity import BrewConnectEntity

DRINK_DISPLAY_NAMES: dict[Drink, str] = {
    Drink.ESPRESSO: "Espresso",
    Drink.AMERICANO: "Americano",
    Drink.LUNGO: "Lungo",
    Drink.CAFFE_LATTE: "Caffe Latte",
    Drink.LATTE_MACCHIATO: "Latte Macchiato",
    Drink.RISTRETTO: "Ristretto",
    Drink.DOPPIO: "Doppio",
    Drink.ESPRESSO_MACCHIATO: "Espresso Macchiato",
    Drink.RISTRETTO_BIANCO: "Ristretto Bianco",
    Drink.FLAT_WHITE: "Flat White",
    Drink.CORTADO: "Cortado",
    Drink.ICED_AMERICANO: "Iced Americano",
    Drink.ICED_LATTE: "Iced Latte",
    Drink.HOT_WATER: "Hot Water",
    Drink.HOT_MILK: "Hot Milk",
    Drink.TRAVEL_MUG: "Travel Mug",
    Drink.CAPPUCCINO: "Cappuccino",
}

WORK_STATE_LABELS = {
    "standby": "Standby",
    "power_save": "Power save",
    "warm_up": "Warming up",
    "brewing": "Brewing",
    "auto_clean": "Cleaning",
    "empty_device": "Emptying",
    "descaling": "Descaling",
    "reset": "Resetting",
}


@dataclass(frozen=True, kw_only=True)
class BrewConnectSensorDescription(SensorEntityDescription):
    value_fn: Callable[[BrewConnectData], object]


SENSOR_DESCRIPTIONS: tuple[BrewConnectSensorDescription, ...] = (
    BrewConnectSensorDescription(
        key="work_state",
        translation_key="work_state",
        value_fn=lambda data: WORK_STATE_LABELS.get(
            data.status.work_state.value, data.status.work_state.value
        ),
    ),
    BrewConnectSensorDescription(
        key="current_drink",
        translation_key="current_drink",
        value_fn=lambda data: (data.status.drink_set.value if data.status.drink_set else None),
    ),
    BrewConnectSensorDescription(
        key="drinks_made_total",
        translation_key="drinks_made_total",
        state_class="total_increasing",
        value_fn=lambda data: data.drinks_made_total,
    ),
    BrewConnectSensorDescription(
        key="last_drink",
        translation_key="last_drink",
        value_fn=lambda data: data.last_drink,
    ),
    BrewConnectSensorDescription(
        key="last_drink_at",
        translation_key="last_drink_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.last_drink_at,
    ),
    BrewConnectSensorDescription(
        key="water_hardness",
        translation_key="water_hardness",
        value_fn=lambda data: data.status.water_hardness,
    ),
    BrewConnectSensorDescription(
        key="mode",
        translation_key="mode",
        value_fn=lambda data: data.status.mode.value,
    ),
)


def _recipe_sensor_descriptions() -> tuple[BrewConnectSensorDescription, ...]:
    """Water/milk/total ml sensors for every drink's saved recipe.

    Generated per-drink so each shows as its own row on the device page
    (a button entity's extra_state_attributes are not visible there).
    Values come live from the device's currently active profile -- see
    Protocol.md#per-drink-recipe-data.
    """
    descriptions = []
    for drink, display_name in DRINK_DISPLAY_NAMES.items():
        key_base = drink.value.lower()
        for field, label, attr in (
            ("water_ml", "Water", "water_ml"),
            ("milk_ml", "Milk", "milk_ml"),
            ("total_ml", "Total", "total_ml"),
        ):
            descriptions.append(
                BrewConnectSensorDescription(
                    key=f"recipe_{key_base}_{field}",
                    name=f"{display_name} {label} Volume",
                    device_class=SensorDeviceClass.VOLUME,
                    native_unit_of_measurement=UnitOfVolume.MILLILITERS,
                    value_fn=lambda data, d=drink, a=attr: (
                        getattr(recipe, a) if (recipe := data.status.recipe_for(d)) else None
                    ),
                )
            )
    return tuple(descriptions)


RECIPE_SENSOR_DESCRIPTIONS: tuple[BrewConnectSensorDescription, ...] = _recipe_sensor_descriptions()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: BrewConnectCoordinator = entry.runtime_data
    async_add_entities(
        BrewConnectSensor(coordinator, description)
        for description in (*SENSOR_DESCRIPTIONS, *RECIPE_SENSOR_DESCRIPTIONS)
    )


class BrewConnectSensor(BrewConnectEntity, SensorEntity):
    entity_description: BrewConnectSensorDescription

    def __init__(
        self, coordinator: BrewConnectCoordinator, description: BrewConnectSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
