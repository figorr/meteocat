from __future__ import annotations

import logging
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import (
    DOMAIN,
    CONF_API_KEY,
    TOWN_NAME,
    TOWN_ID,
    VARIABLE_ID,
    STATION_NAME,
    STATION_ID,
)

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "0.1.15"

PLATFORMS = ["sensor"]  # Define las plataformas a cargar

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Configuración inicial del componente Meteocat."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura una entrada de configuración para Meteocat."""
    _LOGGER.info("Configurando la integración de Meteocat...")

    # Verificar los datos guardados en la entrada
    api_key = entry.data.get(CONF_API_KEY)
    town_name = entry.data.get(TOWN_NAME)
    town_id = entry.data.get(TOWN_ID)
    variable_id = entry.data.get(VARIABLE_ID)
    station_name = entry.data.get(STATION_NAME)
    station_id = entry.data.get(STATION_ID)

    if not all([api_key, town_name, town_id, variable_id, station_id]):
        _LOGGER.error("Faltan datos en la configuración. Por favor, reconfigura la integración.")
        return False

    _LOGGER.info(
        f"Integración configurada para el municipio '{town_name}' (ID: {town_id}), "
        f"variable 'Temperatura' (ID: {variable_id}), estación {station_name} con '{station_id}'."
    )

    # Agregar datos de configuración al hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_API_KEY: api_key,
        TOWN_NAME: town_name,
        TOWN_ID: town_id,
        VARIABLE_ID: variable_id,
        STATION_NAME: station_name,
        STATION_ID: station_id,
    }

    # Configurar plataformas
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Desactiva una entrada de configuración para Meteocat."""
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)

    # Desinstalar plataformas
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
