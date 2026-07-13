"""Helpers for turning a drink request into the right set of DP commands.

The device brews via `drink_set` (choose the recipe) + `start` (trigger it),
with `double` as an independent modifier DP rather than a separate drink
value. This module centralises that mapping so machine.py stays declarative.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from coffee_sdk.models import Drink


@dataclass(frozen=True)
class DrinkCommand:
    """The DP command sequence required to brew a given drink."""

    drink: Drink
    double: bool = False
    extra_dps: dict[str, bool] = field(default_factory=dict)

    def to_dp_commands(self) -> list[dict]:
        commands = [
            {"code": "drink_set", "value": self.drink.value},
            {"code": "double", "value": self.double},
        ]
        for code, value in self.extra_dps.items():
            commands.append({"code": code, "value": value})
        commands.append({"code": "start", "value": True})
        return commands


ESPRESSO = DrinkCommand(Drink.ESPRESSO)
DOUBLE_ESPRESSO = DrinkCommand(Drink.ESPRESSO, double=True)
AMERICANO = DrinkCommand(Drink.AMERICANO)
LUNGO = DrinkCommand(Drink.LUNGO)
RISTRETTO = DrinkCommand(Drink.RISTRETTO)
DOPPIO = DrinkCommand(Drink.DOPPIO)
CAFFE_LATTE = DrinkCommand(Drink.CAFFE_LATTE)
LATTE_MACCHIATO = DrinkCommand(Drink.LATTE_MACCHIATO)
FLAT_WHITE = DrinkCommand(Drink.FLAT_WHITE)
CAPPUCCINO = DrinkCommand(Drink.CAPPUCCINO)
CORTADO = DrinkCommand(Drink.CORTADO)
ESPRESSO_MACCHIATO = DrinkCommand(Drink.ESPRESSO_MACCHIATO)
RISTRETTO_BIANCO = DrinkCommand(Drink.RISTRETTO_BIANCO)
ICED_AMERICANO = DrinkCommand(Drink.ICED_AMERICANO)
ICED_LATTE = DrinkCommand(Drink.ICED_LATTE)
HOT_WATER = DrinkCommand(Drink.HOT_WATER)
HOT_MILK = DrinkCommand(Drink.HOT_MILK)
TRAVEL_MUG = DrinkCommand(Drink.TRAVEL_MUG)
