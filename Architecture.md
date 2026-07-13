# Architecture

```
                    ┌──────────────────────┐
                    │   Tuya Cloud (EU)     │
                    │  openapi.tuyaeu.com   │
                    └──────────┬───────────┘
                               │ HTTPS, HMAC-signed
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐   ┌─────────▼─────────┐   ┌────────▼────────┐
│  coffee_sdk     │   │  Official          │   │  This project's │
│  (this repo)    │   │  HomeDirect app    │   │  HA integration  │
│                  │   │  (untouched)       │   │  (vendors        │
│                  │   │                    │   │   coffee_sdk)    │
└─────────────────┘   └────────────────────┘   └──────────────────┘
```

Both the official app and this project talk to the *same* Tuya Cloud
backend, as independent, equally-valid clients — nothing here proxies
through or depends on the app.

## `coffee_sdk`

```
coffee_sdk/
  client.py       TuyaCloudClient — signed HTTP requests, retries, token mgmt
  auth.py         HMAC-SHA256 request signing, access/refresh token lifecycle
  models.py       Pydantic models: MachineStatus, Drink, WorkState, FaultFlag
  machine.py      CoffeeMachine — high-level status/brew/maintenance API
  drinks.py       Drink -> DP command recipe mapping
  exceptions.py   CoffeeSDKError hierarchy
```

- **Async-first** (`httpx.AsyncClient`) since every operation is a network
  round-trip to Tuya's cloud; there's no local/synchronous fast path to
  optimize for.
- **Typed throughout** — `MachineStatus` is a Pydantic model built from the
  raw Tuya DP array via `MachineStatus.from_dp_status()`, which tolerates
  unknown DP codes (ignored rather than raising) so a firmware update
  adding new DPs doesn't break parsing.
- **Retries + token refresh** live in `TuyaCloudClient._request()`: a
  request that fails with Tuya's "invalid/expired token" error codes
  (1010/1011) triggers a token refresh and one retry, transparently.
- **`http_client` injection**: `TuyaCloudClient` accepts an optional
  pre-built `httpx.AsyncClient`. This exists specifically for embedding
  in Home Assistant — constructing `httpx.AsyncClient()` does blocking
  SSL certificate loading, which HA's event loop explicitly flags as
  unsafe to do inline. The HA integration passes in HA's own shared
  client via `homeassistant.helpers.httpx_client.get_async_client(hass)`
  instead of letting the SDK create its own.

## Home Assistant integration

```
custom_components/beko_brewconnect/
  __init__.py       Entry setup/teardown, wires TuyaCloudClient to HA's httpx client
  config_flow.py    UI setup: Access ID/Secret/Device ID/region -> validates live
  const.py          Domain, config keys, poll interval
  coordinator.py    DataUpdateCoordinator: polls status(), tracks local drink history
  entity.py         Shared base entity (device_info)
  sensor.py         State, current drink, drinks-made counter, last-drink, etc.
  binary_sensor.py  Water/beans/grounds/door/fault flags
  button.py         One button per drink + maintenance action
  coffee_sdk/       Vendored copy of the top-level coffee_sdk package
```

### Why coffee_sdk is vendored, not a dependency

Home Assistant's `manifest.json` `requirements` field installs packages
from PyPI at integration-load time. `coffee_sdk` isn't published there, so
a plain `requirements: ["coffee_sdk"]` wouldn't resolve. Vendoring a copy
under `custom_components/beko_brewconnect/coffee_sdk/` (with imports
rewritten from absolute `coffee_sdk.x` to relative `.x`) is the standard
pattern for HA custom integrations with their own bespoke API client.
If `coffee_sdk` is ever published to PyPI, this vendoring step goes away.

### Why "drinks made" is tracked locally

The Tuya DP schema (see [Protocol.md](Protocol.md)) has no counter or
history DP at all — the device simply doesn't report this. The
coordinator maintains its own history (`DrinkHistoryEntry` list) any time
a drink button is pressed *through this integration*, persisted via HA's
`Store` helper so it survives restarts. This means:

- Drinks made via the official HomeDirect app **won't** be counted here —
  there's no way to observe them, since nothing in the DP schema reports
  brew events.
- The counter is a record of "brews requested through this integration,"
  not "total brews the machine has ever made."

### Why "progress" is a state, not a percentage

`work_state` is an enum (`standby`, `warm_up`, `brewing`, ...), not a
countdown or percentage. The `sensor.beko_brewconnect_work_state` entity
reflects this directly — useful for automations ("notify when brewing
finishes") but not a literal progress bar.

### Why no CLI

The original plan included a `coffee` CLI (Phase 5), but it was skipped:
the only real consumer of this SDK is Home Assistant, which calls it
directly as a library — a CLI would mainly help with manual testing or
scripting outside HA, neither of which was a priority. Straightforward to
add later (`coffee_sdk` already exposes everything a CLI would need) if
that changes.

## Extension points for future work

- **Custom drink recipes** (water/coffee/milk amounts): not found in the
  current DP schema. Worth investigating the opaque `profile{color}` Raw
  blobs (128 bytes, binary-encoded) — likely where per-user drink
  customization lives, if it's controllable via the API at all rather
  than being fully on-device state.
- **CLI**: `coffee_sdk.CoffeeMachine` already has every method a CLI would
  wrap; a `typer`-based `coffee` command is a small addition (the
  `pyproject.toml` already reserves the `[project.scripts]` entry point
  and a `cli` extras group for this).
- **HACS distribution**: the repo structure already matches what HACS
  expects for a custom integration; would need a `hacs.json` and a
  tagged release.
