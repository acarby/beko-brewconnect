# Reverse Engineering Log

This documents how the Beko CEG7348X's control protocol was identified,
from a cold start on the local network through to a working, documented
API — without decompiling the app or defeating certificate pinning.

## Phase 1 — Local network discovery

Goal: find the machine's IP/MAC on the LAN and see what it exposes locally.

1. `nmap -sn 10.20.0.0/24` — ping sweep to populate ARP.
2. `arp -a` + nmap's bundled OUI database (`nmap-mac-prefixes`) to resolve
   MAC vendors for every host. Four candidates stood out as non-standard
   consumer-electronics vendors: **Tuya Smart Inc.**, Ohsung, Hui Zhou
   Gaoshengda, Guangzhou Shirui — all common Chinese IoT/appliance Wi-Fi
   module suppliers.
3. Full TCP port scans (`nmap -Pn -p-`) on all four candidates: **every
   port came back filtered** — no local web server, no local API, nothing
   listening. This turned out to be a real finding, not a scan failure:
   the device is cloud-only by design.
4. UDP capture (`tcpdump`) for Tuya's usual LAN-discovery broadcast beacon:
   none seen. Confirms local/LAN control is disabled on this firmware.
5. **Wrong turn**: correlating power-cycles with ARP/ping drops to identify
   which candidate was the coffee machine was unreliable — multiple
   candidates dropped/recovered together (unrelated Wi-Fi churn on the same
   AP), and the "off" state of the machine turned out to be **standby**,
   which keeps its Wi-Fi module alive. A genuine wall-unplug was needed.
6. **What actually worked**: the HomeDirect app's own device-info screen
   displayed the MAC address directly (`00:33:7a:06:df:ef`), which matched
   `10.20.0.182` exactly. This is the most reliable identification method
   when available — check the app before relying on inference from traffic
   patterns.
7. A UniFi controller's "Client" list had fingerprinted this same MAC as
   **"CatGenie"** (a cat litter box) — a wrong guess by UniFi's heuristic
   fingerprinting DB, based on the Tuya OUI pattern being shared across
   unrelated Tuya-based products. Don't trust vendor fingerprinting labels
   as ground truth; they're a heuristic, not a lookup.

**Conclusion**: `10.20.0.182`, MAC `00:33:7a:06:df:ef`, Tuya Smart Inc.
OUI, zero open ports, no LAN discovery beacon — a pure cloud-tethered
device.

## Phase 2 — Traffic analysis

Goal: see what the app actually talks to.

- **mitmproxy** (`mitmweb`) configured as an HTTP(S) proxy on the phone,
  with its CA cert trusted via `http://mitm.it` + iOS's
  Settings → General → About → Certificate Trust Settings.
- The app is called **HomeDirect**, published by **HomeWhiz** for
  Arçelik/Beko — a third-party white-label IoT platform, not exclusively
  Beko's own.
