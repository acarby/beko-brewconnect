"""Per-drink recipe data, decoded from the `profile{color}` Raw DPs.

Not part of the documented Tuya schema -- reverse engineered by editing
each drink's "Beverage Setting" (water/milk/strength/temperature) in the
Smart Life app and diffing the resulting DP report via the Tuya IoT
Platform's Device Logs. See Protocol.md for the full writeup.

Format: each `profile{color}` DP is a 51-byte blob = 17 consecutive 3-byte
records, one per `Drink`, each record being
`[water_ml, strength_byte, milk_ml]` where
`strength_byte = strength_value + (16 if high_temperature else 0)`.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import StrEnum

from coffee_sdk.models import Drink

RECORD_SIZE = 3
NUM_RECORDS = 17


class Strength(StrEnum):
    POWDER = "Powder"
    SOFT = "Soft"
    STANDARD = "Standard"
    INTENSE = "Intense"


_STRENGTH_BY_VALUE: dict[int, Strength] = {
    0: Strength.POWDER,
    1: Strength.SOFT,
    2: Strength.STANDARD,
    3: Strength.INTENSE,
}

# Record index within the profile blob for each drink, determined
# empirically (see Protocol.md). Espresso, Iced Americano, and Iced Latte
# share identical default values (30ml water, 0ml milk) and could not be
# positionally distinguished from defaults alone -- their assignment below
# is a best-effort guess, though functionally interchangeable since all
# three currently report no milk regardless.
DRINK_RECORD_INDEX: dict[Drink, int] = {
    Drink.ESPRESSO: 0,
    Drink.AMERICANO: 1,
    Drink.LUNGO: 2,
    Drink.CAFFE_LATTE: 3,
    Drink.CAPPUCCINO: 4,
    Drink.LATTE_MACCHIATO: 5,
    Drink.RISTRETTO: 6,
    Drink.DOPPIO: 7,
    Drink.ESPRESSO_MACCHIATO: 8,
    Drink.RISTRETTO_BIANCO: 9,
    Drink.FLAT_WHITE: 10,
    Drink.CORTADO: 11,
    Drink.ICED_AMERICANO: 12,
    Drink.ICED_LATTE: 13,
    Drink.HOT_WATER: 14,
    Drink.HOT_MILK: 15,
    Drink.TRAVEL_MUG: 16,
}


@dataclass(frozen=True)
class Recipe:
    """A single drink's saved water/milk/strength/temperature settings."""

    drink: Drink
    water_ml: int
    milk_ml: int
    strength: Strength
    high_temperature: bool

    @property
    def needs_milk(self) -> bool:
        return self.milk_ml > 0

    @property
    def total_ml(self) -> int:
        return self.water_ml + self.milk_ml


def decode_profile_blob(raw: str | bytes) -> dict[Drink, Recipe]:
    """Decode a `profile{color}` DP value into per-drink Recipe objects.

    Args:
        raw: The DP's raw value from the Tuya status API -- base64-encoded
            (str) or already-decoded bytes.
    """
    data = base64.b64decode(raw) if isinstance(raw, str) else raw
    recipes: dict[Drink, Recipe] = {}
    for drink, idx in DRINK_RECORD_INDEX.items():
        offset = idx * RECORD_SIZE
        if offset + RECORD_SIZE > len(data):
            continue
        water, strength_byte, milk = data[offset], data[offset + 1], data[offset + 2]
        recipes[drink] = Recipe(
            drink=drink,
            water_ml=water,
            milk_ml=milk,
            strength=_STRENGTH_BY_VALUE.get(strength_byte % 16, Strength.STANDARD),
            high_temperature=strength_byte >= 16,
        )
    return recipes
