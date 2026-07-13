"""Constants for the Beko BrewConnect integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "beko_brewconnect"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_DEVICE_ID = "device_id"
CONF_REGION = "region"

DEFAULT_REGION = "eu"
REGIONS = ["eu", "us", "cn", "in"]

UPDATE_INTERVAL = timedelta(seconds=20)

# Local (non-DP) history storage
STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = f"{DOMAIN}_{{device_id}}_history"
