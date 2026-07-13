"""Button entities for Beko BrewConnect: quick-make drinks and maintenance actions."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coffee_sdk.machine import CoffeeMachine
from .coffee_sdk.models import Drink
from .coordinator import BrewConnectCoordinator
from .entity import BrewConnectEntity


@dataclass(frozen=True, kw_only=True)
class BrewConnectButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[CoffeeMachine], Coroutine[Any, Any, None]]
    drink: Drink | None = None


BUTTON_DESCRIPTIONS: tuple[BrewConnectButtonDescription, ...] = (
    BrewConnectButtonDescription(
        key="espresso",
        translation_key="espresso",
        press_fn=lambda m: m.make_espresso(),
        drink=Drink.ESPRESSO,
    ),
    BrewConnectButtonDescription(
        key="double_espresso",
        translation_key="double_espresso",
        press_fn=lambda m: m.make_double(),
        drink=Drink.ESPRESSO,
    ),
    BrewConnectButtonDescription(
        key="americano",
        translation_key="americano",
        press_fn=lambda m: m.make_americano(),
        drink=Drink.AMERICANO,
    ),
    BrewConnectButtonDescription(
        key="latte",
        translation_key="latte",
        press_fn=lambda m: m.make_latte(),
        drink=Drink.CAFFE_LATTE,
    ),
    BrewConnectButtonDescription(
        key="flat_white",
        translation_key="flat_white",
        press_fn=lambda m: m.make_flat_white(),
        drink=Drink.FLAT_WHITE,
    ),
    BrewConnectButtonDescription(
        key="cappuccino",
        translation_key="cappuccino",
        press_fn=lambda m: m.make_cappuccino(),
        drink=Drink.CAPPUCCINO,
    ),
    BrewConnectButtonDescription(
        key="stop",
        translation_key="stop",
        press_fn=lambda m: m.stop(),
    ),
    BrewConnectButtonDescription(
        key="rinse",
        translation_key="rinse",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda m: m.rinse(),
    ),
    BrewConnectButtonDescription(
        key="clean",
        translation_key="clean",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda m: m.clean(),
    ),
    BrewConnectButtonDescription(
        key="clean_milk_cup",
        translation_key="clean_milk_cup",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda m: m.clean_milk_cup(),
    ),
    BrewConnectButtonDescription(
        key="descale",
        translation_key="descale",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda m: m.descale(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: BrewConnectCoordinator = entry.runtime_data
    async_add_entities(
        BrewConnectButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )


class BrewConnectButton(BrewConnectEntity, ButtonEntity):
    entity_description: BrewConnectButtonDescription

    def __init__(
        self, coordinator: BrewConnectCoordinator, description: BrewConnectButtonDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator.machine)
        if self.entity_description.drink is not None:
            await self.coordinator.async_record_drink(self.entity_description.drink)
        else:
            await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Recipe info (ml, milk requirement) for drink buttons.

        Sourced from the machine's own saved recipe for the active user
        profile -- see Protocol.md for how this is decoded. Not available
        for non-drink buttons (stop/rinse/clean/descale).
        """
        drink = self.entity_description.drink
        if drink is None:
            return None
        recipe = self.coordinator.data.status.recipe_for(drink)
        if recipe is None:
            return None
        return {
            "water_ml": recipe.water_ml,
            "milk_ml": recipe.milk_ml,
            "total_ml": recipe.total_ml,
            "needs_milk": recipe.needs_milk,
            "strength": recipe.strength.value,
            "high_temperature": recipe.high_temperature,
        }
