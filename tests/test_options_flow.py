"""Tests for the Meteocat options flow."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.components import persistent_notification
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteocat import options_flow as of
from custom_components.meteocat.const import (
    ALTITUDE,
    CONF_API_KEY,
    CONF_API_KEY_DATE,
    CONF_API_KEY_REMINDER,
    DOMAIN,
    LATITUDE,
    LIMIT_BASIC,
    LIMIT_PREDICCIO,
    LIMIT_QUOTA,
    LIMIT_XDDE,
    LIMIT_XEMA,
    LONGITUDE,
    REGION_ID,
    REGION_NAME,
    STATION_ID,
    STATION_NAME,
    TOWN_ID,
    TOWN_NAME,
    VARIABLE_ID,
    VARIABLE_NAME,
)


class FakeTown:
    """Fake Meteocat town client."""

    def __init__(self, api_key: str, session=None) -> None:
        self.api_key = api_key
        self.session = session

    async def get_municipis(self) -> list[dict[str, str]]:
        return [{"codi": "08019", "nom": "Barcelona"}]


ENTRY_DATA = {
    CONF_API_KEY: "test-api-key",
    TOWN_NAME: "Barcelona",
    TOWN_ID: "08019",
    VARIABLE_NAME: "Temperatura",
    VARIABLE_ID: "32",
    STATION_NAME: "Barcelona - El Raval",
    STATION_ID: "X4",
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


def make_entry(*, data=None, options=None) -> MockConfigEntry:
    """Create a config entry with the full Meteocat payload."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, **(data or {})},
        options=options or {},
        unique_id="08019_X4",
        entry_id="entry1",
    )


def make_flow(hass, entry):
    """Create an options flow for an entry."""
    flow = of.MeteocatOptionsFlowHandler(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    flow.flow_id = "options-flow"
    return flow


async def test_update_limits_preserves_options(hass, monkeypatch) -> None:
    """Limits-only updates must not drop stored options."""
    reload = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry(options={"preserved": True})
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_limits_only(
        {
            LIMIT_XEMA: 500,
            LIMIT_PREDICCIO: 90,
            LIMIT_XDDE: 200,
            LIMIT_QUOTA: 250,
            LIMIT_BASIC: 1500,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"preserved": True}
    reload.assert_awaited_once_with(entry.entry_id)


async def test_update_api_and_limits_saves_date_and_reminder(hass, monkeypatch) -> None:
    """Update the API key date and reminder flag."""
    monkeypatch.setattr(of, "MeteocatTown", FakeTown)
    reload = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry(
        data={CONF_API_KEY_DATE: "2025-01-15"},
        options={CONF_API_KEY_REMINDER: True},
    )
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY: ENTRY_DATA[CONF_API_KEY],
            CONF_API_KEY_DATE: "2025-02-15",
            CONF_API_KEY_REMINDER: True,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_API_KEY_DATE] == "2025-02-15"
    assert result["data"][CONF_API_KEY_REMINDER] is True
    reload.assert_awaited_once_with(entry.entry_id)


async def test_update_api_and_limits_rejects_future_date(hass, monkeypatch) -> None:
    """Reject issue dates in the future without calling the API."""
    town = AsyncMock()
    reload = AsyncMock()
    monkeypatch.setattr(of, "MeteocatTown", town)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry()
    entry.add_to_hass(hass)
    future_date = (dt_util.now().date() + timedelta(days=1)).isoformat()

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY: "new-api-key",
            CONF_API_KEY_DATE: future_date,
            CONF_API_KEY_REMINDER: True,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_API_KEY_DATE: "invalid_date"}
    town.assert_not_called()
    reload.assert_not_awaited()
    assert entry.data[CONF_API_KEY] == ENTRY_DATA[CONF_API_KEY]
    assert CONF_API_KEY_DATE not in entry.data


async def test_same_key_empty_date_preserves_stored_date(hass, monkeypatch) -> None:
    """An empty date for the same key keeps the stored issue date."""
    monkeypatch.setattr(of, "MeteocatTown", FakeTown)
    reload = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry(data={CONF_API_KEY_DATE: "2025-01-15"})
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY: ENTRY_DATA[CONF_API_KEY],
            CONF_API_KEY_DATE: "",
            CONF_API_KEY_REMINDER: False,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_API_KEY_DATE] == "2025-01-15"
    reload.assert_awaited_once_with(entry.entry_id)