- REST traffic to `a1.tuyaeu.com/api.json` confirmed the app is a
  re-skinned **Tuya Smart Life** client:
  - `bundleId=com.arcelik.tud4`
  - `sdkVersion=6.8.0` (Tuya's app SDK)
  - `clientId=7wn9pegqfvtqmaxypqdu` (Tuya OEM client ID for this app)
  - Every request is HMAC-signed (`sign=`) with an AES-encrypted
    `postData` payload — Tuya's standard request envelope. The business
    action name itself (`a=smartlife.m.user.email.password.login`,
    `a=tuya.m.device.get`, etc.) is sent in the clear even though the
    payload isn't, which let us catalog the full set of API actions the
    app calls without needing to decrypt anything.
  - `images.tuyaeu.com` serving generic Tuya Smart Life UI assets
    (FAQ/energy/message icons) confirmed the UI itself is Tuya's, not
    custom-built by Arçelik.
  - `arceliktud4.applink.smart321.com` — `smart321.com` is a
    Tuya-operated deep-linking domain, used for the app's own device-share
    links.
- **Real-time control channel**: no app-level "send command" REST action
  was ever observed — `smartlife.m.api.batch.invoke` likely bundles the
  actual control call inside its encrypted payload. To find the real
  channel, we needed to see *all* of the phone's traffic, not just HTTP:
  - iOS only honors the configured HTTP proxy for URLSession-based
    traffic. A raw TCP socket (which MQTT uses) **silently bypasses it**,
    so mitmproxy in plain HTTP-proxy mode never saw it.
  - Switched to **mitmproxy's WireGuard mode** (`mitmdump --mode wireguard`),
    which captures all traffic regardless of protocol via a VPN profile.
    This surfaced a TCP connection to `18.194.10.142:8883` — **MQTTS**,
    Tuya's real-time device control/status broker — timed exactly with a
    brew command.
  - This connection came through as opaque raw TCP even under mitmproxy's
    interception (rather than being decrypted), consistent with
    certificate pinning on the MQTT socket specifically. Decrypting it
    would require an active pinning bypass (Frida hooking, Phase 3 territory)
    — but turned out to be unnecessary (see Phase 3 below).

**Conclusion**: architecture is standard Tuya — REST (`a1.tuyaeu.com`) for
auth/config/metadata, MQTTS (`18.194.10.142:8883`, pinned) for real-time
control and status push.

## Phase 3 — Skipping APK/IPA reversal

Given the MQTT channel is pinned, the two options were: (a) defeat pinning
with Frida to read the raw MQTT payloads, or (b) skip the app entirely and
use **Tuya's own official Cloud IoT Platform**, which is the same backend
the app talks to.

(b) was taken, since it requires no reverse engineering of the client at
all — it's Tuya's documented, stable, versioned API, and it's how most
open-source Tuya integrations (e.g. Home Assistant's built-in `tuya`
integration, `tinytuya`, `localtuya`) work.

### Getting your own credentials

1. Sign up at [iot.tuya.com](https://iot.tuya.com), create a **Cloud
   Project** — critically, set **Data Center: Central Europe** (matches
   `tuyaeu.com`; the wrong data center means the device won't link).
2. Note the project's **Access ID** and **Access Secret** from its
   Overview tab.
3. **Linking the app account is the fiddly part.** The HomeDirect app has
   its own `smart321.com` universal-link domain registered exclusively to
   itself — its device-share links and QR codes always open HomeDirect,
   never a generic Tuya app, even via Safari or after offloading the app.
   There's no way to link a HomeDirect account directly to a Cloud
   Project through the standard "Link Tuya App Account" QR flow.

   The workaround: **re-pair the physical device to the Smart Life app**
   (Tuya's own generic consumer app, which *is* linkable):
   - Factory-reset the machine's Wi-Fi via its own touchscreen:
     Settings → **WLAN SET** → **AP MODE** → confirm — the Wi-Fi icon
     flashes quickly, and it broadcasts a `SL-HOMEDIRECT-XXXX` hotspot.
   - In Smart Life → Add Device → pick the matching category (or a
     generic EZ-mode/Wi-Fi device flow) → enter your 2.4GHz Wi-Fi
     password → manually join the `SL-HOMEDIRECT-XXXX` hotspot from iOS
     Wi-Fi settings when prompted → return to Smart Life to complete
     pairing.
   - This unbinds the device from HomeDirect (Tuya devices are bound to
     one account at a time) — expected and reversible by re-pairing back
     to HomeDirect later the same way, if desired.
   - Confirmed correct by the Device ID: `bfda99b991844fcd78xgyt` — this
     matched the **Virtual ID** shown earlier in the HomeDirect app's own
     device-info screen, proving it's the same physical unit.
4. Back in the Tuya IoT Platform project → **Devices** → **Link Tuya App
   Account** → scan the QR with **Smart Life** (not HomeDirect) → choose
   **Custom Link** (safer than Automatic if you have other Tuya devices
   on the same account) → grant **Controllable** permission.
5. Open the linked device's **Device Debugging** tab to get the full DP
   schema (see [Protocol.md](Protocol.md)) and confirm control works via
   the web UI's own test panel before writing any code against it.

## What wasn't needed

- APK/IPA decompilation (`jadx`, `apktool`)
- Frida-based SSL pinning bypass
- MITM'ing the MQTT channel
- Any credentials belonging to Beko/Arçelik/Tuya themselves — only your
  own Tuya IoT Platform project and your own device account
