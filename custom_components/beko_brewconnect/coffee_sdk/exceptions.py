"""Exception hierarchy for the coffee_sdk package."""

from __future__ import annotations


class CoffeeSDKError(Exception):
    """Base class for all errors raised by coffee_sdk."""


class AuthenticationError(CoffeeSDKError):
    """Raised when authentication with the Tuya Cloud API fails."""


class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired and could not be refreshed."""


class APIError(CoffeeSDKError):
    """Raised when the Tuya Cloud API returns an error response.

    Attributes:
        code: The Tuya API error code (e.g. 1010, 2010).
        msg: The human-readable error message returned by the API.
    """

    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"Tuya API error {code}: {msg}")


class DeviceOfflineError(CoffeeSDKError):
    """Raised when a command is sent to a device that is reported offline."""


class InvalidDrinkError(CoffeeSDKError):
    """Raised when a requested drink is not in the device's supported drink_set."""
