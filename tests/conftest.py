"""Fixtures for testing."""

import pytest
import sys
import os
from homeassistant.setup import async_setup_component
from homeassistant.core import HomeAssistant

# Agregar el directorio raíz al PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Habilitar la integración personalizada 'meteocat' en el entorno de pruebas
@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass: HomeAssistant):
    """Enable custom integrations."""
    # Aquí se puede habilitar la integración personalizada 'meteocat'
    await async_setup_component(hass, 'meteocat', {})
    yield
    # Si es necesario, puedes hacer limpieza después de cada prueba