async def test_new_key_uses_explicit_date(hass, monkeypatch) -> None:
    """A new API key stores the explicitly supplied issue date."""
    monkeypatch.setattr(of, "MeteocatTown", FakeTown)
    reload = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry(data={CONF_API_KEY_DATE: "2025-01-15"})
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY: "new-api-key",
            CONF_API_KEY_DATE: "2025-02-15",
            CONF_API_KEY_REMINDER: False,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_API_KEY] == "new-api-key"
    assert entry.data[CONF_API_KEY_DATE] == "2025-02-15"
    reload.assert_awaited_once_with(entry.entry_id)


async def test_new_key_with_empty_date_uses_today(hass, monkeypatch) -> None:
    """A new API key with an empty date defaults to today."""
    monkeypatch.setattr(of, "MeteocatTown", FakeTown)
    reload = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry(data={CONF_API_KEY_DATE: "2025-01-15"})
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY: "new-api-key",
            CONF_API_KEY_DATE: "",
            CONF_API_KEY_REMINDER: False,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_API_KEY] == "new-api-key"
    assert entry.data[CONF_API_KEY_DATE] == dt_util.now().date().isoformat()
    reload.assert_awaited_once_with(entry.entry_id)


async def test_missing_key_and_empty_date_preserves_stored_date(
    hass, monkeypatch
) -> None:
    """Omitting the API key and date keeps the existing values."""
    monkeypatch.setattr(of, "MeteocatTown", FakeTown)
    reload = AsyncMock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)

    entry = make_entry(data={CONF_API_KEY_DATE: "2025-01-15"})
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY_DATE: "",
            CONF_API_KEY_REMINDER: False,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_API_KEY] == ENTRY_DATA[CONF_API_KEY]
    assert entry.data[CONF_API_KEY_DATE] == "2025-01-15"
    reload.assert_awaited_once_with(entry.entry_id)


async def test_failed_reload_clears_reminder_and_notification(
    hass, monkeypatch
) -> None:
    """A failed reload still cancels the timer and notification first."""
    monkeypatch.setattr(of, "MeteocatTown", FakeTown)
    reload = AsyncMock(side_effect=RuntimeError("reload failed"))
    dismiss = Mock()
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)
    monkeypatch.setattr(
        persistent_notification, "async_dismiss", dismiss
    )

    unsub = Mock()
    entry = make_entry(data={CONF_API_KEY_DATE: "2025-01-15"})
    entry.runtime_data = SimpleNamespace(reminder_unsub=unsub)
    entry.add_to_hass(hass)

    flow = make_flow(hass, entry)
    try:
        await flow.async_step_update_api_and_limits(
            {
                CONF_API_KEY: ENTRY_DATA[CONF_API_KEY],
                CONF_API_KEY_DATE: "2025-02-15",
                CONF_API_KEY_REMINDER: False,
                LIMIT_XEMA: 700,
                LIMIT_PREDICCIO: 100,
                LIMIT_XDDE: 250,
                LIMIT_QUOTA: 300,
                LIMIT_BASIC: 2000,
            }
        )
    except RuntimeError as err:
        assert str(err) == "reload failed"
    else:
        raise AssertionError("Expected reload failure")

    unsub.assert_called_once_with()
    dismiss.assert_called_once_with(hass, f"meteocat_api_key_expiry_{entry.entry_id}")
    assert entry.runtime_data.reminder_unsub is None
    reload.assert_awaited_once_with(entry.entry_id)
    assert entry.data[CONF_API_KEY_DATE] == "2025-02-15"


async def test_reminder_without_date_requires_date(hass) -> None:
    """Enabling reminders for an entry without a date must fail validation."""
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await make_flow(hass, entry).async_step_update_api_and_limits(
        {
            CONF_API_KEY: ENTRY_DATA[CONF_API_KEY],
            CONF_API_KEY_REMINDER: True,
            LIMIT_XEMA: 700,
            LIMIT_PREDICCIO: 100,
            LIMIT_XDDE: 250,
            LIMIT_QUOTA: 300,
            LIMIT_BASIC: 2000,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_API_KEY_DATE: "date_required"}

