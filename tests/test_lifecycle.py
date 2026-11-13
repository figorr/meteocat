"""Tests for the Meteocat config entry lifecycle."""

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, Mock

from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.meteocat as integration
from custom_components.meteocat.const import (
    ALTITUDE,
    CONF_API_KEY,
    CONF_API_KEY_DATE,
    DOMAIN,
    LATITUDE,
    LIMIT_BASIC,
    LIMIT_PREDICCIO,
    LIMIT_QUOTA,
    LIMIT_XDDE,
    LIMIT_XEMA,
    LONGITUDE,
    PROVINCE_ID,
    PROVINCE_NAME,
    REGION_ID,
    REGION_NAME,
    STATION_ID,
    STATION_NAME,
    TOWN_ID,
    TOWN_NAME,
    VARIABLE_ID,
    VARIABLE_NAME,
)

ENTRY_DATA = {
    CONF_API_KEY: "test-api-key",
    CONF_API_KEY_DATE: "2025-01-15",
    TOWN_NAME: "Barcelona",
    TOWN_ID: "08019",
    VARIABLE_NAME: "Temperatura",
    VARIABLE_ID: "32",
    STATION_NAME: "Barcelona - El Raval",
    STATION_ID: "X4",
    PROVINCE_NAME: "Barcelona",
    PROVINCE_ID: "08",
    REGION_NAME: "Barcelonès",
    REGION_ID: "13",
    LATITUDE: 41.38,
    LONGITUDE: 2.17,
    ALTITUDE: 12,
    LIMIT_XEMA: 750,
    LIMIT_PREDICCIO: 100,
    LIMIT_XDDE: 250,
    LIMIT_QUOTA: 300,
    LIMIT_BASIC: 2000,
}


class FakeCoordinator:
    """Minimal coordinator used by setup tests."""

    instances: ClassVar[list["FakeCoordinator"]] = []

    def __init__(self, hass=None, entry_data=None) -> None:
        self.hass = hass
        self.entry_data = entry_data
        self.data = {"ok": True}
        self.listeners = []
        type(self).instances.append(self)

    async def async_config_entry_first_refresh(self) -> None:
        """Simulate a successful first refresh."""

    def async_add_listener(self, callback):
        self.listeners.append(callback)
        return lambda: self.listeners.remove(callback)


def make_entry(*, entry_id: str = "lifecycle-entry") -> MockConfigEntry:
    """Create a fully populated config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        entry_id=entry_id,
    )


def make_cache() -> SimpleNamespace:
    """Create a fake cache with the lifecycle methods."""
    return SimpleNamespace(
        async_load=AsyncMock(),
        async_keys=AsyncMock(return_value=[]),
        async_remove=AsyncMock(),
    )


async def test_setup_schedules_reminder_and_registers_unload(hass, monkeypatch) -> None:
    """Setup forwards platforms and registers the reminder cleanup."""
    cache = make_cache()
    monkeypatch.setattr(integration, "get_cache", Mock(return_value=cache))
    monkeypatch.setattr(integration, "async_migrate_legacy_quotes", AsyncMock())
    monkeypatch.setattr(integration, "ensure_assets_exist", AsyncMock())
    monkeypatch.setattr(
        integration,
        "_get_coordinator_module",
        lambda _name: FakeCoordinator,
    )
    forward = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", forward)
    unsub = Mock()
    schedule = Mock(return_value=unsub)
    monkeypatch.setattr(integration, "async_schedule_api_key_reminder", schedule)
    on_unload = Mock()
    FakeCoordinator.instances.clear()

    entry = make_entry()
    entry.add_to_hass(hass)
    entry.async_on_unload = on_unload

    assert await integration.async_setup_entry(hass, entry) is True

    cache.async_load.assert_awaited_once()
    forward.assert_awaited_once_with(entry, integration.PLATFORMS)
    schedule.assert_called_once_with(hass, entry)
    on_unload.assert_called_once_with(unsub)
    assert entry.runtime_data.reminder_unsub is unsub
    assert hass.data[DOMAIN][entry.entry_id]["_health"]["sensor_coordinator"] == {
        "status": "ok",
        "reason": "",
        "last_error": "",
    }
    assert hass.data[DOMAIN][entry.entry_id]["sensor_coordinator"] in (
        FakeCoordinator.instances
    )


async def test_unload_removes_entry_data_and_cancels_reminder(hass, monkeypatch) -> None:
    """Unload removes entry data, unloads platforms and cancels reminders."""
    entry = make_entry(entry_id="unload-entry")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"data": True}
    hass.data[DOMAIN]["other-entry"] = {"keep": True}
    unload = AsyncMock(return_value=True)
    cancel = Mock()
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", unload)
    monkeypatch.setattr(integration, "async_get_platforms", Mock(return_value=[]))
    monkeypatch.setattr(integration, "async_cancel_api_key_reminder", cancel)

    result = await integration.async_unload_entry(hass, entry)

    assert result is True
    unload.assert_awaited_once_with(entry, integration.PLATFORMS)
    cancel.assert_called_once_with(hass, entry)
    assert entry.entry_id not in hass.data[DOMAIN]
    assert hass.data[DOMAIN]["other-entry"] == {"keep": True}


async def test_failed_unload_keeps_entry_data_and_reminder(hass, monkeypatch) -> None:
    """A failed platform unload leaves the entry data and reminder intact."""
    entry = make_entry(entry_id="unload-failure-entry")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"data": True}
    unload = AsyncMock(return_value=False)
    cancel = Mock()
    monkeypatch.setattr(hass.config_entries, "async_unload_platforms", unload)
    monkeypatch.setattr(integration, "async_get_platforms", Mock(return_value=[]))
    monkeypatch.setattr(integration, "async_cancel_api_key_reminder", cancel)

    result = await integration.async_unload_entry(hass, entry)

    assert result is False
    unload.assert_awaited_once_with(entry, integration.PLATFORMS)
    cancel.assert_not_called()
    assert entry.entry_id in hass.data[DOMAIN]


async def test_remove_entry_cancels_reminder_and_cleans_cache(hass, monkeypatch) -> None:
    """Removing the last entry cancels reminders and clears the cache."""
    cache = make_cache()
    cancel = Mock()
    monkeypatch.setattr(integration, "get_cache", Mock(return_value=cache))
    monkeypatch.setattr(integration, "async_cancel_api_key_reminder", cancel)

    entry = make_entry(entry_id="remove-entry")
    entry.add_to_hass(hass)

    await integration.async_remove_entry(hass, entry)

    cancel.assert_called_once_with(hass, entry)
    cache.async_load.assert_awaited_once()
    cache.async_remove.assert_awaited_once()
