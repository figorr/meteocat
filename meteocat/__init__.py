from __future__ import annotations

import os
import logging
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .coordinator import MeteocatSensorCoordinator, MeteocatEntityCoordinator
from .const import (
    DOMAIN,
    CONF_API_KEY,
    TOWN_NAME,
    TOWN_ID,
    VARIABLE_NAME,
    VARIABLE_ID,
    STATION_NAME,
    STATION_ID,
)

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "0.1.17"

# Plataformas soportadas por la integración
PLATFORMS = ["sensor", "entity"]


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Configuración inicial del componente Meteocat."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura una entrada de configuración para Meteocat."""
    _LOGGER.info("Configurando la integración de Meteocat...")

    # Extraer los datos necesarios de la entrada de configuración
    entry_data = entry.data
    required_fields = [
        CONF_API_KEY, TOWN_NAME, TOWN_ID, VARIABLE_ID, STATION_NAME, STATION_ID
    ]

    # Validar que todos los campos requeridos estén presentes
    if not all(field in entry_data for field in required_fields):
        _LOGGER.error("Faltan datos en la configuración. Por favor, reconfigura la integración.")
        return False

    api_key = entry_data[CONF_API_KEY]
    town_name = entry_data[TOWN_NAME]
    town_id = entry_data[TOWN_ID]
    variable_name = entry_data[VARIABLE_NAME]
    variable_id = entry_data[VARIABLE_ID]
    station_name = entry_data[STATION_NAME]
    station_id = entry_data[STATION_ID]

    _LOGGER.info(
        f"Integración configurada para el municipio '{town_name}' (ID: {town_id}), "
        f"variable '{variable_name}' (ID: {variable_id}), estación {station_name} (ID: {station_id})."
    )

    # Inicializa y refresca los coordinadores
    try:
        # Pasar los datos adicionales al constructor del coordinador
        sensor_coordinator = MeteocatSensorCoordinator(
            hass,
            entry,
            town_name=town_name,
            town_id=town_id,
            station_name=station_name,
            station_id=station_id,
            variable_name=variable_name,
            variable_id=variable_id,
        )
        # Pasar los mismos datos al constructor de MeteocatEntityCoordinator
        entity_coordinator = MeteocatEntityCoordinator(
            hass,
            entry,
            town_name=town_name,
            town_id=town_id,
            station_name=station_name,
            station_id=station_id,
            variable_name=variable_name,
            variable_id=variable_id,
        )

        await sensor_coordinator.async_config_entry_first_refresh()
        await entity_coordinator.async_config_entry_first_refresh()
    except HomeAssistantError as err:
        _LOGGER.error(f"Error al inicializar los coordinadores: {err}")
        return False

    # Guardar los datos y los coordinadores en hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "sensor_coordinator": sensor_coordinator,
        "entity_coordinator": entity_coordinator,
        "api_key": api_key,
        "town_id": town_id,
        "town_name": town_name,
        "station_id": station_id,
        "station_name": station_name,
        "variable_id": variable_id,
        "variable_name": variable_name,
    }

    # Configurar las plataformas
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Desactiva una entrada de configuración para Meteocat."""
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:  # Si no quedan entradas, elimina el dominio
            hass.data.pop(DOMAIN)

    # Desinstalar las plataformas
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Limpia cualquier dato adicional al desinstalar la integración."""
    _LOGGER.info(f"Eliminando datos residuales de la integración: {entry.entry_id}")

    # Definir la ruta del archivo de símbolos
    assets_folder = hass.config.path("custom_components", DOMAIN, "assets")
    symbols_file = os.path.join(assets_folder, "symbols.json")

    try:
        if os.path.exists(symbols_file):
            os.remove(symbols_file)
            _LOGGER.info("Archivo symbols.json eliminado correctamente.")
        else:
            _LOGGER.info("El archivo symbols.json no se encontró.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar el archivo symbols.json: {e}")
