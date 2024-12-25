import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import mock_component
from homeassistant.setup import async_setup_component

@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass: HomeAssistant):
    """Enable custom integrations."""
    mock_component(hass, "meteocat")
    await async_setup_component(hass, 'meteocat', {})
    yield
