# Home Assistant Integration

## Prerequisites

- A working Tuya IoT Platform project (Access ID + Access Secret) with
  your coffee machine linked, per
  [ReverseEngineering.md](ReverseEngineering.md#getting-your-own-credentials).
  You'll need the machine's **Device ID** from that project's device list.
- Home Assistant with filesystem access to its `config/` directory (this
  is a manual custom component install, not yet published to HACS).

## Installing

Copy the integration folder into your HA config:

```
<ha config dir>/custom_components/beko_brewconnect/
```

If you run HA in Docker (as this project's author does — a
`homeassistant:stable` container with `/config` bind-mounted from the
host), copy it in via `docker cp` rather than trying to write into the
container's filesystem directly if the host-side volume isn't writable by
your user:

```bash
rsync -az custom_components/beko_brewconnect/ your-host:/tmp/beko_deploy/
ssh your-host "
  docker exec homeassistant rm -rf /config/custom_components/beko_brewconnect
  docker cp /tmp/beko_deploy homeassistant:/config/custom_components/beko_brewconnect
  docker exec homeassistant chown -R root:root /config/custom_components/beko_brewconnect
  rm -rf /tmp/beko_deploy
  docker restart homeassistant
"
```

Then restart Home Assistant.

## Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for **"Beko BrewConnect"**
3. Enter:
   - **Access ID** — your Tuya project's Access ID
   - **Access Secret** — your Tuya project's Access Secret
   - **Device ID** — the machine's Tuya device ID
   - **Region** — `eu` (Central Europe data center; correct for
     Beko/Arçelik HomeDirect devices)
4. On success, a device named after the machine appears with all its
   entities.

The config flow validates credentials live (fetches device info) before
letting you finish setup — a bad Access ID/Secret or wrong Device ID
surfaces as an inline error rather than a silently-broken integration.

## Entities

### Sensors

| Entity | Description |
|---|---|
| `sensor.*_state` | Current `work_state`, human-readable (Standby, Warming up, Brewing, Cleaning, Descaling, ...) |
| `sensor.*_current_drink` | The `drink_set` value currently selected on the device |
| `sensor.*_drinks_made` | Count of drinks brewed **through this integration** (see note below) |
| `sensor.*_last_drink` | Name of the last drink brewed through this integration |
| `sensor.*_last_drink_at` | Timestamp of the above |
| `sensor.*_water_hardness` | Configured water hardness (1–5) |
| `sensor.*_mode` | `Default` or `ECO` |

> **"Drinks made" only counts brews triggered via this integration's
> buttons**, not ones made directly on the machine or through the official
> HomeDirect app — the device doesn't report a brew-event history over
> the API at all (see [Protocol.md](Protocol.md)), so there's no way to
> observe those.

### Binary sensors

| Entity | On means |
|---|---|
| `binary_sensor.*_water_tank_empty` | Water tank needs refilling |
| `binary_sensor.*_bean_container_empty` | Bean hopper needs refilling |
| `binary_sensor.*_grounds_container_full` | Grounds/residual container needs emptying |
| `binary_sensor.*_front_door_open` | Front door open |
| `binary_sensor.*_needs_attention` | Any fault flag set (aggregate) |

All boolean — there are no fill-level percentages available.

### Buttons

Espresso, Double espresso, Americano, Latte, Flat white, Cappuccino,
Stop, and (under the entity's "Configuration" category) Rinse, Clean,
Clean milk cup, Descale.

Each drink button exposes its **recipe as entity attributes**, read live
from the machine's own saved settings for the currently active user
profile (see [Protocol.md](Protocol.md#per-drink-recipe-data) for how
this is decoded):

```yaml
water_ml: 60
milk_ml: 190
total_ml: 250
needs_milk: true
strength: Standard
high_temperature: false
```

Since these reflect the **actual saved recipe on the device** (whatever
you've customized in the official app), they'll change if you edit a
drink's Water/Milk Volume sliders there — no need to update anything in
Home Assistant.

## Confirming before brewing a milk drink

Home Assistant button entities don't have a server-side confirmation
step, but the Lovelace dashboard does — add `confirmation` to the
button's `tap_action` for any drink where you want a "are you sure the
milk container is filled?" prompt before it actually fires:

```yaml
type: button
entity: button.beko_brewconnect_latte
name: Latte
tap_action:
  action: perform-action
  perform_action: button.press
  target:
    entity_id: button.beko_brewconnect_latte
  confirmation:
    text: >
      This drink uses milk ({{ state_attr('button.beko_brewconnect_latte', 'milk_ml') }}ml).
      Make sure the milk container is filled and connected.
```

Since `needs_milk` is a live attribute, you can build this dynamically
for every milk drink with a template, or generate one card per drink and
only add the `confirmation` block to the ones where
`needs_milk: true` — a `{% if %}` template card or a small script that
regenerates your dashboard config from the entity attributes both work,
depending on how much you want to automate it versus set up once.

## Example automation

```yaml
automation:
  - alias: "Notify when coffee is ready"
    trigger:
      - platform: state
        entity_id: sensor.beko_brewconnect_state
        from: "Brewing"
        to: "Standby"
    action:
      - service: notify.mobile_app_your_phone
        data:
          message: "Coffee's ready ☕"
```

## Troubleshooting

- **Setup fails with "Authentication failed"**: double-check the Access
  ID/Secret weren't swapped, and that the project's data center is
  actually Central Europe.
- **Setup fails with "Device not found"**: the Device ID is wrong, or the
  device isn't linked to this Tuya project yet (check the IoT Platform's
  Devices tab — status should show "Controllable" permission, not just
  "Read").
- **Entities show unavailable after working fine for a while**: the
  device went offline (Wi-Fi drop, power cut) — the coordinator will
  recover automatically once it reconnects; no action needed.
- **Blocking-call warnings in the HA log mentioning `beko_brewconnect`**:
  should not occur as of this integration passing `http_client` through
  to `TuyaCloudClient` — if you see this, check you're on a version that
  includes that fix (see [Architecture.md](Architecture.md)).
