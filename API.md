# API Reference — `coffee_sdk`

## Installation

```bash
pip install -e .
# or, with dev/test tooling:
pip install -e ".[dev]"
```

Requires Python 3.12+.

## Entry point

```python
from coffee_sdk import login

async with login(client_id, client_secret, region="eu") as client:
    ...
```

`login()` returns a `TuyaCloudClient`, meant to be used as an async
context manager (or manually `await client.aclose()`'d).

- `client_id` / `client_secret` — your Tuya IoT Platform project's Access
  ID / Access Secret (see [ReverseEngineering.md](ReverseEngineering.md)
  for how to get these).
- `region` — Tuya data center: `"eu"` (default; Central Europe — what
  Beko/Arçelik HomeDirect devices use), `"us"`, `"cn"`, or `"in"`.

## `TuyaCloudClient`

```python
class TuyaCloudClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        region: str = "eu",
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None: ...

    def machine(self, device_id: str) -> CoffeeMachine: ...
    async def get(self, path_and_query: str) -> dict: ...
    async def post(self, path_and_query: str, json_body: dict) -> dict: ...
    async def aclose(self) -> None: ...
```

`get`/`post` are the raw signed-request primitives, exposed in case you
need to call a Tuya Cloud endpoint `CoffeeMachine` doesn't wrap. Handles
signing, access-token fetch/refresh, and retries automatically.

Pass `http_client` if embedding in an application that already manages
its own `httpx.AsyncClient` (e.g. Home Assistant) — see
[Architecture.md](Architecture.md#httpx-client-injection) for why this
matters.

## `CoffeeMachine`

Get one via `client.machine(device_id)`.

### Status

```python
status: MachineStatus = await machine.status()
info: DeviceInfo = await machine.info()
```

### Power / brew control

```python
await machine.power_on()
await machine.power_off()
await machine.start()   # start whatever's armed (drink/clean/descale)
await machine.stop()    # cancel current operation
```

### Drinks

```python
await machine.make_espresso()
await machine.make_double()
await machine.make_americano()
await machine.make_latte()
await machine.make_latte_macchiato()
await machine.make_flat_white()
await machine.make_cappuccino()

# Or send any DrinkCommand directly, e.g. for a drink without a dedicated
# make_*() method:
from coffee_sdk.drinks import DrinkCommand
from coffee_sdk.models import Drink
await machine.brew(DrinkCommand(Drink.RISTRETTO))
```

### Maintenance

```python
await machine.clean()
await machine.rinse()
await machine.clean_milk_cup()
await machine.descale()
await machine.empty_device()
```

### Sensors

```python
await machine.water_level_ok()   # bool: True if NOT reported empty
await machine.bean_level_ok()    # bool: True if NOT reported empty
await machine.grounds_full()     # bool
```

These are boolean, not percentages — the device's DP schema doesn't
expose a continuous fill level. See [Protocol.md](Protocol.md).

## Models (`coffee_sdk.models`)

### `MachineStatus`

Pydantic model parsed from a raw Tuya DP status array via
`MachineStatus.from_dp_status(raw_status_list)`.

Key fields: `power_on`, `work_state`, `faults` (a `frozenset[FaultFlag]`),
`drink_set`, `double_shot`, `mode`, `water_hardness`,
`auto_shutoff_timer`, `last_profile`.

Convenience properties: `.water_empty`, `.bean_container_empty`,
`.grounds_full`, `.needs_attention` (true if any fault flag is set).

### Enums

`Drink`, `WorkState`, `Mode`, `AutoShutOffTimer`, `Profile`, `FaultFlag`
— all `StrEnum`s mirroring the Tuya DP schema's enum/bitmap value sets
exactly (see [Protocol.md](Protocol.md) for the authoritative list).

### `DeviceInfo`

Static metadata from `machine.info()`: `id`, `name`, `product_id`,
`product_name`, `online`, `category`, `ip`.

## Exceptions (`coffee_sdk.exceptions`)

```
CoffeeSDKError                 base class
├── AuthenticationError        login/auth failed
│   └── TokenExpiredError      refresh also failed
├── APIError(code, msg)        Tuya API returned success=false
├── DeviceOfflineError         command sent to an offline device
└── InvalidDrinkError          (reserved; not currently raised)
```

## Logging

Standard library `logging`, logger names `coffee_sdk.auth` and
`coffee_sdk.client`/`coffee_sdk.machine`. Configure normally:

```python
import logging
logging.basicConfig(level=logging.INFO)
```
