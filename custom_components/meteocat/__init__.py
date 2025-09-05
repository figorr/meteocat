from __future__ import annotations

import logging
import voluptuous as vol
from pathlib import Path
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers import config_validation as cv

from .helpers import get_storage_dir
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
    MeteocatAlertsCoordinator,
    MeteocatAlertsRegionCoordinator,
    MeteocatQuotesCoordinator,
    MeteocatQuotesFileCoordinator,
    MeteocatLightningCoordinator,
    MeteocatLightningFileCoordinator,
)

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "2.2.7"

# Definir el esquema de configuración CONFIG_SCHEMA
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("api_key"): cv.string,
                vol.Required("town_name"): cv.string,
                vol.Required("town_id"): cv.string,
                vol.Optional("variable_name", default="temperature"): cv.string,
                vol.Required("variable_id"): cv.string,
                vol.Optional("station_name"): cv.string,
                vol.Optional("station_id"): cv.string,
                vol.Optional("province_name"): cv.string,
                vol.Optional("province_id"): cv.string,
                vol.Optional("region_name"): cv.string,
                vol.Optional("region_id"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

def safe_remove(path: Path, is_folder: bool = False) -> None:
    """Elimina un archivo o carpeta vacía de forma segura."""
    try:
        if is_folder:
            if path.exists() and path.is_dir():
                path.rmdir()  # Solo elimina si está vacía
                _LOGGER.info("Carpeta eliminada: %s", path)
        else:
            if path.exists():
                path.unlink()
                _LOGGER.info("Archivo eliminado: %s", path)
    except Exception as e:
        _LOGGER.error("Error eliminando %s: %s", path, e)

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
        "variable_id", "station_name", "station_id", "province_name", 
        "province_id", "region_name", "region_id"
    ]
    missing_fields = [field for field in required_fields if field not in entry_data]
    if missing_fields:
        _LOGGER.error(f"Faltan los siguientes campos en la configuración: {missing_fields}")
        return False

    _LOGGER.debug(
        f"Datos de configuración: Municipio '{entry_data['town_name']}' (ID: {entry_data['town_id']}), "
        f"Variable '{entry_data['variable_name']}' (ID: {entry_data['variable_id']}), "
        f"Estación '{entry_data['station_name']}' (ID: {entry_data['station_id']}), "
        f"Provincia '{entry_data['province_name']}' (ID: {entry_data['province_id']}), "
        f"Comarca '{entry_data['region_name']}' (ID: {entry_data['region_id']})."
    )

    # Inicializar coordinadores
    try:
        sensor_coordinator = MeteocatSensorCoordinator(hass=hass, entry_data=entry_data)
        await sensor_coordinator.async_config_entry_first_refresh()
        
        static_sensor_coordinator = MeteocatStaticSensorCoordinator(hass=hass, entry_data=entry_data)
        # Corregido: refrescar el coordinador estático (antes se refrescaba el de sensor otra vez)
        await static_sensor_coordinator.async_config_entry_first_refresh()

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

        alerts_coordinator = MeteocatAlertsCoordinator(hass=hass, entry_data=entry_data)
        await alerts_coordinator.async_config_entry_first_refresh()

        alerts_region_coordinator = MeteocatAlertsRegionCoordinator(hass=hass, entry_data=entry_data)
        await alerts_region_coordinator.async_config_entry_first_refresh()

        quotes_coordinator = MeteocatQuotesCoordinator(hass=hass, entry_data=entry_data)
        await quotes_coordinator.async_config_entry_first_refresh()

        quotes_file_coordinator = MeteocatQuotesFileCoordinator(hass=hass, entry_data=entry_data)
        await quotes_file_coordinator.async_config_entry_first_refresh()

        lightning_coordinator = MeteocatLightningCoordinator(hass=hass, entry_data=entry_data)
        await lightning_coordinator.async_config_entry_first_refresh()

        lightning_file_coordinator = MeteocatLightningFileCoordinator(hass=hass, entry_data=entry_data)
        await lightning_file_coordinator.async_config_entry_first_refresh()

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
        "alerts_coordinator": alerts_coordinator,
        "alerts_region_coordinator": alerts_region_coordinator,
        "quotes_coordinator": quotes_coordinator,
        "quotes_file_coordinator": quotes_file_coordinator,
        "lightning_coordinator": lightning_coordinator,
        "lightning_file_coordinator": lightning_file_coordinator,
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

    # Rutas persistentes en /config/meteocat_files
    base_folder = get_storage_dir(hass)
    assets_folder = get_storage_dir(hass, "assets")
    files_folder = get_storage_dir(hass, "files")

    # Archivos comunes
    common_files = [
        assets_folder / "towns.json",
        assets_folder / "symbols.json",
        assets_folder / "variables.json",
        assets_folder / "stations.json",
        files_folder / "alerts.json",
        files_folder / "quotes.json",
    ]

    # Archivos específicos de la entrada
    station_id = entry.data.get("station_id")
    town_id = entry.data.get("town_id")
    region_id = entry.data.get("region_id")

    specific_files = []
    if station_id:
        specific_files.append(files_folder / f"station_{station_id.lower()}_data.json")
    if town_id:
        specific_files.extend([
            assets_folder / f"stations_{town_id.lower()}.json",
            files_folder / f"uvi_{town_id.lower()}_data.json",
            files_folder / f"forecast_{town_id.lower()}_hourly_data.json",
            files_folder / f"forecast_{town_id.lower()}_daily_data.json",
        ])
    if region_id:
        specific_files.extend([
            files_folder / f"alerts_{region_id}.json",
            files_folder / f"lightning_{region_id}.json",
        ])

    # Eliminar archivos específicos
    for f in specific_files:
        safe_remove(f)

    # Verificar si quedan otras entradas antes de eliminar archivos comunes
    remaining_entries = [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not remaining_entries:
        for f in common_files:
            safe_remove(f)

        # Intentar eliminar carpetas vacías
        for folder in [assets_folder, files_folder, base_folder]:
            safe_remove(folder, is_folder=True)