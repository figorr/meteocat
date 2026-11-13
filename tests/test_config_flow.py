"""Tests for the Meteocat config flow API key step."""

from datetime import timedelta
from typing import ClassVar
from unittest.mock import AsyncMock

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteocat import config_flow as cf
from custom_components.meteocat.const import (
    CONF_API_KEY,
    CONF_API_KEY_DATE,
    CONF_API_KEY_REMINDER,
    DOMAIN,
)


class FakeTown:
    """Fake Meteocat town client."""

    instances: ClassVar[list["FakeTown"]] = []

    def __init__(self, api_key: str, session=None) -> None:
        self.api_key = api_key
        self.session = session
        self.instances.append(self)

    async def get_municipis(self) -> list[dict[str, str]]:
        return [{"codi": "08019", "nom": "Barcelona"}]


def make_flow(hass):
    """Create a user config flow."""
    flow = cf.MeteocatConfigFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "test-flow"
    flow.context = {"source": "user"}
    return flow


def patch_clients(monkeypatch) -> None:
    """Replace the API client with a fake."""
    monkeypatch.setattr(cf, "MeteocatTown", FakeTown)


def make_reauth_entry(
    *,
    api_key: str = "old-api-key",
    issue_date: str = "2025-01-15",
) -> MockConfigEntry:
    """Create a config entry for reauthentication tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: api_key,
            CONF_API_KEY_DATE: issue_date,
        },
        entry_id="reauth-entry",
    )


def make_reauth_flow(hass, entry):
    """Create a reauth flow for an entry."""
    flow = make_flow(hass)
    flow.context = {"source": SOURCE_REAUTH, "entry_id": entry.entry_id}
    return flow


async def test_user_form_defaults_to_today(hass) -> None:
    """The initial form suggests today and reminders disabled."""
    result = await make_flow(hass).async_step_user()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_rejects_future_date(hass, monkeypatch) -> None:
    """Reject dates in the future without contacting the API."""
    town = AsyncMock()
    monkeypatch.setattr(cf, "MeteocatTown", town)
    future_date = (dt_util.now().date() + timedelta(days=1)).isoformat()

    result = await make_flow(hass).async_step_user(
        {
            CONF_API_KEY: "test-api-key",
            CONF_API_KEY_DATE: future_date,
            CONF_API_KEY_REMINDER: True,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_API_KEY_DATE: "invalid_date"}
    town.assert_not_called()


async def test_user_stores_date_and_reminder(hass, monkeypatch) -> None:
    """Store the submitted date and reminder flag before selecting a town."""
    patch_clients(monkeypatch)
    FakeTown.instances.clear()
    flow = make_flow(hass)
    flow.fetch_and_save_quotes = AsyncMock()
    flow.create_alerts_file = AsyncMock()

    result = await flow.async_step_user(
        {
            CONF_API_KEY: "test-api-key",
            CONF_API_KEY_DATE: "2025-01-15",
            CONF_API_KEY_REMINDER: True,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_municipi"
    assert flow.api_key == "test-api-key"
    assert flow.api_key_date == "2025-01-15"
    assert flow.api_key_reminder is True
    assert flow.municipis == [{"codi": "08019", "nom": "Barcelona"}]
    flow.fetch_and_save_quotes.assert_awaited_once_with("test-api-key")
    assert FakeTown.instances[-1].session is async_get_clientsession(hass)


async def test_user_empty_date_uses_today(hass, monkeypatch) -> None:
    """An empty optional date should default to today."""
    patch_clients(monkeypatch)
    flow = make_flow(hass)
    flow.fetch_and_save_quotes = AsyncMock()
    flow.create_alerts_file = AsyncMock()

    result = await flow.async_step_user(
        {
            CONF_API_KEY: "test-api-key",
            CONF_API_KEY_DATE: "",
            CONF_API_KEY_REMINDER: False,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_municipi"
    assert flow.api_key_date == dt_util.now().date().isoformat()
    assert flow.api_key_reminder is False


async def test_reauth_same_key_preserves_issue_date(hass, monkeypatch) -> None:
    """Reauth with the same key keeps the stored issue date."""
    patch_clients(monkeypatch)
    entry = make_reauth_entry()
    entry.add_to_hass(hass)

    result = await make_reauth_flow(hass, entry).async_step_reauth_confirm(
        {CONF_API_KEY: "old-api-key"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "old-api-key"
    assert entry.data[CONF_API_KEY_DATE] == "2025-01-15"


async def test_reauth_new_key_uses_explicit_date(hass, monkeypatch) -> None:
    """Reauth with a new key stores the supplied issue date."""
    patch_clients(monkeypatch)
    entry = make_reauth_entry()
    entry.add_to_hass(hass)

    result = await make_reauth_flow(hass, entry).async_step_reauth_confirm(
        {
            CONF_API_KEY: "new-api-key",
            CONF_API_KEY_DATE: "2025-02-15",
        }
    )

    assert result["type"] is FlowResultType.ABORT
    assert entry.data[CONF_API_KEY] == "new-api-key"
    assert entry.data[CONF_API_KEY_DATE] == "2025-02-15"


async def test_reauth_new_key_without_date_uses_today(hass, monkeypatch) -> None:
    """Reauth with a new key and no date defaults to today."""
    patch_clients(monkeypatch)
    entry = make_reauth_entry()
    entry.add_to_hass(hass)

    result = await make_reauth_flow(hass, entry).async_step_reauth_confirm(
        {CONF_API_KEY: "new-api-key"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert entry.data[CONF_API_KEY] == "new-api-key"
    assert entry.data[CONF_API_KEY_DATE] == dt_util.now().date().isoformat()


async def test_reauth_rejects_future_date(hass, monkeypatch) -> None:
    """Reauth rejects future issue dates without changing the entry."""
    patch_clients(monkeypatch)
    FakeTown.instances.clear()
    entry = make_reauth_entry()
    entry.add_to_hass(hass)
    future_date = (dt_util.now().date() + timedelta(days=1)).isoformat()

    result = await make_reauth_flow(hass, entry).async_step_reauth_confirm(
        {
            CONF_API_KEY: "new-api-key",
            CONF_API_KEY_DATE: future_date,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {CONF_API_KEY_DATE: "invalid_date"}
    assert entry.data[CONF_API_KEY] == "old-api-key"
    assert entry.data[CONF_API_KEY_DATE] == "2025-01-15"
    assert FakeTown.instances == []
