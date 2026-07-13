"""Typed models for the Beko BrewConnect (HomeDirect) Tuya DP schema.

The DP (data point) schema below was extracted from the Tuya IoT Platform's
"Standard Status Set" for product "Full-Auto Espresso Machine"
(device id bfda99b991844fcd78xgyt, product category "kfj").
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Drink(StrEnum):
    """Values accepted by the `drink_set` DP."""

    ESPRESSO = "Espresso"
    AMERICANO = "Americano"
    LUNGO = "Lungo"
    CAFFE_LATTE = "CaffeLatte"
    LATTE_MACCHIATO = "LatteMacchiato"
    RISTRETTO = "Ristretto"
    DOPPIO = "Doppio"
    ESPRESSO_MACCHIATO = "EspressoMacchiato"
    RISTRETTO_BIANCO = "RistrettoBianco"
    FLAT_WHITE = "FlatWhite"
    CORTADO = "Cortado"
    ICED_AMERICANO = "IcedAmericano"
    ICED_LATTE = "IcedLatte"
    HOT_WATER = "Hotwater"
    HOT_MILK = "Hotmilk"
    TRAVEL_MUG = "TravelMug"
    CAPPUCCINO = "Cappuccino"


class WorkState(StrEnum):
    """Values reported by the `work_state` DP."""

    STANDBY = "standby"
    POWER_SAVE = "power_save"
    WARM_UP = "warm_up"
    BREWING = "brewing"
    AUTO_CLEAN = "auto_clean"
    EMPTY_DEVICE = "empty_device"
    DESCALING = "descaling"
    RESET = "reset"


class Mode(StrEnum):
    """Values accepted by the `mode_selection` DP."""

    DEFAULT = "Default"
    ECO = "ECO"


class AutoShutOffTimer(StrEnum):
    """Values accepted by the `aso_timer` DP."""

    MIN_10 = "10Minutes"
    MIN_20 = "20Minutes"
    MIN_30 = "30Minutes"
    HOUR_1 = "1hour"
    HOUR_2 = "2hours"
    HOUR_3 = "3hours"
    HOUR_6 = "6hours"
    HOUR_12 = "12hours"
    HOUR_24 = "24hours"


class Profile(StrEnum):
    """Values accepted by the `last_profile` DP."""

    GUEST = "guest"
    ORANGE = "orange"
    VIOLET = "violet"
    BLUE = "blue"
    GREEN = "green"


class FaultFlag(StrEnum):
    """Individual bit labels within the `fault` bitmap DP."""

    HEATING_FAULT = "heating_fault"
    NTC_FAULT = "ntc_fault"
    BLOCKING = "blocking"
    FRONT_DOOR_OPEN = "Frontdoor_open"
    BU_MISPLACED = "BU_misplaced"
    WATER_EMPTY = "Water_empty"
    TRASHCAN_MISPLACED = "Trashcan_misplaced"
    BEAN_CONTAINER_EMPTY = "BeanContainer_empty"
    RESIDUAL_FULL = "Residual_full"
    MILKCUP_MISSING = "Milkcup_missing"
    WATERTANK_MISPLACED = "WaterTank_Misplaced"


def _parse_fault_bitmap(value: int | list[str]) -> frozenset[FaultFlag]:
    """Parse the `fault` DP value.

    The Tuya Cloud REST API reports bitmap DPs as an integer bitmask (bit
    order matches the schema's `label` array), while the IoT Platform's web
    debug console displays the same DP as a list of active label strings.
    Both forms are accepted here for robustness.
    """
    if isinstance(value, int):
        flags = list(FaultFlag)
        return frozenset(flags[i] for i in range(len(flags)) if value & (1 << i))
    return frozenset(FaultFlag(label) for label in value if label in FaultFlag._value2member_map_)


# The raw DP code -> Python attribute name mapping used when parsing
# a Tuya `/v1.0/devices/{id}/status` response into a MachineStatus.
_DP_CODE_MAP: dict[str, str] = {
    "switch": "power_on",
    "start": "start",
    "work_state": "work_state",
    "fault": "faults",
    "drink_set": "drink_set",
    "double": "double_shot",
    "pre_brew": "pre_brew",
    "espressoshot": "espresso_shot_active",
    "milkfrothing": "milk_frothing_active",
    "hotwaterdispensing": "hot_water_dispensing_active",
    "auto_clean": "auto_clean_active",
    "rinsing_clean": "rinsing_clean_active",
    "milk_cupclean": "milk_cup_clean_active",
    "descaling": "descaling_active",
    "factory_reset": "factory_reset_active",
    "empty_device": "empty_device_active",
    "mode_selection": "mode",
    "water_hardness": "water_hardness",
    "aso_timer": "auto_shutoff_timer",
    "last_profile": "last_profile",
}


class MachineStatus(BaseModel):
    """A parsed snapshot of the coffee machine's DP status."""

    power_on: bool = False
    start: bool = False
    work_state: WorkState = WorkState.STANDBY
    faults: frozenset[FaultFlag] = Field(default_factory=frozenset)
    drink_set: Drink | None = None
    double_shot: bool = False
    pre_brew: bool = False
    espresso_shot_active: bool = False
    milk_frothing_active: bool = False
    hot_water_dispensing_active: bool = False
    auto_clean_active: bool = False
    rinsing_clean_active: bool = False
    milk_cup_clean_active: bool = False
    descaling_active: bool = False
    factory_reset_active: bool = False
    empty_device_active: bool = False
    mode: Mode = Mode.DEFAULT
    water_hardness: int = 3
    auto_shutoff_timer: AutoShutOffTimer | None = None
    last_profile: Profile | None = None

    @property
    def water_empty(self) -> bool:
        return FaultFlag.WATER_EMPTY in self.faults

    @property
    def bean_container_empty(self) -> bool:
        return FaultFlag.BEAN_CONTAINER_EMPTY in self.faults

    @property
    def grounds_full(self) -> bool:
        return FaultFlag.RESIDUAL_FULL in self.faults

    @property
    def needs_attention(self) -> bool:
        """True if any fault flag is set (door open, empty container, etc.)."""
        return len(self.faults) > 0

    @classmethod
    def from_dp_status(cls, status: list[dict]) -> MachineStatus:
        """Build a MachineStatus from a raw Tuya `status` array.

        Each element of `status` looks like {"code": "switch", "value": true}.
        Unknown DP codes are ignored rather than raising, so newly-discovered
        DPs on firmware updates don't break parsing.
        """
        kwargs: dict = {}
        raw_by_code = {item["code"]: item["value"] for item in status}

        for code, value in raw_by_code.items():
            attr = _DP_CODE_MAP.get(code)
            if attr is None:
                continue
            if code == "fault":
                kwargs[attr] = _parse_fault_bitmap(value)
            elif code == "drink_set":
                kwargs[attr] = Drink(value) if value in Drink._value2member_map_ else None
            elif code == "work_state":
                kwargs[attr] = (
                    WorkState(value) if value in WorkState._value2member_map_ else WorkState.STANDBY
                )
            elif code == "mode_selection":
                kwargs[attr] = Mode(value) if value in Mode._value2member_map_ else Mode.DEFAULT
            elif code == "aso_timer":
                kwargs[attr] = (
                    AutoShutOffTimer(value)
                    if value in AutoShutOffTimer._value2member_map_
                    else None
                )
            elif code == "last_profile":
                kwargs[attr] = Profile(value) if value in Profile._value2member_map_ else None
            else:
                kwargs[attr] = value

        return cls(**kwargs)


class DeviceInfo(BaseModel):
    """Static device metadata from `/v1.0/devices/{id}`."""

    id: str
    name: str
    product_id: str
    product_name: str
    online: bool
    category: str
    ip: str | None = None
