from __future__ import annotations

import logging
import voluptuous as vol
from pathlib import Path
import aiofiles
import json
import importlib  # Para importaciones lazy

from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import async_get_platforms
from homeassistant.helpers import config_validation as cv

from .helpers import get_storage_dir
from meteocatpy.town import MeteocatTown
from meteocatpy.symbols import MeteocatSymbols
from meteocatpy.variables import MeteocatVariables
from meteocatpy.townstations import MeteocatTownStations
from .const import DOMAIN, PLATFORMS, LIMIT_XDDE

_LOGGER = logging.getLogger(__name__)

# Versión
__version__ = "4.1.4"

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
                vol.Required("latitude"): cv.latitude,
                vol.Required("longitude"): cv.longitude,
                vol.Required("altitude"): vol.Coerce(float),
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

async def ensure_assets_exist(hass, api_key, town_id=None, variable_id=None):
    """Comprueba y crea los assets básicos si faltan."""
    assets_dir = get_storage_dir(hass, "assets")
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Lista de assets: (nombre_archivo, fetch_func, clave_json, args)
    assets = [
        ("towns.json", MeteocatTown(api_key).get_municipis, "towns", []),
        ("stations.json", MeteocatTownStations(api_key).stations_service.get_stations, "stations", []),
        ("variables.json", MeteocatVariables(api_key).get_variables, "variables", []),
        ("symbols.json", MeteocatSymbols(api_key).fetch_symbols, "symbols", []),
    ]

    # Si tenemos town_id y variable_id, agregamos stations_<town_id>.json
    if town_id and variable_id:
        assets.append(
            (f"stations_{town_id}.json", MeteocatTownStations(api_key).get_town_stations, "town_stations", [town_id, variable_id])
        )

    for filename, fetch_func, key, args in assets:
        file_path = assets_dir / filename
        if not file_path.exists():
            _LOGGER.debug("Intentando descargar datos para %s desde la API con args: %s", key, args)
            try:
                data = await fetch_func(*args)
            except Exception as ex:
                _LOGGER.warning(
                    "No se pudieron obtener los datos para %s. Intenta regenerarlo más adelante desde las opciones de la integración. Detalle: %s",
                    key,
                    ex,
                )
                data = []
            async with aiofiles.open(file_path, "w", encoding="utf-8") as file:
                await file.write(json.dumps({key: data}, ensure_ascii=False, indent=4))
            _LOGGER.info("Archivo creado: %s", file_path)

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Configuración inicial del componente Meteocat."""
    return True

def _get_coordinator_module(cls_name: str):
    """Importa dinámicamente un coordinador para evitar blocking imports."""
    module = importlib.import_module(".coordinator", "custom_components.meteocat")
    return getattr(module, cls_name)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura una entrada de configuración para Meteocat."""
    _LOGGER.info("Configurando la integración de Meteocat...")

    # Extraer los datos necesarios de la entrada de configuración
    entry_data = entry.data

    # Validar campos requeridos
    required_fields = [
        "api_key", "town_name", "town_id", "variable_name",
        "variable_id", "station_name", "station_id", "province_name",
        "province_id", "region_name", "region_id", "latitude", "longitude", "altitude"
    ]
    missing_fields = [field for field in required_fields if field not in entry_data]
    if missing_fields:
        _LOGGER.error(f"Faltan los siguientes campos en la configuración: {missing_fields}")
        return False

    # Validar coordenadas válidas para Cataluña
    latitude = entry_data.get("latitude")
    longitude = entry_data.get("longitude")
    if not (40.5 <= latitude <= 42.5 and 0.1 <= longitude <= 3.3):  # Rango aproximado para Cataluña
        _LOGGER.warning(
            "Coordenadas inválidas (latitude: %s, longitude: %s). Usando coordenadas de Barcelona por defecto para MeteocatSunCoordinator.",
            latitude, longitude
        )
        entry_data = {
            **entry_data,
            "latitude": 41.38879,
            "longitude": 2.15899
        }

    # Crear los assets básicos si faltan
    await ensure_assets_exist(
        hass,
        api_key=entry_data["api_key"],
        town_id=entry_data.get("town_id"),
        variable_id=entry_data.get("variable_id"),
    )

    _LOGGER.debug(
        f"Datos de configuración: Municipio '{entry_data['town_name']}' (ID: {entry_data['town_id']}), "
        f"Variable '{entry_data['variable_name']}' (ID: {entry_data['variable_id']}), "
        f"Estación '{entry_data['station_name']}' (ID: {entry_data['station_id']}), "
        f"Provincia '{entry_data['province_name']}' (ID: {entry_data['province_id']}), "
        f"Comarca '{entry_data['region_name']}' (ID: {entry_data['region_id']}), "
        f"Coordenadas: ({entry_data['latitude']}, {entry_data['longitude']})."
        f"Altitud: ({entry_data['altitude']})."
    )

    # Lista de coordinadores críticos (bloquean setup si fallan)
    CRITICAL_COORDINATORS = [
        ("sensor_coordinator", "MeteocatSensorCoordinator"),
        ("sensor_file_coordinator", "MeteocatSensorFileCoordinator"),
        ("static_sensor_coordinator", "MeteocatStaticSensorCoordinator"),
        ("entity_coordinator", "MeteocatEntityCoordinator"),
        ("hourly_forecast_coordinator", "HourlyForecastCoordinator"),
        ("daily_forecast_coordinator", "DailyForecastCoordinator"),
        ("condition_coordinator", "MeteocatConditionCoordinator"),
        ("temp_forecast_coordinator", "MeteocatTempForecastCoordinator"),
    ]

    # Lista de coordinadores opcionales (no bloquean setup, pero se intenta cargar)
    OPTIONAL_COORDINATORS = [
        ("uvi_coordinator", "MeteocatUviCoordinator"),
        ("uvi_file_coordinator", "MeteocatUviFileCoordinator"),
        ("alerts_coordinator", "MeteocatAlertsCoordinator"),
        ("alerts_region_coordinator", "MeteocatAlertsRegionCoordinator"),
        ("quotes_coordinator", "MeteocatQuotesCoordinator"),
        ("quotes_file_coordinator", "MeteocatQuotesFileCoordinator"),
        ("lightning_coordinator", "MeteocatLightningCoordinator"),
        ("lightning_file_coordinator", "MeteocatLightningFileCoordinator"),
        ("sun_coordinator", "MeteocatSunCoordinator"),
        ("sun_file_coordinator", "MeteocatSunFileCoordinator"),
        ("moon_coordinator", "MeteocatMoonCoordinator"),
        ("moon_file_coordinator", "MeteocatMoonFileCoordinator"),
    ]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["_health"] = {}

    def _normalize_error_reason(exc: Exception) -> str:
        """Normaliza el tipo de error a una causa legible."""
        err_str = str(exc).lower()
        if "quota" in err_str or "429" in err_str:
            return "quota_exceeded"
        if "timeout" in err_str or "timed out" in err_str:
            return "timeout"
        if "dns" in err_str or "cannot connect" in err_str:
            return "dns_error"
        if "forbidden" in err_str or "403" in err_str:
            return "forbidden"
        if "401" in err_str or "unauthorized" in err_str:
            return "unauthorized"
        return "unknown"

    async def _init_coordinator(key: str, cls_name: str, is_critical: bool = True):
        """Inicializa un coordinador con manejo de errores."""
        try:
            cls = await hass.async_add_executor_job(_get_coordinator_module, cls_name)
            coordinator = cls(hass=hass, entry_data=entry_data)
            await coordinator.async_config_entry_first_refresh()
            hass.data[DOMAIN][entry.entry_id][key] = coordinator
            hass.data[DOMAIN][entry.entry_id]["_health"][key] = {
                "status": "ok",
                "reason": "",
                "last_error": "",
            }
            _setup_recovery_listener(key, coordinator)
            return True
        except Exception as err:
            reason = _normalize_error_reason(err)
            if is_critical:
                return False

            cls = await hass.async_add_executor_job(_get_coordinator_module, cls_name)
            coordinator = cls(hass=hass, entry_data=entry_data)
            hass.data[DOMAIN][entry.entry_id][key] = coordinator
            hass.data[DOMAIN][entry.entry_id]["_health"][key] = {
                "status": "degraded",
                "reason": reason,
                "last_error": str(err)[:100],
            }
            _setup_recovery_listener(key, coordinator)
            _LOGGER.warning(
                "Coordinador opcional '%s' inicializado en modo degradado: causa=%s, detalle=%s",
                key, reason, str(err)[:150]
            )
            return None

    def _setup_recovery_listener(key: str, coordinator):
        """Configura callback para recovery automático cuando update succeed."""

        if hasattr(coordinator, f"_recovery_listener_{key}_registered"):
            return

        async def _on_update_async():
            """Lógica asíncrona de recuperación."""
            try:
                health = hass.data[DOMAIN][entry.entry_id]["_health"].get(key, {})
                if health.get("status") == "degraded":
                    data = coordinator.data
                    has_data = data and (
                        (isinstance(data, dict) and any(v for v in data.values() if v is not None))
                        or (isinstance(data, list) and len(data) > 0)
                    )
                    if has_data:
                        _LOGGER.info("Coordinador '%s' recuperado automáticamente", key)
                        hass.data[DOMAIN][entry.entry_id]["_health"][key] = {
                            "status": "ok",
                            "reason": "",
                            "last_error": "",
                        }
                    else:
                        _LOGGER.debug("Coordinador '%s' sigue sin datos, no recovery aún", key)
            except Exception as e:
                _LOGGER.debug("Error en recovery de %s: %s", key, e)

        def on_update():
            """Callback síncrono esperado por HA."""
            hass.async_create_task(_on_update_async())

        coordinator.async_add_listener(on_update)

        setattr(coordinator, f"_recovery_listener_{key}_registered", True)

    ok_count = 0
    degraded_count = 0
    disabled_count = 0
    LIGHTNING_KEYS = {"lightning_coordinator", "lightning_file_coordinator"}

    for key, cls_name in CRITICAL_COORDINATORS:
        result = await _init_coordinator(key, cls_name, is_critical=True)
        if result is False:
            _LOGGER.error("Coordinador crítico '%s' falló, abortando setup", key)
            return False
        if result:
            ok_count += 1

    for key, cls_name in OPTIONAL_COORDINATORS:
        if key in LIGHTNING_KEYS and entry_data.get(LIMIT_XDDE, 250) == 0:
            hass.data[DOMAIN][entry.entry_id]["_health"][key] = {
                "status": "disabled",
                "reason": "xdde_not_enabled",
                "last_error": "",
            }
            disabled_count += 1
            _LOGGER.debug("Coordinador '%s' omitido: plan XDDE no habilitado", key)
            continue
        result = await _init_coordinator(key, cls_name, is_critical=False)
        if result is None:
            degraded_count += 1

    health = hass.data[DOMAIN][entry.entry_id]["_health"]
    _LOGGER.info(
        "Meteocat cargado: %d/%d OK, %d degradados, %d deshabilitados. Detalles: %s",
        ok_count, len(CRITICAL_COORDINATORS) + len(OPTIONAL_COORDINATORS),
        degraded_count, disabled_count,
        {k: v["reason"] or "ok" for k, v in health.items() if v.get("status") != "ok"}
    )

    hass.data[DOMAIN][entry.entry_id].update(entry_data)

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

    # Archivos comunes (solo se eliminan si no queda ninguna entrada)
    common_files = [
        assets_folder / "towns.json",
        assets_folder / "symbols.json",
        assets_folder / "variables.json",
        assets_folder / "stations.json",
        files_folder / "alerts.json",
        files_folder / "quotes.json",
    ]

    # Identificadores de la entrada eliminada
    station_id = entry.data.get("station_id")
    town_id = entry.data.get("town_id")
    region_id = entry.data.get("region_id")

    specific_files = []

    # 1. Archivos de estación
    if station_id:
        other_entries_with_station = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.data.get("station_id") == station_id
        ]
        if not other_entries_with_station:
            specific_files.append(files_folder / f"station_{station_id.lower()}_data.json")

    # 2. Archivos de municipio
    if town_id:
        other_entries_with_town = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.data.get("town_id") == town_id
        ]
        if not other_entries_with_town:
            specific_files.extend([
                assets_folder / f"stations_{town_id.lower()}.json",
                files_folder / f"uvi_{town_id.lower()}_data.json",
                files_folder / f"forecast_{town_id.lower()}_hourly_data.json",
                files_folder / f"forecast_{town_id.lower()}_daily_data.json",
                files_folder / f"sun_{town_id.lower()}_data.json",
                files_folder / f"moon_{town_id.lower()}_data.json",
            ])

    # 3. Archivos de comarca (region_id)
    if region_id:
        other_entries_with_region = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.data.get("region_id") == region_id
        ]
        if not other_entries_with_region:
            specific_files.extend([
                files_folder / f"alerts_{region_id}.json",
                files_folder / f"lightning_{region_id}.json",
            ])

    # Eliminar archivos específicos (solo si ya no los necesita nadie más)
    for f in specific_files:
        safe_remove(f)

    # Comprobar si quedan entradas activas de la integración
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
