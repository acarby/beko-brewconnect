# Protocol

The device is controlled entirely through the **Tuya Cloud API**
(`https://openapi.tuyaeu.com` for the Central Europe data center). There is
no local/LAN API — see [ReverseEngineering.md](ReverseEngineering.md) for
why.

## Identity

| Field | Value |
|---|---|
| Device ID / Tuya Virtual ID | `bfda99b991844fcd78xgyt` |
| Product category | `kfj` |
| Product name | Full-Auto Espresso Machine |
| MAC | `00:33:7a:06:df:ef` |
| Data center | Central Europe (`tuyaeu.com`) |

Your own device will have a different Device ID — get it from the Tuya IoT
Platform's linked-devices list, or from HomeDirect's device-info screen
(labelled "Virtual ID" there).

## Authentication

Standard Tuya Cloud API v1.0 signing (HMAC-SHA256). See
[developer.tuya.com/en/docs/iot/new-singnature](https://developer.tuya.com/en/docs/iot/new-singnature)
for the full spec; summarized in `coffee_sdk/auth.py`.

```
GET /v1.0/token?grant_type=1
headers: client_id, sign, t, sign_method=HMAC-SHA256
```

returns an `access_token` (used as a header on every subsequent call,
folded into the signature) and a `refresh_token`. Tokens expire in ~2
hours; refresh via `GET /v1.0/token/{refresh_token}` with the same signing
scheme.

## Reading status

```
GET /v1.0/devices/{device_id}/status
```

Returns an array of `{"code": ..., "value": ...}` — one entry per DP
(data point). See the schema below for what each code means.

## Sending commands

```
POST /v1.0/devices/{device_id}/commands
body: {"commands": [{"code": "...", "value": ...}, ...]}
```

Multiple DPs can be set in one call — e.g. brewing sends `drink_set`,
`double`, and `start` together.

## DP (Data Point) Schema

Pulled from the Tuya IoT Platform's device debugger (**Device Debugging →
DP Instruction**), which is the authoritative, complete list — the
"Standard Instruction Set" view shows only a reduced, cross-brand-mapped
subset and should be ignored in favor of this.

### Power & brewing

| Code | Type | Values | Notes |
|---|---|---|---|
| `switch` | Boolean | | Power on/off |
| `start` | Boolean | | Start the currently-armed operation (drink/clean/descale) |
| `drink_set` | Enum | `Espresso`, `Americano`, `Lungo`, `CaffeLatte`, `LatteMacchiato`, `Ristretto`, `Doppio`, `EspressoMacchiato`, `RistrettoBianco`, `FlatWhite`, `Cortado`, `IcedAmericano`, `IcedLatte`, `Hotwater`, `Hotmilk`, `TravelMug`, `Cappuccino` | Select the recipe before `start` |
| `double` | Boolean | | Double-shot modifier |
| `pre_brew` | Boolean | | Pre-brew / bloom |
| `espressoshot` | Boolean | | Manual espresso-shot trigger |
| `milkfrothing` | Boolean | | Manual milk-froth trigger |
| `hotwaterdispensing` | Boolean | | Manual hot-water trigger |

### Maintenance

| Code | Type |
|---|---|
| `auto_clean` | Boolean |
| `rinsing_clean` | Boolean |
| `milk_cupclean` | Boolean |
| `descaling` | Boolean |
| `factory_reset` | Boolean |
| `empty_device` | Boolean |

### Status / diagnostics

| Code | Type | Values |
|---|---|---|
| `work_state` | Enum | `standby`, `power_save`, `warm_up`, `brewing`, `auto_clean`, `empty_device`, `descaling`, `reset` |
| `fault` | Bitmap | `heating_fault`, `ntc_fault`, `blocking`, `Frontdoor_open`, `BU_misplaced`, `Water_empty`, `Trashcan_misplaced`, `BeanContainer_empty`, `Residual_full`, `Milkcup_missing`, `WaterTank_Misplaced` |

**Important**: `fault` is reported by the REST API as an **integer
bitmask** (bit position = index into the label list above), not as a list
of active label strings — despite the IoT Platform's own web debug console
*displaying* it as a list. `coffee_sdk.models._parse_fault_bitmap` handles
both forms.

**No percentage-based level sensors exist.** Water/beans/grounds are only
exposed as boolean empty/full flags within `fault`. There is also no
"time to clean" / "descale due soon" advance-warning DP — only the
booleans above, which only flip once a limit is actually hit.

### Settings

| Code | Type | Values |
|---|---|---|
| `mode_selection` | Enum | `Default`, `ECO` |
| `water_hardness` | Integer | 1–5 |
| `aso_timer` | Enum | `10Minutes`, `20Minutes`, `30Minutes`, `1hour`, `2hours`, `3hours`, `6hours`, `12hours`, `24hours` (auto shut-off) |

### User profiles

Four color-coded profiles plus a guest profile. Profile data
(`profileorange`/`profileviolet`/`profileblue`/`profilegreen`) is opaque
binary (`Raw`, 128 bytes max) — not reverse engineered further, since it
wasn't needed for basic control.

| Code | Type | Values |
|---|---|---|
| `last_profile` | Enum | `guest`, `orange`, `violet`, `blue`, `green` |
| `profile{color}` | Raw (128B) | Opaque per-profile drink preferences |
| `{color}_username` | Raw (128B) | Profile display name |
| `favor` | Raw (128B) | Favorites list, opaque |

## What's not exposed

- No drink-count / brew-history DP — "drinks made" in the Home Assistant
  integration is tracked entirely client-side (see
  [Architecture.md](Architecture.md)).
- No continuous water/bean fill-level percentage.
- No maintenance-due advance warning (only "empty now" / "full now").
- Custom recipe control (exact water/coffee/milk quantities) was not found
  in this schema — the closest is the fixed `drink_set` enum. Possibly
  configurable via the opaque `profile{color}` Raw blobs, unexplored.
