"""Tests for Meteocat sensor platform setup."""

from unittest.mock import AsyncMock, Mock

from custom_components.meteocat.const import DOMAIN
from custom_components.meteocat.sensor import MeteocatSensor, async_setup_entry

COORDINATOR_KEYS = (
    "sensor_coordinator",
    "sensor_file_coordinator",
    "static_sensor_coordinator",
    "uvi_coordinator",
    "uvi_file_coordinator",
    "condition_coordinator",
    "daily_forecast_coordinator",
    "temp_forecast_coordinator",
    "entity_coordinator",
    "alerts_coordinator",
    "alerts_region_coordinator",
    "quotes_coordinator",
    "quotes_file_coordinator",
    "lightning_coordinator",
    "lightning_file_coordinator",
    "sun_coordinator",
    "sun_file_coordinator",
    "moon_coordinator",
    "moon_file_coordinator",
)


async def test_async_setup_entry_adds_sensors(hass):
    """Sensor setup registers entities from each coordinator group."""
    entry = Mock(entry_id="test_entry_id")
    entry_data = {
        "api_key": "fake_api_key",
        "town_name": "FakeTown",
        "town_id": "12345",
        "station_name": "FakeStation",
        "station_id": "67890",
        "region_name": "FakeRegion",
        "region_id": "1",
        "variable_name": "Temperature",
        "variable_id": "32",
        "limit_prediccio": 100,
        "_health": {},
        **{key: AsyncMock() for key in COORDINATOR_KEYS},
    }
    hass.data = {DOMAIN: {entry.entry_id: entry_data}}

    async_add_entities = Mock()

    await async_setup_entry(hass, entry, async_add_entities)

    assert async_add_entities.call_count > 0
    first_entities = list(async_add_entities.call_args_list[0].args[0])
    assert first_entities
    assert isinstance(first_entities[0], MeteocatSensor)
