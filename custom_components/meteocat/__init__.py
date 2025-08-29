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

    # Definir las rutas base
    custom_components_path = Path(hass.config.path("custom_components")) / DOMAIN
    assets_folder = custom_components_path / "assets"
    files_folder = custom_components_path / "files"

    # Archivos comunes
    symbols_file = assets_folder / "symbols.json"
    variables_file = assets_folder / "variables.json"
    alerts_file = files_folder / "alerts.json"
    quotes_file = files_folder / "quotes.json"

    # Archivos específicos de cada entry
    station_id = entry.data.get("station_id")
    town_id = entry.data.get("town_id")
    region_id = entry.data.get("region_id")

    if not custom_components_path.exists():
        _LOGGER.warning(f"La ruta {custom_components_path} no existe. No se realizará la limpieza.")
        return

    # Eliminar archivos específicos de la entrada
    if station_id:
        safe_remove(files_folder / f"station_{station_id.lower()}_data.json")
    if town_id:
        safe_remove(files_folder / f"uvi_{town_id.lower()}_data.json")
        safe_remove(files_folder / f"forecast_{town_id.lower()}_hourly_data.json")
        safe_remove(files_folder / f"forecast_{town_id.lower()}_daily_data.json")
    if region_id:
        safe_remove(files_folder / f"alerts_{region_id}.json")
        safe_remove(files_folder / f"lightning_{region_id}.json")

    # Siempre eliminables
    safe_remove(symbols_file)
    safe_remove(variables_file)

    # 🔑 Solo eliminar los archivos comunes si ya no quedan otras entradas
    remaining_entries = [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not remaining_entries:  # significa que estamos borrando la última
        safe_remove(alerts_file)
        safe_remove(quotes_file)
        safe_remove(assets_folder, is_folder=True)
        safe_remove(files_folder, is_folder=True)
