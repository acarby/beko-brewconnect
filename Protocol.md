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

Four color-coded profiles plus a guest profile.

| Code | Type | Values |
|---|---|---|
| `last_profile` | Enum | `guest`, `orange`, `violet`, `blue`, `green` |
| `profile{color}` | Raw (128B) | Per-profile drink recipes — decoded, see below |
| `{color}_username` | Raw (128B) | Profile display name — not decoded |
| `favor` | Raw (128B) | Favorites list — not decoded |

## Per-drink recipe data (`profile{color}`)

Despite the schema declaring `maxlen: 128`, the actual value observed is a
fixed **51 bytes**, holding the Water/Milk/Strength/Temperature settings
shown in the app's "Beverage Setting" screen for all 17 drinks at once —
not just the currently-selected one.

**Decoded via**: editing one slider at a time in the Smart Life app
("Beverage Setting" → adjust Water Volume/Milk Volume/Coffee
Strength/Brewing Temperature → Save) while watching the Tuya IoT
Platform's **Device Logs** tab, then diffing the base64-decoded
`profile{color}` value before/after each change. No app decompilation
involved — see [ReverseEngineering.md](ReverseEngineering.md) for the
general methodology.

### Format

51 bytes = **17 consecutive 3-byte records**, one per drink:

```
record = [water_ml, strength_byte, milk_ml]

water_ml:      raw byte, 0-255, direct millilitre value
milk_ml:       raw byte, 0-255, direct millilitre value (0 = no milk drink)
strength_byte: strength_value + (16 if high_temperature else 0)
strength_value: 0=Powder, 1=Soft, 2=Standard, 3=Intense
```

Confirmed by: `water_ml + milk_ml` matches the app's displayed total
exactly for every drink tested (e.g. Latte Macchiato: `30 + 220 = 250ml`,
matching the app's "250ml" label), and every single-slider edit produced
exactly the expected single-byte diff at a consistent offset with no
other bytes changing (no checksum, no other structure).

### Record index per drink

Determined empirically by diffing each drink's `Selected Beverage` +
`profile{color}` publish pair in Device Logs:

| Drink | Record # | Byte offset |
|---|---|---|
| Americano | 1 | 3 |
| Lungo | 2 | 6 |
| CaffeLatte | 3 | 9 |
| Cappuccino | 4 | 12 |
| LatteMacchiato | 5 | 15 |
| Ristretto | 6 | 18 |
| Doppio | 7 | 21 |
| EspressoMacchiato | 8 | 24 |
| RistrettoBianco | 9 | 27 |
| FlatWhite | 10 | 30 |
| Cortado | 11 | 33 |
| Hotwater | 14 | 42 |
| Hotmilk | 15 | 45 |
| TravelMug | 16 | 48 |

**Not positionally distinguishable**: Espresso, IcedAmericano, and
IcedLatte all default to identical values (`30ml water, 0ml milk`), so
their assignment to the three remaining record slots (0, 12, 13) is a
best-effort guess in `coffee_sdk/recipes.py`'s `DRINK_RECORD_INDEX`. This
has no practical effect on the `needs_milk`/ml-display feature, since all
three correctly report "no milk" and the same volume regardless of which
exact slot each is assigned — it would only matter if you specifically
customized one of those three drinks' recipe differently from the others
and needed to tell them apart, which the current implementation can't do.

`TravelMug` is a partial exception: the app displays "280ml" for it, but
280 exceeds a single byte's range (max 255) — the stored value (140) is
almost certainly doubled for display purposes (a travel mug being a
double-sized serving), not stored as a literal 280.

### `Recipe` in the SDK

`coffee_sdk.recipes.decode_profile_blob()` parses a `profile{color}`
value into `dict[Drink, Recipe]`. `MachineStatus.recipes` (a property)
automatically picks the blob matching the device's current
`last_profile` DP. See [API.md](API.md) for usage.

## What's not exposed

- No drink-count / brew-history DP — "drinks made" in the Home Assistant
  integration is tracked entirely client-side (see
  [Architecture.md](Architecture.md)).
- No continuous water/bean fill-level percentage.
- No maintenance-due advance warning (only "empty now" / "full now").
- No way to *write* a custom recipe through this SDK yet (reading is
  fully implemented; writing would mean re-encoding and sending back a
  modified 51-byte blob, which hasn't been attempted).
