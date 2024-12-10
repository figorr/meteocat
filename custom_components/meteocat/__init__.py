from __future__ import annotations

import os
import logging
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import async_get_platforms

from .coordinator import MeteocatSensorCoordinator #, MeteocatEntityCoordinator
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "0.1.27"


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Configuración inicial del componente Meteocat."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura una entrada de configuración para Meteocat."""
    _LOGGER.info("Configurando la integración de Meteocat...")

    # Extraer los datos necesarios de la entrada de configuración
    entry_data = entry.data

    # Validar campos requeridos
    required_fields = [
        "api_key", "town_name", "town_id", "variable_name",
        "variable_id", "station_name", "station_id"
    ]
    missing_fields = [field for field in required_fields if field not in entry_data]
    if missing_fields:
        _LOGGER.error(f"Faltan los siguientes campos en la configuración: {missing_fields}")
        return False

    _LOGGER.debug(
        f"Datos de configuración: Municipio '{entry_data['town_name']}' (ID: {entry_data['town_id']}), "
        f"Variable '{entry_data['variable_name']}' (ID: {entry_data['variable_id']}), "
        f"Estación '{entry_data['station_name']}' (ID: {entry_data['station_id']})."
    )

    # Inicializar coordinadores
    try:
        sensor_coordinator = MeteocatSensorCoordinator(hass=hass, entry_data=entry_data)
        # entity_coordinator = MeteocatEntityCoordinator(hass=hass, entry_data=entry_data)

        await sensor_coordinator.async_config_entry_first_refresh()
        # await entity_coordinator.async_config_entry_first_refresh()
    except Exception as err:  # Capturar todos los errores
        _LOGGER.exception(f"Error al inicializar los coordinadores: {err}")
        return False

    # Guardar coordinadores y datos en hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "sensor_coordinator": sensor_coordinator,
        # "entity_coordinator": entity_coordinator,
        **entry_data,
    }

    # Configurar plataformas
    _LOGGER.debug(f"Cargando plataformas: {PLATFORMS}")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Desactiva una entrada de configuración para Meteocat."""
    platforms = async_get_platforms(hass, DOMAIN)
    _LOGGER.info(f"Descargando plataformas: {[p.domain for p in platforms]}")

    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Limpia cualquier dato adicional al desinstalar la integración."""
    _LOGGER.info(f"Eliminando datos residuales de la integración: {entry.entry_id}")

    # Definir las rutas de los archivos y carpetas a eliminar
    custom_components_path = hass.config.path("custom_components", DOMAIN)
    assets_folder = os.path.join(custom_components_path, "assets")
    files_folder = os.path.join(custom_components_path, "files")
    symbols_file = os.path.join(assets_folder, "symbols.json")
    station_data_file = os.path.join(files_folder, "station_data.json")

    # Eliminar el archivo symbols.json si existe
    try:
        if os.path.exists(symbols_file):
            os.remove(symbols_file)
            _LOGGER.info("Archivo symbols.json eliminado correctamente.")
        else:
            _LOGGER.info("El archivo symbols.json no se encontró.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar el archivo symbols.json: {e}")

    # Eliminar el archivo station_data.json si existe
    try:
        if os.path.exists(station_data_file):
            os.remove(station_data_file)
            _LOGGER.info("Archivo station_data.json eliminado correctamente.")
        else:
            _LOGGER.info("El archivo station_data.json no se encontró.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar el archivo station_data.json: {e}")

    # Eliminar la carpeta assets si está vacía
    try:
        if os.path.exists(assets_folder) and not os.listdir(assets_folder):
            os.rmdir(assets_folder)
            _LOGGER.info("Carpeta assets eliminada correctamente.")
        elif os.path.exists(assets_folder):
            _LOGGER.warning("La carpeta assets no está vacía y no se pudo eliminar.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar la carpeta assets: {e}")
    
    # Eliminar la carpeta files si está vacía
    try:
        if os.path.exists(files_folder) and not os.listdir(files_folder):
            os.rmdir(files_folder)
            _LOGGER.info("Carpeta files eliminada correctamente.")
        elif os.path.exists(files_folder):
            _LOGGER.warning("La carpeta files no está vacía y no se pudo eliminar.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar la carpeta files: {e}")
