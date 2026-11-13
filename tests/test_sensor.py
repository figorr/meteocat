"""Tests for Meteocat sensor platform setup."""

from datetime import date
from unittest.mock import AsyncMock, Mock

from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteocat.const import (
    API_KEY_FINGERPRINT,
    CONF_API_KEY,
    CONF_API_KEY_DATE,
    CONF_API_KEY_REMINDER,
    DOMAIN,
)
from custom_components.meteocat.helpers import get_quotes_id
from custom_components.meteocat.sensor import (
    SENSOR_TYPES,
    MeteocatSensor,
    MeteocatStaticSensor,
    async_setup_entry,
)

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

    entities = [
        entity
        for call in async_add_entities.call_args_list
        for entity in call.args[0]
    ]
    static_keys = {
        entity.entity_description.key
        for entity in entities
        if isinstance(entity, MeteocatStaticSensor)
    }
    assert {
        CONF_API_KEY_DATE,
        CONF_API_KEY_REMINDER,
        API_KEY_FINGERPRINT,
    } <= static_keys


def make_static_sensor(hass, entry_data, key):
    """Create a static diagnostic sensor for a key."""
    description = next(item for item in SENSOR_TYPES if item.key == key)
    sensor = MeteocatStaticSensor(Mock(), description, entry_data)
    sensor.hass = hass
    return sensor


async def test_api_key_diagnostic_sensors(hass) -> None:
    """Diagnostic sensors expose only non-sensitive API key metadata."""
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "secret-key"},
        entry_id="entry-a",
    )
    entry_b = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "secret-key"},
        entry_id="entry-b",
    )
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    entry_data = {
        CONF_API_KEY: "secret-key",
        CONF_API_KEY_DATE: "2025-01-15",
        CONF_API_KEY_REMINDER: True,
        "town_name": "FakeTown",
        "town_id": "12345",
        "station_name": "FakeStation",
        "station_id": "67890",
        "region_name": "FakeRegion",
        "region_id": "1",
    }

    date_sensor = make_static_sensor(hass, entry_data, CONF_API_KEY_DATE)
    assert date_sensor.native_value == date(2025, 1, 15)
    assert date_sensor.entity_category is EntityCategory.DIAGNOSTIC
    date_attributes = date_sensor.extra_state_attributes
    assert date_attributes["expiry_date"] == "2026-01-15"
    assert isinstance(date_attributes["days_until_expiry"], int)

    reminder_sensor = make_static_sensor(hass, entry_data, CONF_API_KEY_REMINDER)
    assert reminder_sensor.native_value == "enabled"
    assert reminder_sensor.entity_category is EntityCategory.DIAGNOSTIC

    fingerprint_sensor = make_static_sensor(hass, entry_data, API_KEY_FINGERPRINT)
    fingerprint = fingerprint_sensor.native_value
    assert fingerprint == get_quotes_id("secret-key")[:8]
    assert "secret-key" not in fingerprint
    assert fingerprint_sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert fingerprint_sensor.extra_state_attributes["entries_using_key"] == 2


async def test_reminder_sensor_reports_disabled(hass) -> None:
    """The reminder sensor reports the disabled option."""
    entry_data = {
        CONF_API_KEY: "secret-key",
        CONF_API_KEY_DATE: "2025-01-15",
        CONF_API_KEY_REMINDER: False,
        "town_name": "FakeTown",
        "town_id": "12345",
        "station_name": "FakeStation",
        "station_id": "67890",
        "region_name": "FakeRegion",
        "region_id": "1",
    }

    sensor = make_static_sensor(hass, entry_data, CONF_API_KEY_REMINDER)

    assert sensor.native_value == "disabled"
