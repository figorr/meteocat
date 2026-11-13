"""Tests for Meteocat sensor coordinator error handling."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from meteocatpy.exceptions import ForbiddenError, TooManyRequestsError

from custom_components.meteocat.coordinator import MeteocatSensorCoordinator

ENTRY_DATA = {
    "api_key": "fake_api_key",
    "town_name": "FakeTown",
    "town_id": "12345",
    "station_name": "FakeStation",
    "station_id": "67890",
    "variable_name": "Temperature",
    "variable_id": "32",
}


def make_coordinator(hass):
    """Create a sensor coordinator with test entry data."""
    return MeteocatSensorCoordinator(hass, ENTRY_DATA)


async def test_coordinator_update_data_success(hass):
    """The coordinator returns station data and stores it in the cache."""
    coordinator = make_coordinator(hass)
    expected = [{"variables": [{"codi": "32", "lectures": []}]}]
    coordinator.meteocat_station_data.get_station_data = AsyncMock(
        return_value=expected
    )

    data = await coordinator._async_update_data()

    assert data == expected
    cached = await coordinator.station_file.async_read_json()
    assert cached["data"] == expected
    assert coordinator.meteocat_station_data._session is async_get_clientsession(hass)


async def test_coordinator_update_data_rate_limit(hass):
    """Too many requests become ConfigEntryNotReady."""
    coordinator = make_coordinator(hass)
    coordinator.meteocat_station_data.get_station_data = AsyncMock(
        side_effect=TooManyRequestsError("Too many requests")
    )

    with pytest.raises(ConfigEntryNotReady):
        await coordinator._async_update_data()


async def test_coordinator_update_data_forbidden_requests_reauth(hass):
    """Forbidden errors trigger reauthentication."""
    coordinator = make_coordinator(hass)
    coordinator.meteocat_station_data.get_station_data = AsyncMock(
        side_effect=ForbiddenError("Forbidden")
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_update_data_invalid_payload(hass):
    """Invalid API payloads fall back to an empty result."""
    coordinator = make_coordinator(hass)
    coordinator.meteocat_station_data.get_station_data = AsyncMock(
        return_value={"Temperature": 20.5}
    )

    assert await coordinator._async_update_data() == []
