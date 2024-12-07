from __future__ import annotations

import os
import logging
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from .coordinator import MeteocatSensorCoordinator, MeteocatEntityCoordinator
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "0.1.23"


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Configuración inicial del componente Meteocat."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura una entrada de configuración para Meteocat."""
    _LOGGER.info("Configurando la integración de Meteocat...")

    # Extraer los datos necesarios de la entrada de configuración
    entry_data = entry.data

    # Validar que todos los campos requeridos estén presentes
    required_fields = [
        "api_key", "town_name", "town_id", "variable_name",
        "variable_id", "station_name", "station_id"
    ]
    if not all(field in entry_data for field in required_fields):
        _LOGGER.error("Faltan datos en la configuración. Por favor, reconfigura la integración.")
        return False

    _LOGGER.info(
        f"Integración configurada para el municipio '{entry_data['town_name']}' "
        f"(ID: {entry_data['town_id']}), variable '{entry_data['variable_name']}' "
        f"(ID: {entry_data['variable_id']}), estación '{entry_data['station_name']}' "
        f"(ID: {entry_data['station_id']})."
    )

    # Inicializa y refresca los coordinadores
    try:
        # Crear el coordinador para sensores
        sensor_coordinator = MeteocatSensorCoordinator(
            hass=hass,
            entry_data=entry_data,  # Pasa los datos como un diccionario
        )

        # Crear el coordinador para entidades de predicción
        entity_coordinator = MeteocatEntityCoordinator(
            hass=hass,
            entry_data=entry_data,  # Pasa los mismos datos
        )

        # Ejecutar la primera actualización
        await sensor_coordinator.async_config_entry_first_refresh()
        await entity_coordinator.async_config_entry_first_refresh()
    except HomeAssistantError as err:
        _LOGGER.error(f"Error al inicializar los coordinadores: {err}")
        return False

    # Guardar los coordinadores en hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "sensor_coordinator": sensor_coordinator,
        "entity_coordinator": entity_coordinator,
        **entry_data,
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
