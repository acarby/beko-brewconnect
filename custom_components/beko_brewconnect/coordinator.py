"""DataUpdateCoordinator for polling the coffee machine and tracking local history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .coffee_sdk.client import TuyaCloudClient
from .coffee_sdk.exceptions import CoffeeSDKError
from .coffee_sdk.models import Drink, MachineStatus
from .const import DOMAIN, STORAGE_KEY_TEMPLATE, STORAGE_VERSION, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

MAX_HISTORY_ENTRIES = 200


@dataclass
class DrinkHistoryEntry:
    drink: str
    made_at: str  # ISO 8601, always UTC and timezone-aware

    @classmethod
    def now(cls, drink: Drink) -> DrinkHistoryEntry:
        return cls(drink=drink.value, made_at=datetime.now(UTC).isoformat())


@dataclass
class BrewConnectData:
    status: MachineStatus
    history: list[DrinkHistoryEntry] = field(default_factory=list)

    @property
    def drinks_made_total(self) -> int:
        return len(self.history)

    @property
    def last_drink(self) -> str | None:
        return self.history[-1].drink if self.history else None

    @property
    def last_drink_at(self) -> datetime | None:
        if not self.history:
            return None
        parsed = datetime.fromisoformat(self.history[-1].made_at)
        # Defensive: older persisted history entries (pre-UTC fix) may be
        # naive. Assume UTC rather than raising, since HA's timestamp
        # device class requires timezone-aware datetimes.
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class BrewConnectCoordinator(DataUpdateCoordinator[BrewConnectData]):
    """Polls machine status and tracks a locally-persisted drink history.

    The device's DP schema has no drink-count or history DP, so "drinks
    made" is derived entirely from calls this integration itself makes,
    persisted via HA's Store helper so it survives restarts.
    """

    def __init__(self, hass: HomeAssistant, client: TuyaCloudClient, device_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.device_id = device_id
        self.machine = client.machine(device_id)
        self._store: Store[list[dict]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(device_id=device_id)
        )
        self._history: list[DrinkHistoryEntry] = []

    async def async_load_history(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self._history = [DrinkHistoryEntry(**item) for item in stored]

    async def async_record_drink(self, drink: Drink) -> None:
        """Record that a drink was just requested. Call this from the button entities."""
        self._history.append(DrinkHistoryEntry.now(drink))
        self._history = self._history[-MAX_HISTORY_ENTRIES:]
        await self._store.async_save([vars(e) for e in self._history])
        await self.async_request_refresh()

    async def _async_update_data(self) -> BrewConnectData:
        try:
            status = await self.machine.status()
        except CoffeeSDKError as err:
            raise UpdateFailed(f"Error communicating with coffee machine: {err}") from err
        return BrewConnectData(status=status, history=self._history)
