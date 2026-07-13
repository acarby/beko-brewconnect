# beko-brewconnect

A Python SDK and Home Assistant integration for the Beko/Arçelik **CEG7348X**
full-automatic espresso machine, controlled independently of the official
**HomeDirect** mobile app.

The machine turned out to be a white-labeled **Tuya Smart Life** device.
Rather than reverse engineering and defeating the app's certificate-pinned
MQTT channel, this project talks to the machine through the official
**Tuya Cloud API**, using credentials from a Tuya IoT Platform project linked
to your existing HomeDirect/Smart Life account. No app decompilation,
firmware dumping, or pinning bypass required.

See [ReverseEngineering.md](ReverseEngineering.md) for how the device was
identified and how this conclusion was reached, [Protocol.md](Protocol.md)
for the full data-point (DP) schema, [Architecture.md](Architecture.md) for
how the pieces fit together, [API.md](API.md) for the Python SDK reference,
and [HomeAssistant.md](HomeAssistant.md) for setting up the integration.

## What's here

```
coffee_sdk/                          Typed async Python SDK
custom_components/beko_brewconnect/  Home Assistant custom integration
tests/                                Unit tests for the SDK
```

## Quick start (SDK)

```bash
pip install -e .
```

```python
import asyncio
from coffee_sdk import login

async def main():
    async with login(client_id="...", client_secret="...", region="eu") as client:
        machine = client.machine("your-device-id")
        status = await machine.status()
        print(status.work_state, status.water_empty)
        await machine.make_espresso()

asyncio.run(main())
```

`client_id`/`client_secret` come from a Tuya IoT Platform project you create
and link to your Tuya app account — see
[ReverseEngineering.md](ReverseEngineering.md#getting-your-own-credentials)
for the exact steps, since there's no public shared API key for this.

## Quick start (Home Assistant)

Copy `custom_components/beko_brewconnect` into your HA `config/custom_components/`
directory, restart HA, then add the integration via
**Settings → Devices & Services → Add Integration → Beko BrewConnect**.
Full details in [HomeAssistant.md](HomeAssistant.md).

## Status

- [x] Device identified and confirmed on the local network
- [x] Protocol reverse engineered (Tuya Cloud, DP schema documented)
- [x] Python SDK — status, brewing, maintenance actions, typed models
- [x] Home Assistant integration — sensors, binary sensors, buttons
- [ ] CLI (skipped for now — see [Architecture.md](Architecture.md#why-no-cli))
- [ ] Custom drink recipes (water/coffee/milk ratios) — not exposed by the
      DP schema found so far; potential future investigation

## Disclaimer

This project is the result of independent reverse engineering of network
traffic and a vendor cloud platform you already have legitimate access to
(your own device, your own Tuya account). It is not affiliated with, and
is not endorsed by, Beko, Arçelik, Tuya, or HomeWhiz. Use at your own risk;
sending malformed commands to the device is unlikely to be dangerous
(control is mediated entirely by Tuya's cloud, which validates DP values
against the schema) but is entirely unsupported by the manufacturer.
