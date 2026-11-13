"""Tests for the Meteocat config flow API key step."""

from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.meteocat import config_flow as cf
from custom_components.meteocat.const import (
    CONF_API_KEY,
    CONF_API_KEY_DATE,
    CONF_API_KEY_REMINDER,
    DOMAIN,
)


class FakeTown:
    """Fake Meteocat town client."""

    def __init__(self, api_key: str, session=None) -> None:
        self.api_key = api_key
        self.session = session

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
