from __future__ import annotations

import logging
from pathlib import Path
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import async_get_platforms

from .coordinator import (
    MeteocatSensorCoordinator,
    MeteocatStaticSensorCoordinator,
    MeteocatEntityCoordinator,
    MeteocatUviCoordinator,
    MeteocatUviFileCoordinator,
    HourlyForecastCoordinator,
    DailyForecastCoordinator,
    MeteocatConditionCoordinator,
    MeteocatTempForecastCoordinator,
)

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "0.1.41"

def safe_remove(path: Path, is_folder: bool = False):
    """Elimina de forma segura un archivo o carpeta si existe."""
    try:
        if is_folder and path.exists() and not any(path.iterdir()):
            path.rmdir()
            _LOGGER.info(f"Carpeta {path.name} eliminada correctamente.")
        elif not is_folder and path.exists():
            path.unlink()
            _LOGGER.info(f"Archivo {path.name} eliminado correctamente.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar {path.name}: {e}")

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
        await sensor_coordinator.async_config_entry_first_refresh()
        
        static_sensor_coordinator = MeteocatStaticSensorCoordinator(hass=hass, entry_data=entry_data)
        await sensor_coordinator.async_config_entry_first_refresh()

        entity_coordinator = MeteocatEntityCoordinator(hass=hass, entry_data=entry_data)
        await entity_coordinator.async_config_entry_first_refresh()

        uvi_coordinator = MeteocatUviCoordinator(hass=hass, entry_data=entry_data)
        await uvi_coordinator.async_config_entry_first_refresh()

        uvi_file_coordinator = MeteocatUviFileCoordinator(hass=hass, entry_data=entry_data)
        await uvi_file_coordinator.async_config_entry_first_refresh()

        hourly_forecast_coordinator = HourlyForecastCoordinator(hass=hass, entry_data=entry_data)
        await hourly_forecast_coordinator.async_config_entry_first_refresh()
        
        daily_forecast_coordinator = DailyForecastCoordinator(hass=hass, entry_data=entry_data)
        await daily_forecast_coordinator.async_config_entry_first_refresh()

        condition_coordinator = MeteocatConditionCoordinator(hass=hass, entry_data=entry_data)
        await condition_coordinator.async_config_entry_first_refresh()

        temp_forecast_coordinator = MeteocatTempForecastCoordinator(hass=hass, entry_data=entry_data)
        await temp_forecast_coordinator.async_config_entry_first_refresh()

    except Exception as err:  # Capturar todos los errores
        _LOGGER.exception(f"Error al inicializar los coordinadores: {err}")
        return False

    # Guardar coordinadores y datos en hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "sensor_coordinator": sensor_coordinator,
        "static_sensor_coordinator": static_sensor_coordinator,
        "entity_coordinator": entity_coordinator,
        "uvi_coordinator":  uvi_coordinator,
        "uvi_file_coordinator": uvi_file_coordinator,
        "hourly_forecast_coordinator": hourly_forecast_coordinator,
        "daily_forecast_coordinator": daily_forecast_coordinator,
        "condition_coordinator": condition_coordinator,
        "temp_forecast_coordinator": temp_forecast_coordinator,
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

    # Definir las rutas base a eliminar
    custom_components_path = Path(hass.config.path("custom_components")) / DOMAIN
    assets_folder = custom_components_path / "assets"
    files_folder = custom_components_path / "files"

    # Definir archivos relacionados a eliminar
    symbols_file = assets_folder / "symbols.json"
    variables_file = assets_folder / "variables.json"

    # Obtener el `station_id` para identificar el archivo a eliminar
    station_id = entry.data.get("station_id")
    if not station_id:
        _LOGGER.warning("No se encontró 'station_id' en la configuración. No se puede eliminar el archivo de datos de la estación.")
        return

    # Archivo JSON de la estación
    station_data_file = files_folder / f"station_{station_id.lower()}_data.json"

    # Obtener el `town_id` para identificar el archivo a eliminar
    town_id = entry.data.get("town_id")
    if not town_id:
        _LOGGER.warning("No se encontró 'town_id' en la configuración. No se puede eliminar el archivo de datos de la estación.")
        return

    # Archivo JSON UVI del municipio
    town_data_file = files_folder / f"uvi_{town_id.lower()}_data.json"

    # Arhivos JSON de las predicciones del municipio a eliminar
    forecast_hourly_data_file = files_folder / f"forecast_{town_id.lower()}_hourly_data.json"
    forecast_daily_data_file = files_folder / f"forecast_{town_id.lower()}_daily_data.json"

    # Validar la ruta base
    if not custom_components_path.exists():
        _LOGGER.warning(f"La ruta {custom_components_path} no existe. No se realizará la limpieza.")
        return

    # Eliminar archivos y carpetas
    safe_remove(symbols_file)
    safe_remove(variables_file)
    safe_remove(station_data_file)
    safe_remove(town_data_file)
    safe_remove(forecast_hourly_data_file)
    safe_remove(forecast_daily_data_file)
    safe_remove(assets_folder, is_folder=True)
    safe_remove(files_folder, is_folder=True)
