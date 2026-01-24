from __future__ import annotations

import json
import aiofiles
import logging
import asyncio
import random
import unicodedata
from pathlib import Path
from datetime import date, datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

from homeassistant.core import HomeAssistant, EVENT_HOMEASSISTANT_START
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.weather import Forecast

from solarmoonpy.moon import (
    moon_phase,
    moon_day,
    moon_rise_set,
    illuminated_percentage,
    moon_distance,
    moon_angular_diameter,
    lunation_number,
    get_moon_phase_name,
    get_lunation_duration
)
from solarmoonpy.location import Location, LocationInfo

from meteocatpy.data import MeteocatStationData
from meteocatpy.uvi import MeteocatUviData
from meteocatpy.forecast import MeteocatForecast
from meteocatpy.alerts import MeteocatAlerts
from meteocatpy.quotes import MeteocatQuotes
from meteocatpy.lightning import MeteocatLightning

from meteocatpy.exceptions import (
    BadRequestError,
    ForbiddenError,
    TooManyRequestsError,
    InternalServerError,
    UnknownAPIError,
)

from .helpers import get_storage_dir
from .condition import get_condition_from_statcel
from .const import (
    DOMAIN,
    CONDITION_MAPPING,
    DEFAULT_VALIDITY_DAYS,
    DEFAULT_VALIDITY_HOURS,
    DEFAULT_VALIDITY_MINUTES,
    DEFAULT_UVI_LOW_VALIDITY_HOURS,
    DEFAULT_UVI_LOW_VALIDITY_MINUTES,
    DEFAULT_UVI_HIGH_VALIDITY_HOURS,
    DEFAULT_UVI_HIGH_VALIDITY_MINUTES,
    DEFAULT_UVI_MIN_HOURS_SINCE_LAST_UPDATE,
    DEFAULT_ALERT_VALIDITY_TIME,
    DEFAULT_QUOTES_VALIDITY_TIME,
    ALERT_VALIDITY_MULTIPLIER_100,
    ALERT_VALIDITY_MULTIPLIER_200,
    ALERT_VALIDITY_MULTIPLIER_500,
    ALERT_VALIDITY_MULTIPLIER_DEFAULT,
    DEFAULT_LIGHTNING_VALIDITY_TIME,
    DEFAULT_LIGHTNING_VALIDITY_HOURS,
    DEFAULT_LIGHTNING_VALIDITY_MINUTES,
    PREDICCIO_HIGH_QUOTA_LIMIT
)

_LOGGER = logging.getLogger(__name__)

# Valores predeterminados para los intervalos de actualización
DEFAULT_SENSOR_UPDATE_INTERVAL = timedelta(minutes=90)
DEFAULT_STATIC_SENSOR_UPDATE_INTERVAL = timedelta(hours=24)
DEFAULT_ENTITY_UPDATE_INTERVAL = timedelta(minutes=60)
DEFAULT_HOURLY_FORECAST_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_DAILY_FORECAST_UPDATE_INTERVAL = timedelta(minutes=15)
DEFAULT_UVI_UPDATE_INTERVAL = timedelta(minutes=60)
DEFAULT_UVI_SENSOR_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_CONDITION_SENSOR_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_TEMP_FORECAST_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_ALERTS_UPDATE_INTERVAL = timedelta(minutes=10)
DEFAULT_ALERTS_REGION_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_QUOTES_UPDATE_INTERVAL = timedelta(minutes=10)
DEFAULT_QUOTES_FILE_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_LIGHTNING_UPDATE_INTERVAL = timedelta(minutes=10)
DEFAULT_LIGHTNING_FILE_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_SUN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_SUN_FILE_UPDATE_INTERVAL = timedelta(seconds=30)
DEFAULT_MOON_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_MOON_FILE_UPDATE_INTERVAL = timedelta(seconds=30)

# Definir la zona horaria local
TIMEZONE = ZoneInfo("Europe/Madrid")

async def save_json_to_file(data: dict, output_file: Path) -> None:
    """Guarda datos JSON en un archivo de forma asíncrona."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(output_file, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        raise RuntimeError(f"Error guardando JSON en {output_file}: {e}")

async def load_json_from_file(input_file: Path) -> dict:
    """Carga un archivo JSON de forma asincrónica."""
    try:
        async with aiofiles.open(input_file, "r", encoding="utf-8") as f:
            data = await f.read()
            return json.loads(data)
    except FileNotFoundError:
        _LOGGER.warning("El archivo %s no existe.", input_file)
        return {}
    except json.JSONDecodeError as err:
        _LOGGER.error("Error al decodificar JSON del archivo %s: %s", input_file, err)
        return {}

def normalize_name(name: str) -> str:
    """Normaliza el nombre eliminando acentos y convirtiendo a minúsculas."""
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    return name.lower()

# Definir _quotes_lock para evitar que varios coordinadores modifiquen quotes.json al mismo tiempo
_quotes_lock = asyncio.Lock()

async def _update_quotes(hass: HomeAssistant, plan_name: str) -> None:
    """Actualiza las cuotas en quotes.json después de una consulta."""
    async with _quotes_lock:
        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        quotes_file = files_folder / "quotes.json"

        try:
            data = await load_json_from_file(quotes_file)

            if not data or not isinstance(data, dict):
                _LOGGER.warning("quotes.json está vacío o tiene un formato inválido: %s", data)
                return
            if "plans" not in data or not isinstance(data["plans"], list):
                _LOGGER.warning("Estructura inesperada en quotes.json: %s", data)
                return

            for plan in data["plans"]:
                if plan.get("nom") == plan_name:
                    plan["consultesRealitzades"] += 1
                    plan["consultesRestants"] = max(0, plan["consultesRestants"] - 1)
                    _LOGGER.debug(
                        "Cuota actualizada para el plan %s: Consultas realizadas %s, restantes %s",
                        plan_name, plan["consultesRealitzades"], plan["consultesRestants"]
                    )
                    break
            
            await save_json_to_file(data, quotes_file)

        except FileNotFoundError:
            _LOGGER.error("El archivo quotes.json no fue encontrado en la ruta esperada: %s", quotes_file)
        except json.JSONDecodeError:
            _LOGGER.error("Error al decodificar quotes.json, posiblemente el archivo está corrupto.")
        except Exception as e:
            _LOGGER.exception("Error inesperado al actualizar las cuotas en quotes.json: %s", str(e))

class BaseFileCoordinator(DataUpdateCoordinator):
    """
    Coordinador base para leer datos desde archivos JSON.

    Proporciona un pequeño desfase aleatorio antes de cada actualización
    para evitar colisión entre el coordinador que crea el JSON y el que lo lee.

    Cada coordinador que herede de esta clase debe implementar su propio
    método `_async_update_data()` para definir la lógica de lectura y validación. 
    """

    def __init__(self, hass, name: str, update_interval: timedelta, min_delay: float = 1.0, max_delay: float = 2.0):
        """
        Inicializa el coordinador base.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            name (str): Nombre identificativo del coordinador.
            update_interval (timedelta): Intervalo de actualización.
            min_delay (float): Límite inferior del desfase aleatorio en segundos (default: 1.0).
            max_delay (float): Límite superior del desfase aleatorio en segundos (default: 2.0).
        """
        super().__init__(hass, _LOGGER, name=name, update_interval=update_interval)
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._first_delay = random.uniform(min_delay, max_delay)
        self._initialized = False

    async def _apply_random_delay(self):
        """
        Aplica un desfase aleatorio leve antes de la lectura.

        - En la primera ejecución: usa un desfase fijo (_first_delay)
        - En las siguientes: aplica un desfase aleatorio entre 1 y 2 segundos
        """
        if not self._initialized:
            delay = self._first_delay
            self._initialized = True
        else:
            delay = random.uniform(self._min_delay, self._max_delay)

        _LOGGER.debug("%s aplicando desfase aleatorio de %.2fs", self.name, delay)
        await asyncio.sleep(delay)

class MeteocatSensorCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de los sensores."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador de sensores de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
        """
        self.api_key = entry_data["api_key"]
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.variable_name = entry_data["variable_name"]
        self.variable_id = entry_data["variable_id"]
        self.meteocat_station_data = MeteocatStationData(self.api_key)

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.station_file = files_folder / f"station_{self.station_id.lower()}_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Sensor Coordinator",
            update_interval=DEFAULT_SENSOR_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de los sensores desde la API de Meteocat."""
        try:
            data = await asyncio.wait_for(
                self.meteocat_station_data.get_station_data(self.station_id),
                timeout=30
            )
            _LOGGER.debug("Datos de sensores actualizados exitosamente: %s", data)

            # Actualizar las cuotas
            await _update_quotes(self.hass, "XEMA")

            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                _LOGGER.error(
                    "Formato inválido: Se esperaba una lista de dicts, pero se obtuvo %s. Datos: %s",
                    type(data).__name__,
                    data,
                )
                raise ValueError("Formato de datos inválido")

            # Guardar datos en JSON persistente
            await save_json_to_file(data, self.station_file)

            return data

        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener datos de la API de Meteocat.")
            raise ConfigEntryNotReady from err
        except ForbiddenError as err:
            _LOGGER.error(
                "Acceso denegado al obtener datos de sensores (Station ID: %s): %s",
                self.station_id,
                err,
            )
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning(
                "Límite de solicitudes alcanzado al obtener datos de sensores (Station ID: %s): %s",
                self.station_id,
                err,
            )
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error(
                "Error al obtener datos de sensores (Station ID: %s): %s",
                self.station_id,
                err,
            )
            raise
        except Exception as err:
            if isinstance(err, ConfigEntryNotReady):
                _LOGGER.exception("No se pudo inicializar el dispositivo (Station ID: %s): %s", self.station_id, err)
                raise
            else:
                _LOGGER.exception("Error inesperado al obtener datos de sensores (Station ID: %s): %s", self.station_id, err)
           
        # === FALLBACK SEGURO ===
        cached_data = await load_json_from_file(self.station_file)
        if cached_data and isinstance(cached_data, list) and cached_data:
            # Buscar la última lectura (cualquier variable)
            last_reading = None
            last_time_str = "unknown"
            for var_block in cached_data:
                for variable in var_block.get("variables", []):
                    lectures = variable.get("lectures", [])
                    if lectures:
                        candidate = lectures[-1].get("data")
                        if candidate and (last_reading is None or candidate > last_time_str):
                            last_reading = candidate
                            last_time_str = candidate
            
            # Formatear hora legible
            try:
                if last_time_str != "unknown":
                    dt = datetime.fromisoformat(last_time_str.replace("Z", "+00:00"))
                    local_dt = dt.astimezone(TIMEZONE)
                    display_time = local_dt.strftime("%d/%m/%Y %H:%M")
                else:
                    display_time = "unknown"
            except (ValueError, TypeError, AttributeError):
                display_time = last_time_str.split("T")[0] if "T" in last_time_str else last_time_str
            
            _LOGGER.warning(
                "SENSOR: API falló → usando caché local:\n"
                "   • Estación: %s (%s)\n"
                "   • Archivo: %s\n"
                "   • Última lectura: %s",
                self.station_name,
                self.station_id,
                self.station_file.name,
                display_time
            )
            
            self.async_set_updated_data(cached_data)
            return cached_data
        
        _LOGGER.error("SENSOR: No hay caché disponible para los datos de la estación %s.", self.station_id)
        self.async_set_updated_data([])
        return []

class MeteocatStaticSensorCoordinator(DataUpdateCoordinator):
    """Coordinator to manage and update static sensor data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.region_name = entry_data["region_name"]
        self.region_id = entry_data["region_id"]

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Static Sensor Coordinator",
            update_interval=DEFAULT_STATIC_SENSOR_UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        """Retorna los datos estáticos (no necesita archivos)."""
        _LOGGER.debug(
            "Updating static sensor data: town %s (ID %s), station %s (ID %s), region %s (ID %s)",
            self.town_name,
            self.town_id,
            self.station_name,
            self.station_id,
            self.region_name,
            self.region_id,
        )
        return {
            "town_name": self.town_name,
            "town_id": self.town_id,
            "station_name": self.station_name,
            "station_id": self.station_id,
            "region_name": self.region_name,
            "region_id": self.region_id,
        }

class MeteocatUviCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de UVI desde la API de Meteocat."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        self.api_key = entry_data["api_key"]
        self.town_id = entry_data["town_id"]
        self.limit_prediccio = entry_data["limit_prediccio"]
        self.meteocat_uvi_data = MeteocatUviData(self.api_key)

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.uvi_file = files_folder / f"uvi_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Uvi Coordinator",
            update_interval=DEFAULT_UVI_UPDATE_INTERVAL,
        )

    async def is_uvi_data_valid(self) -> Optional[dict]:
        """Valida si los datos UVI en caché son aún válidos, considerando:
           1. Antigüedad de la fecha del primer día (lógica existente según cuota)
           2. Hora mínima del día (según cuota)
           3. Han pasado más de DEFAULT_UVI_MIN_HOURS_SINCE_LAST_UPDATE horas desde la última actualización exitosa
        """
        if not self.uvi_file.exists():
            _LOGGER.debug("Archivo UVI no existe: %s", self.uvi_file)
            return None

        try:
            data = await load_json_from_file(self.uvi_file)

            # Validar estructura básica
            if not isinstance(data, dict) or "uvi" not in data or not isinstance(data["uvi"], list) or not data["uvi"]:
                _LOGGER.warning("Estructura UVI inválida en %s", self.uvi_file)
                return None

            # ── Condición 1: Antigüedad de la fecha del primer día ──
            try:
                first_date_str = data["uvi"][0].get("date")
                first_date = datetime.strptime(first_date_str, "%Y-%m-%d").date()
            except Exception as exc:
                _LOGGER.warning("Fecha UVI inválida en %s: %s", self.uvi_file, exc)
                return None

            now_local = datetime.now(TIMEZONE)
            today = now_local.date()
            current_time_local = now_local.time()
            days_diff = (today - first_date).days

            # Determinar umbrales según cuota
            if self.limit_prediccio >= PREDICCIO_HIGH_QUOTA_LIMIT:
                min_days = DEFAULT_VALIDITY_DAYS           # ej: 1 día
                min_update_time = time(DEFAULT_UVI_HIGH_VALIDITY_HOURS, DEFAULT_UVI_HIGH_VALIDITY_MINUTES)
                quota_level = "ALTA"
            else:
                min_days = DEFAULT_VALIDITY_DAYS + 1       # ej: 2 días
                min_update_time = time(DEFAULT_UVI_LOW_VALIDITY_HOURS, DEFAULT_UVI_LOW_VALIDITY_MINUTES)
                quota_level = "BAJA"

            cond1 = days_diff >= min_days
            cond2 = current_time_local >= min_update_time

            # ── Condición 3: Más de X horas desde última actualización ──
            cond3 = True  # por defecto (si no hay dataUpdate → permite actualizar)
            last_update_str = None
            if "actualitzat" in data and "dataUpdate" in data["actualitzat"]:
                try:
                    last_update = datetime.fromisoformat(data["actualitzat"]["dataUpdate"])
                    time_since = now_local - last_update
                    cond3 = time_since > timedelta(hours=DEFAULT_UVI_MIN_HOURS_SINCE_LAST_UPDATE)
                    last_update_str = last_update.strftime("%Y-%m-%d %H:%M:%S %z")
                    _LOGGER.debug(
                        "Tiempo desde última actualización: %s (%s %dh)",
                        time_since,
                        "supera" if cond3 else "NO supera",
                        DEFAULT_UVI_MIN_HOURS_SINCE_LAST_UPDATE
                    )
                except ValueError:
                    _LOGGER.warning("Formato inválido en dataUpdate: %s", data["actualitzat"]["dataUpdate"])
                    cond3 = True  # si corrupto → permite actualizar

            should_update = cond1 and cond2 and cond3

            _LOGGER.debug(
                "[UVI %s] Validación → cond1(días >=%d)=%s | cond2(hora >=%s)=%s | "
                "cond3(>%dh desde %s)=%s | cuota=%d (%s) | actualizar=%s",
                self.town_id,
                min_days,
                cond1,
                min_update_time.strftime("%H:%M"),
                cond2,
                DEFAULT_UVI_MIN_HOURS_SINCE_LAST_UPDATE,
                last_update_str or "nunca",
                cond3,
                self.limit_prediccio,
                quota_level,
                should_update,
            )

            if should_update:
                _LOGGER.info(
                    "Datos UVI obsoletos o antiguos → llamando API (town=%s, cuota=%d)",
                    self.town_id, self.limit_prediccio
                )
                return None

            _LOGGER.debug("Datos UVI válidos → usando caché")
            return data

        except json.JSONDecodeError:
            _LOGGER.error("JSON corrupto en %s", self.uvi_file)
            return None
        except Exception as e:
            _LOGGER.error("Error validando UVI: %s", e)
            return None

    async def _async_update_data(self) -> Optional[dict]:
        """Actualiza los datos de UVI desde la API o caché."""
        try:
            valid_data = await self.is_uvi_data_valid()
            if valid_data:
                _LOGGER.debug("Los datos del índice UV están actualizados. No se realiza llamada a la API.")
                return valid_data

            # ── Llamada a la API ──
            data = await asyncio.wait_for(
                self.meteocat_uvi_data.get_uvi_index(self.town_id),
                timeout=30,
            )
            _LOGGER.debug("Datos UVI obtenidos desde API: %s", data)

            await _update_quotes(self.hass, "Prediccio")

            if not isinstance(data, dict) or "uvi" not in data or not isinstance(data["uvi"], list):
                _LOGGER.error("Formato inválido: se esperaba un dict con 'uvi' -> %s", data)
                raise ValueError("Formato de datos inválido")

            # Añadir timestamp de actualización exitosa
            now_iso = datetime.now(TIMEZONE).isoformat()
            enhanced_data = {
                "actualitzat": {
                    "dataUpdate": now_iso
                },
                **data  # conserva ine, nom, comarca, capital, uvi, ...
            }

            await save_json_to_file(enhanced_data, self.uvi_file)
            _LOGGER.debug("Datos UVI guardados con dataUpdate: %s", now_iso)

            return enhanced_data   # ← en lugar de return data["uvi"]

        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener datos UVI.")
            raise ConfigEntryNotReady from err
        except ForbiddenError as err:
            _LOGGER.error("Acceso denegado al obtener datos UVI para town %s: %s", self.town_id, err)
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning("Límite de solicitudes alcanzado al obtener datos UVI para town %s: %s", self.town_id, err)
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error("Error API al obtener datos UVI para town %s: %s", self.town_id, err)
            raise
        except Exception as err:
            _LOGGER.exception("Error inesperado al obtener datos del índice UV para %s: %s", self.town_id, err)

        # ── FALLBACK SEGURO ──
        cached_data = await load_json_from_file(self.uvi_file)
        if cached_data and "uvi" in cached_data and cached_data["uvi"]:
            raw_date = cached_data["uvi"][0].get("date", "unknown")
            try:
                first_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                first_date = raw_date

            _LOGGER.warning(
                "API UVI falló → usando caché local:\n"
                " • Archivo: %s\n"
                " • Datos desde: %s",
                self.uvi_file.name,
                first_date
            )

            self.async_set_updated_data(cached_data)
            return cached_data

        _LOGGER.error("No hay datos UVI ni en caché para %s", self.town_id)
        self.async_set_updated_data(None)
        return None

class MeteocatUviFileCoordinator(BaseFileCoordinator):
    """Coordinator to read and process UV data from a file."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        self.town_id = entry_data["town_id"]

        super().__init__(
            hass,
            name=f"{DOMAIN} Uvi File Coordinator",
            update_interval=DEFAULT_UVI_SENSOR_UPDATE_INTERVAL,
            min_delay=1.0,  # Rango predeterminado
            max_delay=2.0,  # Rango predeterminado
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self._file_path = files_folder / f"uvi_{self.town_id.lower()}_data.json"

    async def _async_update_data(self):
        """Read and process UV data for the current hour from the file asynchronously."""
        # 🔸 Añadimos un pequeño desfase aleatorio (1 a 2 segundos) basados en el BaseFileCoordinator
        await self._apply_random_delay()

        try:
            async with aiofiles.open(self._file_path, "r", encoding="utf-8") as file:
                raw = await file.read()
                raw_data = json.loads(raw)
        except FileNotFoundError:
            _LOGGER.error("No se ha encontrado el archivo JSON con datos del índice UV en %s.", self._file_path)
            return {}
        except json.JSONDecodeError:
            _LOGGER.error("Error al decodificar el archivo JSON del índice UV en %s.", self._file_path)
            return {}

        return self._get_uv_for_current_hour(raw_data)

    def _get_uv_for_current_hour(self, raw_data):
        """Get UV data for the current hour."""
        # Fecha y hora actual
        current_datetime = datetime.now()
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_hour = current_datetime.hour

        # Busca los datos para la fecha actual
        for day_data in raw_data.get("uvi", []):
            if day_data.get("date") == current_date:
                # Encuentra los datos de la hora actual
                for hour_data in day_data.get("hours", []):
                    if hour_data.get("hour") == current_hour:
                        return {
                            "hour": hour_data.get("hour", 0),
                            "uvi": hour_data.get("uvi", 0),
                            "uvi_clouds": hour_data.get("uvi_clouds", 0),
                        }

        # Si no se encuentran datos, devuelve un diccionario vacío con valores predeterminados
        _LOGGER.warning(
            "No se encontraron datos del índice UV para hoy (%s) y la hora actual (%s).",
            current_date,
            current_hour,
        )
        return {"hour": 0, "uvi": 0, "uvi_clouds": 0}

class MeteocatEntityCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de las entidades de predicción."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador de datos para entidades de predicción.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
        """
        self.api_key = entry_data["api_key"]
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.variable_name = entry_data["variable_name"]
        self.variable_id = entry_data["variable_id"]
        self.limit_prediccio = entry_data["limit_prediccio"]  # Límite de llamada a la API para PREDICCIONES
        self.meteocat_forecast = MeteocatForecast(self.api_key)

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.hourly_file = files_folder / f"forecast_{self.town_id}_hourly_data.json"
        self.daily_file = files_folder / f"forecast_{self.town_id}_daily_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Entity Coordinator",
            update_interval=DEFAULT_ENTITY_UPDATE_INTERVAL,
        )
    
    # --------------------------------------------------------------------- #
    #  VALIDACIÓN DINÁMICA DE DATOS DE PREDICCIÓN
    # --------------------------------------------------------------------- #
    async def validate_forecast_data(self, file_path: Path) -> dict:
        """Valida y retorna datos de predicción si son válidos.
        
        - Si `limit_prediccio >= 550` → actualiza **el día siguiente** después de las DEFAULT_VALIDITY_HOURS:DEFAULT_VALIDITY_MINUTES.
        - Si `limit_prediccio < 550`  → actualiza **dos días después** después de las DEFAULT_VALIDITY_HOURS:DEFAULT_VALIDITY_MINUTES.
        """
        if not file_path.exists():
            _LOGGER.warning("El archivo %s no existe. Se considerará inválido.", file_path)
            return None
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            # Fecha del primer día de predicción (solo fecha)
            first_date_str = data["dies"][0]["data"].rstrip("Z")
            first_date = datetime.fromisoformat(first_date_str).date()
            today = datetime.now(timezone.utc).date()

            # Hora actual en zona local (Europe/Madrid)
            current_time_local = datetime.now(TIMEZONE).time()
            min_update_time = time(DEFAULT_VALIDITY_HOURS, DEFAULT_VALIDITY_MINUTES)

            days_diff = (today - first_date).days

            # -----------------------------------------------------------------
            #  Lógica según cuota
            # -----------------------------------------------------------------
            if self.limit_prediccio >= PREDICCIO_HIGH_QUOTA_LIMIT:
                # Cuota alta → actualiza cuando los datos son de ayer (o antes) + hora OK
                should_update = days_diff >= DEFAULT_VALIDITY_DAYS and current_time_local >= min_update_time
            else:
                # Cuota baja → actualiza solo cuando los datos son de anteayer + hora OK
                should_update = days_diff > DEFAULT_VALIDITY_DAYS and current_time_local >= min_update_time

            # -----------------------------------------------------------------
            #  Logs detallados
            # -----------------------------------------------------------------
            _LOGGER.debug(
                "[%s] Validación: primer_día=%s, hoy=%s → días=%d, "
                "cuota=%d (%s), hora_local=%s ≥ %s → actualizar=%s",
                file_path.name,
                first_date,
                today,
                days_diff,
                self.limit_prediccio,
                "ALTA" if self.limit_prediccio >= 550 else "BAJA",
                current_time_local.strftime("%H:%M"),
                min_update_time.strftime("%H:%M"),
                should_update,
            )

            if should_update:
                _LOGGER.debug(
                    "Datos obsoletos o actualizables → llamando API (%s, cuota=%d)",
                    file_path.name, self.limit_prediccio
                )
                return None  # → forzar actualización

            _LOGGER.debug("Datos válidos en %s → usando caché", file_path.name)
            return data

        except Exception as e:
            _LOGGER.warning("Error validando %s: %s", file_path, e)
            return None

    # --------------------------------------------------------------------- #
    #  OBTENCIÓN Y GUARDADO DE DATOS DESDE LA API
    # --------------------------------------------------------------------- #
    async def _fetch_and_save_data(self, api_method, file_path: Path) -> dict:
        """Obtiene datos de la API y los guarda en un archivo JSON."""
        try:
            data = await asyncio.wait_for(api_method(self.town_id), timeout=30)

            # Procesar precipitación negativa antes de guardar los datos
            for day in data.get("dies", []):
                for var, details in day.get("variables", {}).items():
                    if (
                        var == "precipitacio"
                        and isinstance(details.get("valor"), str)
                        and details["valor"].startswith("-")
                    ):
                        details["valor"] = "0.0"

            await save_json_to_file(data, file_path)

            # Actualizar cuotas (dependiendo del tipo de predicción horaria/diaria)
            if api_method.__name__ in ("get_prediccion_horaria", "get_prediccion_diaria"):
                await _update_quotes(self.hass, "Prediccio")

            return data

        except Exception as err:
            _LOGGER.error(f"Error al obtener datos de la API para {file_path}: {err}")
            raise

    # --------------------------------------------------------------------- #
    #  ACTUALIZACIÓN PRINCIPAL
    # --------------------------------------------------------------------- #
    async def _async_update_data(self) -> Dict[str, Any]:
        """Actualiza los datos de predicción horaria y diaria."""
        try:
            # ---  Validar o actualizar datos horarios ---
            hourly_data = await self.validate_forecast_data(self.hourly_file)
            if not hourly_data:
                hourly_data = await self._fetch_and_save_data(
                    self.meteocat_forecast.get_prediccion_horaria, self.hourly_file
                )

            # ---  Validar o actualizar datos diarios ---
            daily_data = await self.validate_forecast_data(self.daily_file)
            if not daily_data:
                daily_data = await self._fetch_and_save_data(
                    self.meteocat_forecast.get_prediccion_diaria, self.daily_file
                )

            return {"hourly": hourly_data, "daily": daily_data}

        # -----------------------------------------------------------------
        #  Manejo de errores de API
        # -----------------------------------------------------------------
        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener datos de predicción.")
            raise ConfigEntryNotReady from err
        except ForbiddenError as err:
            _LOGGER.error(
                "Acceso denegado al obtener datos de predicción (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning(
                "Límite de solicitudes alcanzado al obtener datos de predicción (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error(
                "Error al obtener datos de predicción (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise
        except Exception as err:
            _LOGGER.exception("Error inesperado al obtener datos de predicción: %s", err)
           
        # === FALLBACK SEGURO ===
        hourly_cache = await load_json_from_file(self.hourly_file) or {}
        daily_cache = await load_json_from_file(self.daily_file) or {}
        
        # --- Fecha horaria ---
        h_raw = hourly_cache.get("dies", [{}])[0].get("data", "")
        try:
            h_date = h_raw.replace("Z", "").split("T")[0]
            h_display = datetime.strptime(h_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, AttributeError, IndexError):
            h_display = "unknown"
        
        # --- Fecha diaria ---
        d_raw = daily_cache.get("dies", [{}])[0].get("data", "")
        try:
            d_date = d_raw.replace("Z", "").split("T")[0]
            d_display = datetime.strptime(d_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, AttributeError, IndexError):
            d_display = "unknown"
        
        _LOGGER.warning(
            "API falló → usando caché local:\n"
            "   • %s → %s\n"
            "   • %s → %s",
            self.hourly_file.name, h_display,
            self.daily_file.name, d_display
        )
        
        self.async_set_updated_data({"hourly": hourly_cache, "daily": daily_cache})
        return {"hourly": hourly_cache, "daily": daily_cache}

def get_condition_from_code(code: int) -> str:
    """Devuelve la condición meteorológica basada en el código."""
    return next((key for key, codes in CONDITION_MAPPING.items() if code in codes), "unknown")

class HourlyForecastCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar las predicciones horarias desde archivos locales."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """Inicializa el coordinador para predicciones horarias."""
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]

        # === NUEVO: ubicación solar usando solarmoonpy ===
        latitude = entry_data.get("latitude", hass.config.latitude)
        longitude = entry_data.get("longitude", hass.config.longitude)
        altitude = entry_data.get("altitude", hass.config.elevation or 0.0)
        timezone_str = hass.config.time_zone or "Europe/Madrid"

        self.location = Location(
            LocationInfo(
                name=self.town_name,
                region="Spain",
                timezone=timezone_str,
                latitude=latitude,
                longitude=longitude,
                elevation=altitude,
            )
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.file_path = files_folder / f"forecast_{self.town_id.lower()}_hourly_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Hourly Forecast Coordinator",
            update_interval=DEFAULT_HOURLY_FORECAST_UPDATE_INTERVAL,
        )

    def _convert_to_local_time(self, forecast_time: datetime) -> datetime:
        """Convierte una hora UTC a la hora local en la zona horaria de Madrid, considerando el horario de verano."""
        # Convertir la hora UTC a la hora local usando la zona horaria de Madrid
        local_time = forecast_time.astimezone(TIMEZONE)
        return local_time

    async def _is_data_valid(self) -> bool:
        """Verifica si los datos horarios en el archivo JSON son válidos y actuales."""
        if not self.file_path.exists():
            return False

        try:
            async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            if not data or "dies" not in data:
                return False

            now = datetime.now(TIMEZONE)
            for dia in data["dies"]:
                for forecast in dia.get("variables", {}).get("estatCel", {}).get("valors", []):
                    forecast_time = datetime.fromisoformat(forecast["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
                    # Convertir la hora de la predicción a la hora local
                    forecast_time_local = self._convert_to_local_time(forecast_time)
                    if forecast_time_local >= now:
                        return True

            return False
        except Exception as e:
            _LOGGER.warning("Error validando datos horarios en %s: %s", self.file_path, e)
            return False

    async def _async_update_data(self) -> dict:
        """Lee los datos horarios desde el archivo local."""
        if await self._is_data_valid():
            try:
                async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content)
            except Exception as e:
                _LOGGER.warning("Error leyendo archivo de predicción horaria en %s: %s", self.file_path, e)

        return {}

    def parse_hourly_forecast(self, dia: dict, forecast_time_local: datetime) -> dict:
        """Convierte una hora de predicción en un diccionario con los datos necesarios."""
        variables = dia.get("variables", {})

        # Buscar el código de condición correspondiente al tiempo objetivo (en hora local)
        condition_code = next(
            (item["valor"] for item in variables.get("estatCel", {}).get("valors", []) if
            self._convert_to_local_time(
                datetime.fromisoformat(item["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
            ) == forecast_time_local),
            -1,
        )

        # Determinar la condición usando `get_condition_from_statcel`
        condition_data = get_condition_from_statcel(
            codi_estatcel=condition_code,
            current_time=forecast_time_local,
            location=self.location,
            is_hourly=True
        )
        condition = condition_data["condition"]

        return {
            "datetime": forecast_time_local.isoformat(),
            "temperature": self._get_variable_value(dia, "temp", forecast_time_local),
            "precipitation": self._get_variable_value(dia, "precipitacio", forecast_time_local),
            "condition": condition,
            "wind_speed": self._get_variable_value(dia, "velVent", forecast_time_local),
            "wind_bearing": self._get_variable_value(dia, "dirVent", forecast_time_local),
            "humidity": self._get_variable_value(dia, "humitat", forecast_time_local),
        }

    def get_all_hourly_forecasts(self) -> list[dict]:
        """Obtiene una lista de predicciones horarias procesadas."""
        if not self.data or "dies" not in self.data:
            return []

        forecasts = []
        now = datetime.now(TIMEZONE)
        for dia in self.data["dies"]:
            for forecast in dia.get("variables", {}).get("estatCel", {}).get("valors", []):
                forecast_time = datetime.fromisoformat(forecast["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
                # Convertir la hora de la predicción a la hora local
                forecast_time_local = self._convert_to_local_time(forecast_time)
                if forecast_time_local >= now:
                    forecasts.append(self.parse_hourly_forecast(dia, forecast_time_local))
        return forecasts

    def _get_variable_value(self, dia, variable_name, target_time):
        """Devuelve el valor de una variable específica para una hora determinada."""
        variable = dia.get("variables", {}).get(variable_name, {})
        if not variable:
            _LOGGER.warning("Variable '%s' no encontrada en los datos.", variable_name)
            return None

        # Obtener lista de valores, soportando tanto 'valors' como 'valor'
        valores = variable.get("valors") or variable.get("valor")
        if not valores:
            _LOGGER.warning("No se encontraron valores para la variable '%s'.", variable_name)
            return None

        for valor in valores:
            try:
                # Convertir tiempo del JSON a hora local
                data_hora = datetime.fromisoformat(valor["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
                data_hora_local = self._convert_to_local_time(data_hora)

                # Comparar con tiempo objetivo en hora local
                if data_hora_local == target_time:
                    return float(valor["valor"])
            except (KeyError, ValueError) as e:
                _LOGGER.warning("Error procesando '%s' para %s: %s", variable_name, valor, e)
                continue

        _LOGGER.warning("No se encontró un valor válido para '%s' en %s.", variable_name, target_time)
        return None
    
class DailyForecastCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar las predicciones diarias desde archivos locales."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """Inicializa el coordinador para predicciones diarias."""
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.file_path = files_folder / f"forecast_{self.town_id.lower()}_daily_data.json"
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Daily Forecast Coordinator",
            update_interval=DEFAULT_DAILY_FORECAST_UPDATE_INTERVAL,
        )

    def _convert_to_local_date(self, forecast_time: datetime) -> datetime.date:
        """Convierte una hora UTC a la fecha local en la zona horaria de Madrid, considerando el horario de verano."""
        # Asegura que forecast_time es datetime y no date
        if not isinstance(forecast_time, datetime):
            forecast_time = datetime.combine(forecast_time, time(0, tzinfo=timezone.utc))

        # Convertir la hora UTC a la hora local y extraer solo la fecha
        local_datetime = forecast_time.astimezone(TIMEZONE)
        return local_datetime.date()

    async def _is_data_valid(self) -> bool:
        """Verifica si hay datos válidos y actuales en el archivo JSON."""
        if not self.file_path.exists():
            return False

        try:
            async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            if not data or "dies" not in data or not data["dies"]:
                return False

            today = datetime.now(TIMEZONE).date()
            for dia in data["dies"]:
                forecast_date = datetime.fromisoformat(dia["data"].rstrip("Z")).date()
                forecast_date_local = self._convert_to_local_date(forecast_date)
                if forecast_date_local >= today:
                    return True

            return False
        except Exception as e:
            _LOGGER.warning("Error validando datos diarios en %s: %s", self.file_path, e)
            return False

    async def _async_update_data(self) -> dict:
        """Lee y filtra los datos de predicción diaria desde el archivo local."""
        if await self._is_data_valid():
            try:
                async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)

                # Filtrar días pasados
                today = datetime.now(TIMEZONE).date()
                filtered_days = []
                for dia in data["dies"]:
                    forecast_date = datetime.fromisoformat(dia["data"].rstrip("Z"))
                    forecast_date_local = self._convert_to_local_date(forecast_date)
                    if forecast_date_local >= today:
                        filtered_days.append(dia)

                data["dies"] = filtered_days
                return data
            except Exception as e:
                _LOGGER.warning("Error leyendo archivo de predicción diaria en %s: %s", self.file_path, e)

        return {}

    def get_forecast_for_today(self) -> dict | None:
        """Obtiene los datos diarios para el día actual."""
        if not self.data or "dies" not in self.data or not self.data["dies"]:
            return None

        today = datetime.now(TIMEZONE).date()
        for dia in self.data["dies"]:
            forecast_date = datetime.fromisoformat(dia["data"].rstrip("Z")).date()
            forecast_date_local = self._convert_to_local_date(forecast_date)
            if forecast_date_local == today:
                return dia
        return None

    def parse_forecast(self, dia: dict) -> dict:
        """Convierte un día de predicción en un diccionario con los datos necesarios."""
        variables = dia.get("variables", {})
        condition_code = variables.get("estatCel", {}).get("valor", -1)
        condition = get_condition_from_code(int(condition_code))

        # Usar la fecha original del pronóstico
        forecast_date = datetime.fromisoformat(dia["data"].rstrip("Z"))
        forecast_date_local = self._convert_to_local_date(forecast_date)

        forecast_data = {
            "date": forecast_date_local.isoformat(),
            "temperature_max": float(variables.get("tmax", {}).get("valor", 0.0)),
            "temperature_min": float(variables.get("tmin", {}).get("valor", 0.0)),
            "precipitation": float(variables.get("precipitacio", {}).get("valor", 0.0)),
            "condition": condition,
        }
        return forecast_data

    def get_all_daily_forecasts(self) -> list[dict]:
        """Obtiene una lista de predicciones diarias procesadas."""
        if not self.data or "dies" not in self.data:
            return []

        forecasts = []
        for dia in self.data["dies"]:
            forecasts.append(self.parse_forecast(dia))
        return forecasts

class MeteocatConditionCoordinator(DataUpdateCoordinator):
    """Coordinator to read and process Condition data from a file."""

    DEFAULT_CONDITION = {"condition": "unknown", "hour": None, "icon": None, "date": None}

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Initialize the Meteocat Condition Coordinator.

        Args:
            hass (HomeAssistant): Instance of Home Assistant.
            entry_data (dict): Configuration data from core.config_entries.
        """
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]  # Municipality ID
        self.hass = hass

        # === NUEVO: ubicación solar usando solarmoonpy ===
        latitude = entry_data.get("latitude", hass.config.latitude)
        longitude = entry_data.get("longitude", hass.config.longitude)
        altitude = entry_data.get("altitude", hass.config.elevation or 0.0)
        timezone_str = hass.config.time_zone or "Europe/Madrid"

        self.location = Location(
            LocationInfo(
                name=self.town_name,
                region="Spain",
                timezone=timezone_str,
                latitude=latitude,
                longitude=longitude,
                elevation=altitude,
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Condition Coordinator",
            update_interval=DEFAULT_CONDITION_SENSOR_UPDATE_INTERVAL,
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self._file_path = files_folder / f"forecast_{self.town_id.lower()}_hourly_data.json"

    async def _async_update_data(self):
        """Read and process condition data for the current hour from the file asynchronously."""
        _LOGGER.debug("Iniciando actualización de datos desde el archivo: %s", self._file_path)

        raw_data = await load_json_from_file(self._file_path)
        if not raw_data:
            return self.DEFAULT_CONDITION

        return self._get_condition_for_current_hour(raw_data) or self.DEFAULT_CONDITION
    
    def _convert_to_local_time(self, forecast_time: datetime) -> datetime:
        """Convierte una hora UTC a la hora local en la zona horaria de Madrid, considerando el horario de verano."""
        return forecast_time.astimezone(TIMEZONE)

    def _get_condition_for_current_hour(self, raw_data):
        """Get condition data for the current hour."""
        current_datetime = datetime.now(TIMEZONE)
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_hour = current_datetime.hour

        for day in raw_data.get("dies", []):
            if day["data"].startswith(current_date):
                for value in day["variables"]["estatCel"]["valors"]:
                    data_hour = datetime.fromisoformat(value["data"]).replace(tzinfo=ZoneInfo("UTC"))
                    local_hour = self._convert_to_local_time(data_hour)
                    if local_hour.hour == current_hour:
                        codi_estatcel = value["valor"]
                        condition = get_condition_from_statcel(
                            codi_estatcel,
                            current_datetime,
                            location=self.location,
                            is_hourly=True,
                        )
                        condition.update({
                            "hour": current_hour,
                            "date": current_date,
                        })
                        _LOGGER.debug(
                            "Hora actual: %s, Código estatCel: %s, Condición procesada: %s",
                            current_datetime,
                            codi_estatcel,
                            condition,
                        )
                        return condition
                break

        _LOGGER.warning(
            "No se encontraron datos del Estado del Cielo para hoy (%s) y la hora actual (%s).",
            current_date,
            current_hour,
        )
        return {"condition": "unknown", "hour": current_hour, "icon": None, "date": current_date}


class MeteocatTempForecastCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la temperatura máxima y mínima de las predicciones diarias desde archivos locales."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """Inicializa el coordinador para las temperaturas máximas y mínimas de predicciones diarias."""
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Daily Temperature Forecast Coordinator",
            update_interval=DEFAULT_TEMP_FORECAST_UPDATE_INTERVAL,
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.file_path = files_folder / f"forecast_{self.town_id.lower()}_daily_data.json"

    def _convert_to_local_time(self, forecast_time: datetime) -> datetime:
        """Convierte una hora UTC a la hora local en la zona horaria de Madrid, considerando el horario de verano."""
        return forecast_time.astimezone(TIMEZONE)

    async def _is_data_valid(self) -> bool:
        """Verifica si hay datos válidos y actuales en el archivo JSON."""
        data = await load_json_from_file(self.file_path)
        if not data or "dies" not in data or not data["dies"]:
            return False

        today = datetime.now(TIMEZONE).date()
        return any(
            self._convert_to_local_time(
                datetime.fromisoformat(dia["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
            ).date() >= today
            for dia in data["dies"]
        )

    async def _async_update_data(self) -> dict:
        """Lee y filtra los datos de predicción diaria desde el archivo local."""
        if await self._is_data_valid():
            data = await load_json_from_file(self.file_path)
            if not data:
                return {}

            today = datetime.now(TIMEZONE).date()
            data["dies"] = [
                dia for dia in data["dies"]
                if self._convert_to_local_time(
                    datetime.fromisoformat(dia["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
                ).date() >= today
            ]

            today_temp_forecast = self.get_temp_forecast_for_today(data)
            if today_temp_forecast:
                return self.parse_temp_forecast(today_temp_forecast)

        return {}

    def get_temp_forecast_for_today(self, data: dict) -> dict | None:
        """Obtiene los datos de temperaturas diarios para el día actual."""
        if not data or "dies" not in data or not data["dies"]:
            return None

        today = datetime.now(TIMEZONE).date()
        for dia in data["dies"]:
            forecast_date_utc = datetime.fromisoformat(dia["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
            forecast_date_local = self._convert_to_local_time(forecast_date_utc)
            if forecast_date_local.date() == today:
                return dia
        return None

    def parse_temp_forecast(self, dia: dict) -> dict:
        """Convierte la temperatura de un día de predicción en un diccionario con los datos necesarios."""
        variables = dia.get("variables", {})
        forecast_date_utc = datetime.fromisoformat(dia["data"].rstrip("Z")).replace(tzinfo=timezone.utc)

        temp_forecast_data = {
            "date": self._convert_to_local_time(forecast_date_utc).date(),
            "max_temp_forecast": float(variables.get("tmax", {}).get("valor", 0.0)),
            "min_temp_forecast": float(variables.get("tmin", {}).get("valor", 0.0)),
        }
        return temp_forecast_data
    
class MeteocatAlertsCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de alertas."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        """
        Inicializa el coordinador de alertas de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
        """
        self.api_key = entry_data["api_key"]
        self.region_id = entry_data["region_id"]  # ID de la región o comarca
        self.limit_prediccio = entry_data["limit_prediccio"]  # Límite de llamada a la API para PREDICCIONES
        self.alerts_data = MeteocatAlerts(self.api_key)

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.alerts_file = files_folder / "alerts.json"
        self.alerts_region_file = files_folder / f"alerts_{self.region_id}.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Alerts Coordinator",
            update_interval=DEFAULT_ALERTS_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de alertas desde la API de Meteocat o desde el archivo local según las condiciones especificadas."""
        # Comprobar si existe el archivo 'alerts.json'
        existing_data = await load_json_from_file(self.alerts_file)

        # Calcular el tiempo de validez basado en el límite de predicción
        if self.limit_prediccio <= 100:
            multiplier = ALERT_VALIDITY_MULTIPLIER_100
        elif 100 < self.limit_prediccio <= 200:
            multiplier = ALERT_VALIDITY_MULTIPLIER_200
        elif 200 < self.limit_prediccio <= 500:
            multiplier = ALERT_VALIDITY_MULTIPLIER_500
        else:
            multiplier = ALERT_VALIDITY_MULTIPLIER_DEFAULT

        validity_duration = timedelta(minutes=DEFAULT_ALERT_VALIDITY_TIME * multiplier)
        
        # Si no existe el archivo
        if not existing_data:
            return await self._fetch_and_save_new_data()
        else:
            # Comprobar la antigüedad de los datos
            last_update = datetime.fromisoformat(existing_data['actualitzat']['dataUpdate'])
            now = datetime.now(timezone.utc).astimezone(TIMEZONE)

            # Comparar la antigüedad de los datos
            if now - last_update > validity_duration:
                return await self._fetch_and_save_new_data()
            else:
                # Comprobar si el archivo regional sigue con INITIAL_TEMPLATE o sin datos válidos
                region_data = await load_json_from_file(self.alerts_region_file)
                if (
                    not region_data
                    or region_data.get("actualitzat", {}).get("dataUpdate") in [None, "1970-01-01T00:00:00+00:00"]
                ):
                    _LOGGER.info(
                        "El archivo regional %s sigue con plantilla inicial. Regenerando a partir de alerts.json",
                        self.alerts_region_file,
                    )
                    await self._filter_alerts_by_region()

                # Devolver los datos del archivo existente
                _LOGGER.debug("Usando datos existentes de alertas: %s", existing_data)
                return {
                "actualizado": existing_data['actualitzat']['dataUpdate']
                }

    async def _fetch_and_save_new_data(self):
        """Obtiene nuevos datos de la API y los guarda en el archivo JSON."""
        try:
            # Obtener los datos de alertas desde la API
            data = await asyncio.wait_for(self.alerts_data.get_alerts(), timeout=30)
            _LOGGER.debug("Datos de alertas actualizados exitosamente: %s", data)

            # Validar que los datos sean una lista de diccionarios o una lista vacía
            if not isinstance(data, list) or (data and not all(isinstance(item, dict) for item in data)):
                _LOGGER.error(
                    "Formato inválido: Se esperaba una lista de diccionarios, pero se obtuvo %s. Datos: %s",
                    type(data).__name__,
                    data,
                )
                raise ValueError("Formato de datos inválido")
            
            # Actualizar cuotas usando la función externa
            await _update_quotes(self.hass, "Prediccio")  # Asegúrate de usar el nombre correcto del plan aquí
            
            # Añadir la clave 'actualitzat' con la fecha y hora actual de la zona horaria local
            current_time = datetime.now(timezone.utc).astimezone(TIMEZONE).isoformat()
            data_with_timestamp = {
                "actualitzat": {
                    "dataUpdate": current_time
                },
                "dades": data
            }

            # Guardar los datos de alertas en un archivo JSON
            await save_json_to_file(data_with_timestamp, self.alerts_file)

            # Filtrar los datos por región y guardar en un nuevo archivo JSON
            await self._filter_alerts_by_region()

            # Devolver tanto los datos de alertas como la fecha de actualización
            return {
                "actualizado": data_with_timestamp['actualitzat']['dataUpdate']
            }
        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener datos de alertas.")
            raise ConfigEntryNotReady from err
        except ForbiddenError as err:
            _LOGGER.error("Acceso denegado al obtener datos de alertas: %s", err)
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning("Límite de solicitudes alcanzado al obtener datos de alertas: %s", err)
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error("Error al obtener datos de alertas: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Error al obtener alertas: %s", err)
            
        # === FALLBACK SEGURO ===
        cached_data = await load_json_from_file(self.alerts_file)
        if self._is_valid_alert_data(cached_data):
            update_str = cached_data["actualitzat"]["dataUpdate"]
            try:
                update_dt = datetime.fromisoformat(update_str)
                local_dt = update_dt.astimezone(TIMEZONE)
                display_time = local_dt.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                display_time = update_str
            
            _LOGGER.warning(
                "ALERTAS: API falló → usando caché local:\n"
                "   • Archivo: %s\n"
                "   • Última actualización: %s\n"
                "   • Alertas activas: %d",
                self.alerts_file.name,
                display_time
            )
            
            self.async_set_updated_data({
                "actualizado": cached_data["actualitzat"]["dataUpdate"]
            })
            return {"actualizado": cached_data["actualitzat"]["dataUpdate"]}
        
        _LOGGER.error("ALERTAS: No hay caché disponible. Sin datos de alertas.")
        self.async_set_updated_data({})
        return {}

    @staticmethod
    def _is_valid_alert_data(data: dict) -> bool:
        """Valida que los datos de alertas tengan el formato esperado."""
        return (
            isinstance(data, dict)
            and "dades" in data
            and isinstance(data["dades"], list)
            and (not data["dades"] or all(isinstance(item, dict) for item in data["dades"]))
            and "actualitzat" in data
            and isinstance(data["actualitzat"], dict)
            and "dataUpdate" in data["actualitzat"]
        )
    
    async def _filter_alerts_by_region(self):
        """Filtra las alertas por la región y guarda los resultados en un archivo JSON."""
        # Obtener el momento actual
        now = datetime.now(timezone.utc).astimezone(TIMEZONE).isoformat()

        # Carga el archivo alerts.json
        data = await load_json_from_file(self.alerts_file)
        if not data:
            _LOGGER.error("El archivo de alertas %s no existe o está vacío.", self.alerts_file)
            return

        filtered_alerts = []

        for item in data.get("dades", []):
            avisos_filtrados = []

            for aviso in item.get("avisos", []):
                evolucions = []
                data_inici = None
                data_fi = None

                for evolucion in aviso.get("evolucions", []):
                    periodes = []
                    for periode in evolucion.get("periodes", []):
                        afectacions = [
                            afectacio for afectacio in (periode.get("afectacions") or [])
                            if afectacio and str(afectacio.get("idComarca")) == self.region_id
                        ]
                        if afectacions:
                            if not data_inici:
                                dia = evolucion.get("dia")[:-6]
                                data_inici = f"{dia}{periode.get('nom').split('-')[0]}:00Z"
                            
                            # Calcular dataFi
                            dia = evolucion.get('dia')[:-6]  # Eliminar "T00:00Z"
                            hora_fin = periode.get('nom').split('-')[1]
                            # Ajustar dataFi correctamente si termina a medianoche
                            if hora_fin == "00":
                                dia = evolucion.get('dia')[:-6]  # Eliminar "T00:00Z"
                                data_fi = f"{dia}23:59Z"
                            else:
                                dia = evolucion.get('dia')[:-6]  # Eliminar "T00:00Z"
                                data_fi = f"{dia}{hora_fin}:00Z"

                        periodes.append({
                            "nom": periode.get("nom"),
                            "afectacions": afectacions if afectacions else None
                        })

                    if any(p.get("afectacions") for p in periodes):
                        evolucions.append({
                            "dia": evolucion.get("dia"),
                            "comentari": evolucion.get("comentari"),
                            "representatiu": evolucion.get("representatiu"),
                            "llindar1": evolucion.get("llindar1"),
                            "llindar2": evolucion.get("llindar2"),
                            "distribucioGeografica": evolucion.get("distribucioGeografica"),
                            "periodes": periodes,
                            "valorMaxim": evolucion.get("valorMaxim")
                        })

                # Comprobar si la fecha de fin ya ha pasado
                if evolucions and data_fi >= now:
                    avisos_filtrados.append({
                        "tipus": aviso.get("tipus"),
                        "dataEmisio": aviso.get("dataEmisio"),
                        "dataInici": data_inici,
                        "dataFi": data_fi,
                        "evolucions": evolucions,
                        "estat": aviso.get("estat")
                    })

            if avisos_filtrados:
                filtered_alerts.append({
                    "estat": item.get("estat"),
                    "meteor": item.get("meteor"),
                    "avisos": avisos_filtrados
                })

        # Guardar los datos filtrados en un archivo JSON
        await save_json_to_file({
            "actualitzat": data.get("actualitzat"),
            "dades": filtered_alerts
        }, self.alerts_region_file)

class MeteocatAlertsRegionCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de alertas por región."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        """Inicializa el coordinador para alertas de una comarca."""
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.region_name = entry_data["region_name"]
        self.region_id = entry_data["region_id"]

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Alerts Region Coordinator",
            update_interval=DEFAULT_ALERTS_REGION_UPDATE_INTERVAL,
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self._file_path = files_folder / f"alerts_{self.region_id}.json"

    def _convert_to_local_time(self, time_str: str) -> datetime:
        """Convierte una cadena de tiempo UTC a la zona horaria de Madrid."""
        if not time_str:
            return None
        # Convertir el tiempo de ISO a datetime con zona horaria UTC
        utc_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        # Convertir la hora UTC a la hora local
        local_time = utc_time.astimezone(TIMEZONE)
        return local_time
    
    def _count_active_alerts(self, data: dict) -> int:
        """Cuenta las alertas activas procesando todas las alertas, sin detenerse en la primera coincidencia."""
        if not isinstance(data, dict) or "dades" not in data:
            _LOGGER.warning("Formato inesperado: 'dades' no es un diccionario o no contiene 'dades'.")
            return 0

        active_alerts = 0
        current_time = datetime.now(TIMEZONE)  # Hora local de Madrid

        for item in data["dades"]:  # Directamente acceder a 'dades' ya que sabemos que existe
            # Obtener el estado global de la alerta desde "dades"
            estat = item.get("estat", {}).get("nom")
            
            # Proceder solo si el estado es "Obert"
            if estat == "Obert":
                avisos = item.get("avisos", [])
                for aviso in avisos:
                    # Convertir las fechas de inicio y fin a hora local
                    start_time = self._convert_to_local_time(aviso.get("dataInici"))
                    end_time = self._convert_to_local_time(aviso.get("dataFi"))
                    
                    # Verificar las condiciones para contar como alerta activa
                    if start_time and end_time and start_time <= current_time <= end_time + timedelta(seconds=1):
                        _LOGGER.debug(
                            f"Alerta activa encontrada: {item.get('meteor', {}).get('nom', 'Desconocido')}"
                        )
                        active_alerts += 1

        return active_alerts

    def _get_time_period(self, current_hour: int) -> str:
        """Devuelve la franja horaria actual en formato 'nom'."""
        periods = ["00-06", "06-12", "12-18", "18-00"]
        if 0 <= current_hour < 6:
            return periods[0]
        elif 6 <= current_hour < 12:
            return periods[1]
        elif 12 <= current_hour < 18:
            return periods[2]
        else:
            return periods[3]
    
    def _convert_period_to_local_time(self, period: str, date: str) -> str:
        """Convierte un periodo UTC a la hora local para una fecha específica."""
        utc_times = period.split("-")
        # Manejar la transición de "18-00" como "18-24" para el cálculo
        start_utc = utc_times[0]
        end_utc = "24" if utc_times[1] == "00" else utc_times[1]
        
        # Convertir los tiempos UTC a datetime
        date_utc = datetime.fromisoformat(f"{date}T00:00+00:00")  # Fecha base en UTC
        start_local = (date_utc + timedelta(hours=int(start_utc))).astimezone(TIMEZONE)
        end_local = (date_utc + timedelta(hours=int(end_utc))).astimezone(TIMEZONE)
        
        # Formatear los tiempos a "HH:MM"
        return f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')}"

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga y procesa los datos de alertas desde el archivo JSON."""
        data = await load_json_from_file(self._file_path)
        _LOGGER.debug("Datos cargados desde %s: %s", self._file_path, data)  # Log de la carga de datos

        if not data:
            _LOGGER.error("No se pudo cargar el archivo JSON de alertas en %s.", self._file_path)
            return {}

        return self._process_alerts_data(data)

    def _process_alerts_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa los datos de alertas y devuelve un diccionario filtrado por región."""
        if not data.get("dades"):
            _LOGGER.debug("No hay alertas activas para la región %s.", self.region_id)
            return {
                "estado": "Tancat",
                "actualizado": data.get("actualitzat", {}).get("dataUpdate", ""),
                "activas": 0,  # Sin alertas activas
                "detalles": {"meteor": {}}
            }

        # Obtener la fecha de actualización y añadirla a detalles
        data_update = data.get("actualitzat", {}).get("dataUpdate", "")
        current_time = datetime.now(TIMEZONE)
        current_date = current_time.date()
        current_hour = current_time.hour
        current_period = self._get_time_period(current_hour)

        periods = ["00-06", "06-12", "12-18", "18-00"]
        current_period_index = periods.index(current_period)

        alert_data = {
            "estado": "Obert",
            "actualizado": data_update,
            "activas": 0,  # Inicializamos a 0 y actualizamos al final
            "detalles": {"meteor": {}}
        }

        for alert in data["dades"]:
            estat = alert.get("estat", {}).get("nom", "Desconocido")
            meteor = alert.get("meteor", {}).get("nom", "Desconocido")
            avisos = alert.get("avisos", [])
            alert_found = False  # Bandera para saber si encontramos una alerta para este meteor

            for aviso in avisos:
                data_inici = self._convert_to_local_time(aviso.get("dataInici"))
                data_fi = self._convert_to_local_time(aviso.get("dataFi"))
                _LOGGER.info("Procesando aviso: inicio=%s, fin=%s", data_inici, data_fi)  # Log del aviso

                if data_inici and data_fi and data_inici <= data_fi:  # Asegurarse que data_inici no sea mayor que data_fi
                    evoluciones = aviso.get("evolucions", [])
                    for evolucion in evoluciones:
                        evolucion_date = datetime.fromisoformat(evolucion["dia"].replace("Z", "+00:00")).date()
                        comentario = evolucion.get("comentari", "")

                        if evolucion_date >= current_date:  # Mirar desde el día actual hacia adelante
                            if evolucion_date == current_date:
                                # Mirar el periodo actual y el siguiente si no hay alerta
                                periodos_a_revisar = evolucion.get("periodes", [])[current_period_index:]
                                if len(periodos_a_revisar) == 0 or not any(periodo.get("afectacions") for periodo in periodos_a_revisar):
                                    # Si no hay alertas en los periodos actuales o siguientes, miramos el siguiente periodo
                                    if current_period_index + 1 < len(periods):
                                        next_period = next((p for p in evolucion.get("periodes", []) if p.get("nom") == periods[current_period_index + 1]), None)
                                        if next_period and next_period.get("afectacions"):
                                            periodos_a_revisar = [next_period]
                                        else:
                                            periodos_a_revisar = []
                                    else:
                                        # Si estamos en el último periodo, miramos a días futuros
                                        periodos_a_revisar = []
                            else:
                                periodos_a_revisar = evolucion.get("periodes", [])

                            for periodo in periodos_a_revisar:
                                local_period = self._convert_period_to_local_time(periodo["nom"], evolucion["dia"][:10])
                                afectaciones = periodo.get("afectacions", [])
                                if not afectaciones:
                                    _LOGGER.debug("No se encontraron afectaciones en el período: %s", periodo["nom"])
                                    continue

                                for afectacion in afectaciones:
                                    if afectacion.get("idComarca") == int(self.region_id):  # Filtrar por idComarca de la región
                                        if not alert_found:  # Solo agregamos la primera alerta encontrada para este meteor
                                            alert_data["detalles"]["meteor"][meteor] = {
                                                "fecha": evolucion["dia"][:10],
                                                "periodo": local_period,
                                                "estado": estat,
                                                "motivo": meteor,
                                                "inicio": data_inici,
                                                "fin": data_fi,
                                                "comentario": comentario,
                                                "umbral": afectacion.get("llindar", "Desconocido"),
                                                "peligro": afectacion.get("perill", 0),
                                                "nivel": afectacion.get("nivell", 0),
                                            }
                                            alert_found = True
                                            _LOGGER.info(
                                                "Alerta encontrada y agregada para %s: %s",
                                                meteor,
                                                alert_data["detalles"]["meteor"][meteor],
                                            )
                                            break  # Salimos del ciclo de afectaciones ya que encontramos una alerta
                                if alert_found:
                                    break  # Salimos del ciclo de periodos ya que encontramos una alerta
                        if alert_found:
                            break  # Salimos del ciclo de evoluciones si ya encontramos una alerta

        alert_data["activas"] = len(alert_data["detalles"]["meteor"])  # Actualizar el número de alertas activas
        _LOGGER.info("Detalles recibidos: %s", alert_data.get("detalles", []))

        return alert_data

class MeteocatQuotesCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de las cuotas de la API de Meteocat."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador de cuotas de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
        """
        self.api_key = entry_data["api_key"]  # Usamos la API key de la configuración
        self.meteocat_quotes = MeteocatQuotes(self.api_key)

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.quotes_file = files_folder / "quotes.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Quotes Coordinator",
            update_interval=DEFAULT_QUOTES_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de las cuotas desde la API de Meteocat o usa datos en caché según la antigüedad."""
        existing_data = await load_json_from_file(self.quotes_file) or {}

        # Definir la duración de validez de los datos
        validity_duration = timedelta(minutes=DEFAULT_QUOTES_VALIDITY_TIME)

        # Si no existe el archivo
        if not existing_data:
            return await self._fetch_and_save_new_data()
        else:
            # Comprobar la antigüedad de los datos
            last_update = datetime.fromisoformat(existing_data['actualitzat']['dataUpdate'])
            now = datetime.now(timezone.utc).astimezone(TIMEZONE)

            # Comparar la antigüedad de los datos
            if now - last_update >= validity_duration:
                return await self._fetch_and_save_new_data()
            else:
                # Devolver los datos del archivo existente
                _LOGGER.debug("Usando datos existentes de cuotas: %s", existing_data)
                return {
                "actualizado": existing_data['actualitzat']['dataUpdate']
                }

    async def _fetch_and_save_new_data(self):
        """Obtiene nuevos datos de la API y los guarda en el archivo JSON."""
        try:
            data = await asyncio.wait_for(
                self.meteocat_quotes.get_quotes(),
                timeout=30  # Tiempo límite de 30 segundos
            )
            _LOGGER.debug("Datos de cuotas actualizados exitosamente: %s", data)

            if not isinstance(data, dict):
                _LOGGER.error("Formato inválido: Se esperaba un diccionario, pero se obtuvo %s", type(data).__name__)
                raise ValueError("Formato de datos inválido")
            
            # Modificar los nombres de los planes con normalización
            plan_mapping = {
                "xdde_": "XDDE",
                "prediccio_": "Prediccio",
                "referencia basic": "Basic",
                "xema_": "XEMA",
                "quota": "Quota"
            }

            modified_plans = []
            for plan in data["plans"]:
                normalized_nom = normalize_name(plan["nom"])
                new_name = next((v for k, v in plan_mapping.items() if normalized_nom.startswith(k)), plan["nom"])

                # Si el plan es "Quota", actualizamos las consultas realizadas y restantes
                if new_name == "Quota":
                    plan["consultesRealitzades"] += 1
                    plan["consultesRestants"] = max(0, plan["consultesRestants"] - 1)

                modified_plans.append({
                    "nom": new_name,
                    "periode": plan["periode"],
                    "maxConsultes": plan["maxConsultes"],
                    "consultesRestants": plan["consultesRestants"],
                    "consultesRealitzades": plan["consultesRealitzades"]
                })

            # Añadir la clave 'actualitzat' con la fecha y hora actual de la zona horaria local
            current_time = datetime.now(timezone.utc).astimezone(TIMEZONE).isoformat()
            data_with_timestamp = {
                "actualitzat": {
                    "dataUpdate": current_time
                },
                "client": data["client"],
                "plans": modified_plans
            }

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data_with_timestamp, self.quotes_file)

            # Devolver tanto los datos de alertas como la fecha de actualización
            return {
                "actualizado": data_with_timestamp['actualitzat']['dataUpdate']
            }

        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener las cuotas de la API de Meteocat.")
            raise ConfigEntryNotReady from err
        except ForbiddenError as err:
            _LOGGER.error("Acceso denegado al obtener cuotas de la API de Meteocat: %s", err)
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning("Límite de solicitudes alcanzado al obtener cuotas de la API de Meteocat: %s", err)
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error("Error al obtener cuotas de la API de Meteocat: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Error al obtener cuotas: %s", err)
           
        # === FALLBACK SEGURO ===
        cached_data = await load_json_from_file(self.quotes_file)
        if cached_data and "actualitzat" in cached_data and "dataUpdate" in cached_data["actualitzat"]:
            update_str = cached_data["actualitzat"]["dataUpdate"]
            try:
                update_dt = datetime.fromisoformat(update_str)
                local_dt = update_dt.astimezone(TIMEZONE)
                display_time = local_dt.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                display_time = update_str.split("T")[0]
            
            # Contar planes activos
            plans_count = len(cached_data.get("plans", []))
            
            _LOGGER.warning(
                "CUOTAS: API falló → usando caché local:\n"
                "   • Archivo: %s\n"
                "   • Última actualización: %s\n"
                "   • Planes registrados: %d",
                self.quotes_file.name,
                display_time,
                plans_count
            )
            
            self.async_set_updated_data({
                "actualizado": cached_data["actualitzat"]["dataUpdate"]
            })
            return {"actualizado": cached_data["actualitzat"]["dataUpdate"]}
        
        _LOGGER.error("CUOTAS: No hay caché disponible. Sin información de consumo.")
        self.async_set_updated_data({})
        return {}
    
class MeteocatQuotesFileCoordinator(BaseFileCoordinator):
    """Coordinator para manejar la actualización de las cuotas desde quotes.json."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador del sensor de cuotas de la API de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
            update_interval (timedelta): Intervalo de actualización.
        """
        self.town_id = entry_data["town_id"]  # Usamos el ID del municipio

        super().__init__(
            hass,
            name=f"{DOMAIN} Quotes File Coordinator",
            update_interval=DEFAULT_QUOTES_FILE_UPDATE_INTERVAL,
            min_delay=1.0,  # Rango predeterminado
            max_delay=2.0,  # Rango predeterminado
        )
        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.quotes_file = files_folder / "quotes.json"

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de quotes.json y devuelve el estado de las cuotas."""
        # 🔸 Añadimos un pequeño desfase aleatorio (1 a 2 segundos) basados en el BaseFileCoordinator
        await self._apply_random_delay()

        existing_data = await load_json_from_file(self.quotes_file)

        if not existing_data:
            _LOGGER.warning("No se encontraron datos en quotes.json.")
            return {}

        return {
            "actualizado": existing_data.get("actualitzat", {}).get("dataUpdate"),
            "client": existing_data.get("client", {}).get("nom"),
            "plans": [
                {
                    "nom": plan.get("nom"),
                    "periode": plan.get("periode"),
                    "maxConsultes": plan.get("maxConsultes"),
                    "consultesRestants": plan.get("consultesRestants"),
                    "consultesRealitzades": plan.get("consultesRealitzades"),
                }
                for plan in existing_data.get("plans", [])
            ]
        }

    async def get_plan_info(self, plan_name: str) -> dict:
        """Obtiene la información de un plan específico."""
        data = await self._async_update_data()
        for plan in data.get("plans", []):
            if plan.get("nom") == plan_name:
                return {
                    "nom": plan.get("nom"),
                    "periode": plan.get("periode"),
                    "maxConsultes": plan.get("maxConsultes"),
                    "consultesRestants": plan.get("consultesRestants"),
                    "consultesRealitzades": plan.get("consultesRealitzades"),
                }
        _LOGGER.warning("Plan %s no encontrado en quotes.json.", plan_name)
        return {}

class MeteocatLightningCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de rayos de la API de Meteocat."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador de rayos de Meteocat.
        
        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
        """
        self.api_key = entry_data["api_key"]  # API Key de la configuración
        self.region_id = entry_data["region_id"]  # Región de la configuración
        self.meteocat_lightning = MeteocatLightning(self.api_key)

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.lightning_file = files_folder / f"lightning_{self.region_id}.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Lightning Coordinator",
            update_interval=DEFAULT_LIGHTNING_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de rayos desde la API de Meteocat o usa datos en caché según la antigüedad."""
        existing_data = await load_json_from_file(self.lightning_file) or {}

        # Definir la duración de validez de los datos
        now = datetime.now(timezone.utc).astimezone(TIMEZONE)
        current_time = now.time()  # Extraer solo la parte de la hora
        offset = now.utcoffset().total_seconds() / 3600  # Obtener el offset en horas
        
        # Determinar la hora de validez considerando el offset horario, el horario de verano (+02:00) o invierno (+01:00)
        validity_start_time = time(int(DEFAULT_LIGHTNING_VALIDITY_HOURS + offset), DEFAULT_LIGHTNING_VALIDITY_MINUTES)
        
        validity_duration = timedelta(minutes=DEFAULT_LIGHTNING_VALIDITY_TIME)

        if not existing_data:
            return await self._fetch_and_save_new_data()
        else:
            last_update = datetime.fromisoformat(existing_data['actualitzat']['dataUpdate'])
            
            if now - last_update >= validity_duration and current_time >= validity_start_time:
                return await self._fetch_and_save_new_data()
            else:
                _LOGGER.debug("Usando datos existentes de rayos: %s", existing_data)
                return {"actualizado": existing_data['actualitzat']['dataUpdate']}

    async def _fetch_and_save_new_data(self):
        """Obtiene nuevos datos de la API y los guarda en el archivo JSON."""
        try:
            data = await asyncio.wait_for(
                self.meteocat_lightning.get_lightning_data(self.region_id),
                timeout=30  # Tiempo límite de 30 segundos
            )
            _LOGGER.debug("Datos de rayos actualizados exitosamente: %s", data)

            # Verificar que `data` sea una lista (como la API de Meteocat devuelve)
            if not isinstance(data, list):
                _LOGGER.error("Formato inválido: Se esperaba una lista, pero se obtuvo %s", type(data).__name__)
                raise ValueError("Formato de datos inválido")

            # Estructurar los datos en el formato correcto
            current_time = datetime.now(timezone.utc).astimezone(TIMEZONE).isoformat()
            data_with_timestamp = {
                "actualitzat": {
                    "dataUpdate": current_time
                },
                "dades": data  # Siempre será una lista
            }

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data_with_timestamp, self.lightning_file)

            # Actualizar cuotas usando la función externa
            await _update_quotes(self.hass, "XDDE")  # Asegúrate de usar el nombre correcto del plan aquí

            return {"actualizado": data_with_timestamp['actualitzat']['dataUpdate']}

        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener los datos de rayos de la API de Meteocat.")
            raise ConfigEntryNotReady from err
        except Exception as err:
            _LOGGER.exception("Error al obtener datos de rayos: %s", err)
            
        # === FALLBACK SEGURO ===
        cached_data = await load_json_from_file(self.lightning_file)
        if cached_data and "actualitzat" in cached_data:
            update_str = cached_data["actualitzat"]["dataUpdate"]
            try:
                update_dt = datetime.fromisoformat(update_str)
                # Convertir a hora local para mostrar
                local_dt = update_dt.astimezone(TIMEZONE)
                display_time = local_dt.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                display_time = update_str
            
            _LOGGER.warning(
                "API rayos falló → usando caché local:\n"
                "   • Archivo: %s\n"
                "   • Última actualización: %s",
                self.lightning_file.name,
                display_time
            )

            self.async_set_updated_data({
                "actualizado": cached_data["actualitzat"]["dataUpdate"]
            })
            return {"actualizado": cached_data["actualitzat"]["dataUpdate"]}
        
        _LOGGER.error("No hay caché de rayos disponible.")
        self.async_set_updated_data({})
        return {}

class MeteocatLightningFileCoordinator(BaseFileCoordinator):
    """Coordinator para manejar la actualización de los datos de rayos desde lightning_{region_id}.json."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        """
        Inicializa el coordinador de rayos desde archivo.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración de la entrada.
        """
        self.region_id = entry_data["region_id"]
        self.town_id = entry_data["town_id"]

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.lightning_file = files_folder / f"lightning_{self.region_id}.json"

        # ✅ Marca interna para recordar si ya se hizo reset con una fecha concreta
        self._last_reset_date: Optional[date] = None

        super().__init__(
            hass,
            name=f"{DOMAIN} Lightning File Coordinator",
            update_interval=DEFAULT_LIGHTNING_FILE_UPDATE_INTERVAL,
            min_delay=1.0,  # Rango predeterminado
            max_delay=2.0,  # Rango predeterminado
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de rayos desde el archivo JSON y procesa la información."""
       # 🔸 Añadimos un pequeño desfase aleatorio (1 a 2 segundos) basados en el BaseFileCoordinator
        await self._apply_random_delay()
        
        existing_data = await load_json_from_file(self.lightning_file)

        if not existing_data:
            _LOGGER.warning("No se encontraron datos en %s.", self.lightning_file)
            return self._empty_state()

        # Obtener fecha de actualización del JSON
        update_date_str = existing_data.get("actualitzat", {}).get("dataUpdate", "")
        if not update_date_str:
            _LOGGER.warning("El archivo %s no contiene campo 'dataUpdate'.", self.lightning_file)
            return self._empty_state()

        try:
            update_date = datetime.fromisoformat(update_date_str).astimezone(TIMEZONE)
        except ValueError:
            _LOGGER.warning("Formato de fecha inválido en %s: %s", self.lightning_file, update_date_str)
            return self._empty_state()

        now = datetime.now(TIMEZONE)

        # 📆 Si los datos son de otro día:
        if update_date.date() != now.date():
            # Si ya hicimos reset para esta fecha, no volver a procesar el JSON
            if self._last_reset_date == update_date.date():
                _LOGGER.debug(
                    "Archivo de rayos aún sin actualizar (última: %s, hoy: %s). Manteniendo datos a cero.",
                    update_date.date(),
                    now.date(),
                )
                return self._empty_state()

            # Primer reset detectado para esta fecha
            _LOGGER.debug("Los datos de rayos son de un día diferente. Reiniciando valores a cero.")
            self._last_reset_date = update_date.date()
            return self._empty_state()

        # 📅 Si los datos son actuales:
        self._last_reset_date = None  # borrar marca de reset
        region_data = self._process_region_data(existing_data.get("dades", []))
        town_data = self._process_town_data(existing_data.get("dades", []))

        return {
            "actualizado": update_date,
            "region": region_data,
            "town": town_data,
        }

    def _process_region_data(self, data_list):
        """Suma los tipos de descargas para toda la región."""
        region_counts = {
            "cc": 0,
            "cg-": 0,
            "cg+": 0
        }
        for town in data_list:
            for discharge in town.get("descarregues", []):
                if discharge["tipus"] in region_counts:
                    region_counts[discharge["tipus"]] += discharge["recompte"]

        region_counts["total"] = sum(region_counts.values())
        return region_counts

    def _process_town_data(self, data_list):
        """Encuentra y suma los tipos de descargas para un municipio específico."""
        town_counts = {
            "cc": 0,
            "cg-": 0,
            "cg+": 0
        }
        for town in data_list:
            if town["codi"] == self.town_id:
                for discharge in town.get("descarregues", []):
                    if discharge["tipus"] in town_counts:
                        town_counts[discharge["tipus"]] += discharge["recompte"]
                break  # Solo necesitamos datos de un municipio

        town_counts["total"] = sum(town_counts.values())
        return town_counts

    def _reset_data(self):
        """Resetea los datos a cero."""
        return {
            "cc": 0,
            "cg-": 0,
            "cg+": 0,
            "total": 0,
        }

    def _empty_state(self) -> Dict[str, Any]:
        """Devuelve un estado vacío (valores a cero) para los sensores."""
        now_iso = datetime.now(TIMEZONE).isoformat()
        empty = self._reset_data()
        return {
            "actualizado": now_iso,
            "region": empty,
            "town": empty,
        }

class MeteocatSunCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de sol calculados con sun.py."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        """Inicializa el coordinador de sol de Meteocat."""
        self.latitude = entry_data.get("latitude")
        self.longitude = entry_data.get("longitude")
        self.elevation = entry_data.get("altitude", 0.0)
        self.timezone_str = hass.config.time_zone or "Europe/Madrid"
        self.town_id = entry_data.get("town_id")

        # Crear ubicación para cálculos solares
        self.location = Location(LocationInfo(
            name=entry_data.get("town_name", "Municipio"),
            region="Spain",
            timezone=self.timezone_str,
            latitude=self.latitude,
            longitude=self.longitude,
            elevation=self.elevation,
        ))

        files_folder = get_storage_dir(hass, "files")
        self.sun_file = files_folder / f"sun_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Sun Coordinator",
            update_interval=DEFAULT_SUN_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """Comprueba si es necesario actualizar los datos solares (evitando escrituras innecesarias)."""
        _LOGGER.debug("☀️ Comprobando si es necesario actualizar los datos solares...")
        now = datetime.now(tz=ZoneInfo(self.timezone_str))
        today = now.date()
        tomorrow = today + timedelta(days=1)

        # === 1️⃣ Calcular eventos solares esperados ===
        events_today = self.location.sun_events(date=today, local=True)
        events_tomorrow = self.location.sun_events(date=tomorrow, local=True)

        def get_expected_sun_data():
            """Selecciona si usar los eventos de hoy o mañana según la hora actual."""
            expected = {}
            events = [
                "dawn_astronomical", "dawn_nautical", "dawn_civil",
                "sunrise", "noon", "sunset",
                "dusk_civil", "dusk_nautical", "dusk_astronomical",
                "midnight"
            ]
            for event in events:
                event_time = events_today.get(event)
                if event_time and now >= event_time:
                    expected[event] = events_tomorrow.get(event)
                    _LOGGER.debug("☀️ %s ya pasó (%s), usando valor de mañana: %s",
                                event, event_time, expected[event])
                else:
                    expected[event] = event_time
            expected["daylight_duration"] = (
                events_tomorrow["daylight_duration"]
                if expected["sunset"] == events_tomorrow["sunset"]
                else events_today["daylight_duration"]
            )
            return expected

        expected = get_expected_sun_data()

        # === 2️⃣ Cargar datos existentes del archivo ===
        existing_data = await load_json_from_file(self.sun_file) or {}
        if not existing_data or "dades" not in existing_data or not existing_data["dades"]:
            _LOGGER.debug("☀️ No hay datos solares previos. Generando nuevos datos.")
            return await self._calculate_and_save_new_data(**expected)

        dades = existing_data["dades"][0]

        try:
            saved = {k: (datetime.fromisoformat(v) if k != "daylight_duration" else v)
                    for k, v in dades.items() if k in expected}
        except Exception as e:
            _LOGGER.warning("☀️ Error al leer el archivo solar: %s", e)
            return await self._calculate_and_save_new_data(**expected)

        # === 3️⃣ Detectar cambios en eventos solares ===
        changed_events = {
            key: expected[key] for key in expected
            if saved.get(key) != expected[key]
        }

        # === 4️⃣ Calcular posición solar actual y futura (una sola vez) ===
        current_pos = self.location.sun_position(dt=now, local=True)
        future_time = now + timedelta(minutes=10)
        future_pos = self.location.sun_position(dt=future_time, local=True)

        # === 5️⃣ Función auxiliar: umbral dinámico de elevación ===
        def get_dynamic_elevation_threshold() -> float:
            sunrise = saved.get("sunrise")
            sunset = saved.get("sunset")
            noon = saved.get("noon")
            if sunrise and sunset and noon:
                sunrise_window = (sunrise - timedelta(hours=1), sunrise + timedelta(hours=1))
                sunset_window = (sunset - timedelta(hours=1), sunset + timedelta(hours=1))
                noon_window = (noon - timedelta(hours=2), noon + timedelta(hours=2))
                if sunrise_window[0] <= now <= sunrise_window[1] or sunset_window[0] <= now <= sunset_window[1]:
                    return 0.3  # Mayor sensibilidad cerca del horizonte
                elif noon_window[0] <= now <= noon_window[1]:
                    return 1.0  # Menor sensibilidad cerca del mediodía
            return 0.5  # Valor base para el resto del día

        # === 6️⃣ Función auxiliar: validez dinámica con límites ===
        def get_dynamic_validity_interval(current_elev: float, future_elev: float) -> timedelta:
            elevation_change = abs(future_elev - current_elev)
            rate_of_change = elevation_change / 10  # °/min
            _LOGGER.debug("☀️ Tasa de cambio de elevación: %.4f°/min", rate_of_change)

            if rate_of_change > 0.05:   # Amanecer/atardecer: cambio rápido
                validity = timedelta(minutes=30)
            elif rate_of_change > 0.02:  # Cambio moderado
                validity = timedelta(minutes=60)
            else:                        # Noche o mediodía: cambio lento
                validity = timedelta(minutes=120)

            # Limitar entre 15 y 180 minutos
            return max(timedelta(minutes=15), min(validity, timedelta(minutes=180)))

        SUN_POSITION_VALIDITY = get_dynamic_validity_interval(
            current_pos["elevation"], future_pos["elevation"]
        )

        # === 7️⃣ Evaluar necesidad de actualización ===
        position_needs_update = False
        last_pos_update_str = dades.get("sun_position_updated")

        if last_pos_update_str:
            try:
                last_pos_update = datetime.fromisoformat(last_pos_update_str)
                if last_pos_update.tzinfo is None:
                    last_pos_update = last_pos_update.replace(tzinfo=ZoneInfo(self.timezone_str))

                time_expired = (now - last_pos_update) > SUN_POSITION_VALIDITY
                elevation_threshold = get_dynamic_elevation_threshold()

                last_elev = dades.get("sun_elevation")
                if last_elev is not None:
                    elev_changed = abs(current_pos["elevation"] - float(last_elev)) > elevation_threshold
                else:
                    elev_changed = True

                # ✅ Ambas condiciones deben cumplirse
                position_needs_update = time_expired and elev_changed or bool(changed_events)

                _LOGGER.debug(
                    "☀️ Verificación solar -> expirado=%s (validez=%s), elevación_cambió=%s (umbral=%.2f°), eventos_cambiados=%s, actualizar=%s",
                    time_expired, SUN_POSITION_VALIDITY, elev_changed, elevation_threshold, bool(changed_events), position_needs_update
                )
            except Exception as e:
                _LOGGER.warning("☀️ Error al verificar posición solar previa: %s", e)
                position_needs_update = True
        else:
            position_needs_update = True

        # === 8️⃣ Si nada cambió, no se actualiza ===
        if not changed_events and not position_needs_update:
            _LOGGER.debug("☀️ Datos solares actuales coinciden con lo esperado. No se actualiza.")
            return existing_data

        # === 9️⃣ Actualizar si es necesario ===
        sun_pos = current_pos if position_needs_update else None
        if sun_pos:
            _LOGGER.debug("Posición solar actualizada: elev=%.2f°, azim=%.2f°, rising=%s",
                        sun_pos["elevation"], sun_pos["azimuth"], sun_pos["rising"])

        updated_data = saved.copy()
        updated_data.update(changed_events)

        # 🟡 Si hay eventos solares nuevos (por ejemplo, cambio de sunset → mañana),
        # forzar cálculo inmediato de la posición solar para evitar huecos.
        if changed_events and sun_pos is None:
            sun_pos = self.location.sun_position(dt=now, local=True)
            _LOGGER.debug("☀️ Posición solar recalculada tras cambio de eventos: elev=%.2f°, azim=%.2f°, rising=%s",
                        sun_pos["elevation"], sun_pos["azimuth"], sun_pos["rising"])

        _LOGGER.debug("☀️ Datos solares han cambiado. Actualizando: %s", changed_events)
        return await self._calculate_and_save_new_data(
            **updated_data,
            sun_pos=sun_pos,
            now=now
        )
   
    async def _calculate_and_save_new_data(
        self,
        dawn_civil: Optional[datetime] = None,
        dawn_nautical: Optional[datetime] = None,
        dawn_astronomical: Optional[datetime] = None,
        sunrise: Optional[datetime] = None,
        noon: Optional[datetime] = None,
        sunset: Optional[datetime] = None,
        dusk_civil: Optional[datetime] = None,
        dusk_nautical: Optional[datetime] = None,
        dusk_astronomical: Optional[datetime] = None,
        midnight: Optional[datetime] = None,
        daylight_duration: Optional[float] = None,
        sun_pos: Optional[dict] = None,
        now: Optional[datetime] = None,
    ) -> dict:
        """Guarda los datos solares pasados, usando valores existentes si no se proporcionan."""
        try:
            now = datetime.now(tz=ZoneInfo(self.timezone_str))
            today = now.date()

            # Cargar datos existentes para preservar valores no cambiados
            existing_data = await load_json_from_file(self.sun_file) or {}
            existing_dades = existing_data.get("dades", [{}])[0] if existing_data else {}

            # Convertir valores existentes a tipos adecuados
            try:
                saved = {
                    "dawn_civil": datetime.fromisoformat(existing_dades["dawn_civil"]) if existing_dades.get("dawn_civil") else None,
                    "dawn_nautical": datetime.fromisoformat(existing_dades["dawn_nautical"]) if existing_dades.get("dawn_nautical") else None,
                    "dawn_astronomical": datetime.fromisoformat(existing_dades["dawn_astronomical"]) if existing_dades.get("dawn_astronomical") else None,
                    "sunrise": datetime.fromisoformat(existing_dades["sunrise"]) if existing_dades.get("sunrise") else None,
                    "noon": datetime.fromisoformat(existing_dades["noon"]) if existing_dades.get("noon") else None,
                    "sunset": datetime.fromisoformat(existing_dades["sunset"]) if existing_dades.get("sunset") else None,
                    "dusk_civil": datetime.fromisoformat(existing_dades["dusk_civil"]) if existing_dades.get("dusk_civil") else None,
                    "dusk_nautical": datetime.fromisoformat(existing_dades["dusk_nautical"]) if existing_dades.get("dusk_nautical") else None,
                    "dusk_astronomical": datetime.fromisoformat(existing_dades["dusk_astronomical"]) if existing_dades.get("dusk_astronomical") else None,
                    "midnight": datetime.fromisoformat(existing_dades["midnight"]) if existing_dades.get("midnight") else None,
                    "daylight_duration": existing_dades.get("daylight_duration"),
                }
            except Exception as e:
                _LOGGER.warning("☀️ Error al leer datos existentes, recalculando todo: %s", e)
                saved = {}

            # Si no se proporcionan valores, usar los existentes o calcularlos
            if not any([dawn_civil, dawn_nautical, dawn_astronomical, sunrise, noon, sunset, dusk_civil, dusk_nautical, dusk_astronomical, midnight]):
                events = self.location.sun_events(date=today, local=True)
                dawn_civil = events["dawn_civil"]
                dawn_nautical = events["dawn_nautical"]
                dawn_astronomical = events["dawn_astronomical"]
                sunrise = events["sunrise"]
                noon = events["noon"]
                sunset = events["sunset"]
                dusk_civil = events["dusk_civil"]
                dusk_nautical = events["dusk_nautical"]
                dusk_astronomical = events["dusk_astronomical"]
                midnight = events["midnight"]
                daylight_duration = events["daylight_duration"]
            else:
                # Usar valores proporcionados, o los existentes si no se proporcionan
                dawn_civil = dawn_civil if dawn_civil is not None else saved.get("dawn_civil")
                dawn_nautical = dawn_nautical if dawn_nautical is not None else saved.get("dawn_nautical")
                dawn_astronomical = dawn_astronomical if dawn_astronomical is not None else saved.get("dawn_astronomical")
                sunrise = sunrise if sunrise is not None else saved.get("sunrise")
                noon = noon if noon is not None else saved.get("noon")
                sunset = sunset if sunset is not None else saved.get("sunset")
                dusk_civil = dusk_civil if dusk_civil is not None else saved.get("dusk_civil")
                dusk_nautical = dusk_nautical if dusk_nautical is not None else saved.get("dusk_nautical")
                dusk_astronomical = dusk_astronomical if dusk_astronomical is not None else saved.get("dusk_astronomical")
                midnight = midnight if midnight is not None else saved.get("midnight")
                daylight_duration = daylight_duration if daylight_duration is not None else saved.get("daylight_duration")

                # Recalcular daylight_duration si sunrise o sunset han cambiado
                if sunrise and sunset and (sunrise != saved.get("sunrise") or sunset != saved.get("sunset")):
                    daylight_duration = (sunset - sunrise).total_seconds() / 3600 if sunrise and sunset else None

            # CONSTRUIR DADES
            dades_dict = {
                "dawn_civil": dawn_civil.isoformat() if dawn_civil else None,
                "dawn_nautical": dawn_nautical.isoformat() if dawn_nautical else None,
                "dawn_astronomical": dawn_astronomical.isoformat() if dawn_astronomical else None,
                "sunrise": sunrise.isoformat() if sunrise else None,
                "noon": noon.isoformat() if noon else None,
                "sunset": sunset.isoformat() if sunset else None,
                "dusk_civil": dusk_civil.isoformat() if dusk_civil else None,
                "dusk_nautical": dusk_nautical.isoformat() if dusk_nautical else None,
                "dusk_astronomical": dusk_astronomical.isoformat() if dusk_astronomical else None,
                "midnight": midnight.isoformat() if midnight else None,
                "daylight_duration": daylight_duration,
            }

            # AÑADIR POSICIÓN SOLAR
            if sun_pos:
                dades_dict.update({
                    "sun_elevation": round(sun_pos["elevation"], 2),
                    "sun_azimuth": round(sun_pos["azimuth"], 2),
                    "sun_horizon_position": sun_pos["horizon_position"],
                    "sun_rising": sun_pos["rising"],
                    "sun_position_updated": now.isoformat()
                })

            # GUARDAR
            data_with_timestamp = {
                "actualitzat": {"dataUpdate": now.isoformat()},
                "dades": [dades_dict],
            }

            await save_json_to_file(data_with_timestamp, self.sun_file)
            _LOGGER.info("Archivo solar actualizado (eventos: %s, posición: %s)",
                         bool(dawn_civil is not None), bool(sun_pos))

            return data_with_timestamp

        except Exception as err:
            _LOGGER.exception("Error al calcular/guardar los datos solares: %s", err)
            
            # === FALLBACK SEGURO ===
            cached = await load_json_from_file(self.sun_file)
            if cached and "actualitzat" in cached and "dades" in cached and cached["dades"]:
                update_str = cached["actualitzat"]["dataUpdate"]
                try:
                    update_dt = datetime.fromisoformat(update_str)
                    local_dt = update_dt.astimezone(ZoneInfo(self.timezone_str))
                    display_time = local_dt.strftime("%d/%m/%Y %H:%M")
                except (ValueError, TypeError):
                    display_time = update_str.split("T")[0]
                
                sunrise = cached["dades"][0].get("sunrise", "unknown")
                sunset = cached["dades"][0].get("sunset", "unknown")
                
                _LOGGER.warning(
                    "SOL: Cálculo falló → usando caché local:\n"
                    "   • Archivo: %s\n"
                    "   • Última actualización: %s\n"
                    "   • Amanecer: %s\n"
                    "   • Atardecer: %s",
                    self.sun_file.name,
                    display_time,
                    sunrise.split("T")[1][:5] if "T" in sunrise else sunrise,
                    sunset.split("T")[1][:5] if "T" in sunset else sunset
                )
                
                self.async_set_updated_data(cached)
                return cached
            
            _LOGGER.error("SOL: No hay caché disponible. Sin datos solares.")
            self.async_set_updated_data({})
            return {}

class MeteocatSunFileCoordinator(BaseFileCoordinator):
    """Coordinator para manejar la actualización de los datos de sol desde sun_{town_id}.json."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador de sol desde archivo.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración de la entrada.
        """
        self.town_id = entry_data["town_id"]
        self.timezone_str = hass.config.time_zone or "Europe/Madrid"

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.sun_file = files_folder / f"sun_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            name=f"{DOMAIN} Sun File Coordinator",
            update_interval=DEFAULT_SUN_FILE_UPDATE_INTERVAL,
            min_delay=1.0,  # Rango predeterminado
            max_delay=2.0,  # Rango predeterminado
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Lee el archivo y resetea si el primer evento (dawn_astronomical) es de ayer."""
        # 🔸 Añadimos un pequeño desfase aleatorio (1 a 2 segundos) basados en el BaseFileCoordinator
        await self._apply_random_delay()

        try:
            data = await load_json_from_file(self.sun_file)
            if not data or "dades" not in data or not data["dades"]:
                _LOGGER.warning("Archivo solar vacío: %s", self.sun_file)
                return self._reset_data()

            dades = data["dades"][0]
            update_str = data.get("actualitzat", {}).get("dataUpdate")
            update_dt = datetime.fromisoformat(update_str) if update_str else None
            now = datetime.now(ZoneInfo(self.timezone_str))
            today = now.date()

            # === PRIMER EVENTO: dawn_astronomical ===
            dawn_astro_str = dades.get("dawn_astronomical")
            if not dawn_astro_str:
                _LOGGER.debug("No hay 'dawn_astronomical'. Forzando reset.")
                return self._reset_data()

            try:
                dawn_astro_dt = datetime.fromisoformat(dawn_astro_str)
                event_date = dawn_astro_dt.date()
            except ValueError as e:
                _LOGGER.warning("Formato inválido en dawn_astronomical: %s → %s", dawn_astro_str, e)
                return self._reset_data()

            # === ¿Es de un día anterior a ayer? ===
            if event_date < (today - timedelta(days=1)):
                _LOGGER.info(
                    "Datos solares muy antiguos: dawn_astronomical es del %s (hoy es %s). Reiniciando.",
                    event_date, today
                )
                return self._reset_data()

            # 🟢 Si el evento es de mañana, mantener datos actuales (no resetear)
            if event_date > today:
                _LOGGER.debug(
                    "Datos solares son de mañana (%s). Manteniendo valores actuales hasta próxima actualización.",
                    event_date
                )

            # === DATOS VÁLIDOS DEL DÍA ACTUAL ===
            result = {
                "actualizado": update_dt.isoformat() if update_dt else now.isoformat(),
                "dawn_civil": dades.get("dawn_civil"),
                "dawn_nautical": dades.get("dawn_nautical"),
                "dawn_astronomical": dawn_astro_str,
                "sunrise": dades.get("sunrise"),
                "noon": dades.get("noon"),
                "sunset": dades.get("sunset"),
                "dusk_civil": dades.get("dusk_civil"),
                "dusk_nautical": dades.get("dusk_nautical"),
                "dusk_astronomical": dades.get("dusk_astronomical"),
                "midnight": dades.get("midnight"),
                "daylight_duration": dades.get("daylight_duration"),
                "sun_elevation": dades.get("sun_elevation"),
                "sun_azimuth": dades.get("sun_azimuth"),
                "sun_horizon_position": dades.get("sun_horizon_position"),
                "sun_rising": dades.get("sun_rising"),
                "sun_position_updated": dades.get("sun_position_updated"),
            }

            _LOGGER.debug("Datos solares válidos para hoy (%s)", today)
            return result

        except Exception as e:
            _LOGGER.error("Error crítico en SunFileCoordinator: %s", e)
            return self._reset_data()

    def _reset_data(self):
        """Resetea los datos a valores nulos."""
        now = datetime.now(ZoneInfo(self.timezone_str)).isoformat()
        return {
            "actualizado": now,
            "sunrise": None,
            "sunset": None,
            "noon": None,
            "dawn_civil": None,
            "dusk_civil": None,
            "dawn_nautical": None,
            "dusk_nautical": None,
            "dawn_astronomical": None,
            "dusk_astronomical": None,
            "midnight": None,
            "daylight_duration": None,
            "sun_elevation": None,
            "sun_azimuth": None,
            "sun_horizon_position": None,
            "sun_rising": None,
            "sun_position_updated": now,
        }

class MeteocatMoonCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de la luna desde moon.py."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        self.latitude = entry_data.get("latitude")
        self.longitude = entry_data.get("longitude")
        self.timezone_str = hass.config.time_zone or "Europe/Madrid"
        self.town_id = entry_data.get("town_id")

        self.location = LocationInfo(
            name=entry_data.get("town_name", "Municipio"),
            region="Spain",
            timezone=self.timezone_str,
            latitude=self.latitude,
            longitude=self.longitude,
        )

        files_folder = get_storage_dir(hass, "files")
        self.moon_file = files_folder / f"moon_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Moon Coordinator",
            update_interval=DEFAULT_MOON_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """Determina si los datos de la luna son válidos o requieren actualización."""
        _LOGGER.debug("🌙 Iniciando actualización de datos de la luna...")
        now = datetime.now(tz=ZoneInfo(self.timezone_str))
        existing_data = await load_json_from_file(self.moon_file) or {}

        # 🟡 Si no hay datos previos o JSON incompleto → calcular todo para hoy
        if (
            not existing_data
            or "dades" not in existing_data
            or not existing_data["dades"]
            or "actualitzat" not in existing_data
            or "dataUpdate" not in existing_data["actualitzat"]
        ):
            _LOGGER.warning("🌙 Datos previos incompletos o ausentes: calculando todos los datos para hoy.")
            return await self._calculate_and_save_new_data(today_only=True, existing_data=existing_data)

        dades = existing_data["dades"][0]
        last_lunar_update_date_str = existing_data["actualitzat"].get("last_lunar_update_date")
        last_lunar_update_date = (
            datetime.fromisoformat(f"{last_lunar_update_date_str}T00:00:00").date()
            if last_lunar_update_date_str
            else now.date() - timedelta(days=1)  # Fallback
        )

        # 🟢 Comprobar si los datos son obsoletos (last_lunar_update_date y eventos antiguos)
        try:
            moonrise_str = dades.get("moonrise")
            moonset_str = dades.get("moonset")
            moonrise = datetime.fromisoformat(moonrise_str) if moonrise_str else None
            moonset = datetime.fromisoformat(moonset_str) if moonset_str else None

            # Si last_lunar_update_date es de un día anterior y los eventos (si existen) también lo son
            events_are_old = (
                (moonrise is None or moonrise.date() < now.date())
                and (moonset is None or moonset.date() < now.date())
            )
            if last_lunar_update_date < now.date() and events_are_old:
                _LOGGER.debug(
                    "🌙 Datos obsoletos: last_lunar_update_date=%s, moonrise=%s, moonset=%s. Calculando para hoy.",
                    last_lunar_update_date, moonrise, moonset
                )
                return await self._calculate_and_save_new_data(today_only=True, existing_data=existing_data)
        except Exception as e:
            _LOGGER.warning("🌙 Error interpretando fechas previas: %s", e)
            return await self._calculate_and_save_new_data(today_only=True, existing_data=existing_data)

        # 🟢 Comprobar si los datos lunares necesitan actualización
        if now.date() > last_lunar_update_date:
            _LOGGER.debug("🌙 Fecha actual superior a last_lunar_update_date: actualizando datos lunares.")
            return await self._calculate_and_save_new_data(
                update_type="update_lunar_data",
                existing_data=existing_data
            )

        _LOGGER.debug(
            "🌙 Estado actual → now=%s | moonrise=%s | moonset=%s",
            now.isoformat(), moonrise, moonset
        )

        # Lógica para eventos moonrise y moonset
        if moonrise is None and moonset is None:
            _LOGGER.debug("🌙 Ambos eventos None: verificando si datos son actuales.")
            if last_lunar_update_date == now.date():
                _LOGGER.debug("🌙 Datos de hoy sin eventos: no se actualiza.")
                return {"actualizado": existing_data["actualitzat"]["dataUpdate"]}
            return await self._calculate_and_save_new_data(today_only=True, existing_data=existing_data)

        elif moonrise is None:
            _LOGGER.debug("🌙 No moonrise: tratando moonset como único evento.")
            if now < moonset:
                _LOGGER.debug("🌙 Antes del moonset: no se actualiza.")
                return {"actualizado": existing_data["actualitzat"]["dataUpdate"]}
            else:
                _LOGGER.debug("🌙 Después del moonset: actualizar moonset para mañana.")
                return await self._calculate_and_save_new_data(update_type="update_set_tomorrow", existing_data=existing_data)

        elif moonset is None:
            _LOGGER.debug("🌙 No moonset: tratando moonrise como único evento.")
            if now < moonrise:
                _LOGGER.debug("🌙 Antes del moonrise: no se actualiza.")
                return {"actualizado": existing_data["actualitzat"]["dataUpdate"]}
            else:
                _LOGGER.debug("🌙 Después del moonrise: actualizar moonrise para mañana.")
                return await self._calculate_and_save_new_data(update_type="update_rise_tomorrow", existing_data=existing_data)

        else:
            min_event = min(moonrise, moonset)
            max_event = max(moonrise, moonset)
            first_is_rise = (min_event == moonrise)

            if now < min_event:
                _LOGGER.debug("🌙 Momento actual antes del primer evento → no se actualiza nada.")
                return {"actualizado": existing_data["actualitzat"]["dataUpdate"]}

            elif now < max_event:
                if first_is_rise:
                    _LOGGER.debug("🌙 Después del moonrise pero antes del moonset → actualizar solo moonrise para mañana.")
                    return await self._calculate_and_save_new_data(update_type="update_rise_tomorrow", existing_data=existing_data)
                else:
                    _LOGGER.debug("🌙 Después del moonset pero antes del moonrise → actualizar solo moonset para mañana.")
                    return await self._calculate_and_save_new_data(update_type="update_set_tomorrow", existing_data=existing_data)

            else:
                _LOGGER.debug("🌙 Después de ambos eventos → actualizar moonrise y moonset para mañana.")
                return await self._calculate_and_save_new_data(update_type="update_both_tomorrow", existing_data=existing_data)

    async def _calculate_and_save_new_data(self, today_only: bool = False, update_type: str = None, existing_data: dict = None):
        """Calcula y guarda nuevos datos de la luna según el tipo de actualización."""
        try:
            now = datetime.now(tz=ZoneInfo(self.timezone_str))
            tz = ZoneInfo(self.timezone_str)
            today = now.date()
            next_day = today + timedelta(days=1)
            next_next_day = today + timedelta(days=2)

            _LOGGER.debug("🌙 Calculando nuevos datos (update_type=%s)...", update_type)

            # 🟣 Calcular fase e iluminación, distancia y diámetro angular
            moon_phase_value = moon_phase(today)
            moon_day_today = moon_day(today)
            lunation = lunation_number(today)
            illum_percentage = round(illuminated_percentage(today), 2)
            distance = round(moon_distance(today), 0)
            angular_diameter = round(moon_angular_diameter(today), 2)
            moon_phase_name = get_moon_phase_name(today)
            lunation_duration = get_lunation_duration(today)

            # Inicializar moonrise_final y moonset_final
            moonrise_final = None
            moonset_final = None

            # 🟢 Caso: actualizar solo datos lunares
            if update_type == "update_lunar_data":
                dades = existing_data.get("dades", [{}])[0]
                moonrise_str = dades.get("moonrise")
                moonset_str = dades.get("moonset")
                moonrise_final = datetime.fromisoformat(moonrise_str) if moonrise_str else None
                moonset_final = datetime.fromisoformat(moonset_str) if moonset_str else None

                # Si faltan moonrise o moonset, calcular de fallback
                if moonrise_final is None or moonset_final is None:
                    _LOGGER.debug("🌙 Falta algún evento lunar, calculando de fallback.")
                    moonrise_today, moonset_today = moon_rise_set(self.latitude, self.longitude, today)
                    moonrise_tomorrow, moonset_tomorrow = moon_rise_set(self.latitude, self.longitude, next_day)
                    moonrise_next_tomorrow, moonset_next_tomorrow = moon_rise_set(self.latitude, self.longitude, next_next_day)

                    # Convertir a zona local
                    events = {
                        "moonrise_today": moonrise_today,
                        "moonset_today": moonset_today,
                        "moonrise_tomorrow": moonrise_tomorrow,
                        "moonset_tomorrow": moonset_tomorrow,
                        "moonrise_next_tomorrow": moonrise_next_tomorrow,
                        "moonset_next_tomorrow": moonset_next_tomorrow,
                    }
                    for key, val in events.items():
                        if val:
                            events[key] = val.astimezone(tz)
                    moonrise_today, moonset_today, moonrise_tomorrow, moonset_tomorrow, moonrise_next_tomorrow, moonset_next_tomorrow = (
                        events["moonrise_today"],
                        events["moonset_today"],
                        events["moonrise_tomorrow"],
                        events["moonset_tomorrow"],
                        events["moonrise_next_tomorrow"],
                        events["moonset_next_tomorrow"],
                    )

                    # Seleccionar los eventos más próximos disponibles
                    moonrise_final = moonrise_final or (moonrise_today if moonrise_today else (moonrise_tomorrow if moonrise_tomorrow else moonrise_next_tomorrow))
                    moonset_final = moonset_final or (moonset_today if moonset_today else (moonset_tomorrow if moonset_tomorrow else moonset_next_tomorrow))
                    _LOGGER.debug("🌙 Fallback: usando moonrise=%s y moonset=%s", moonrise_final, moonset_final)

            else:
                # Calcular eventos lunares
                moonrise_today, moonset_today = moon_rise_set(self.latitude, self.longitude, today)
                moonrise_tomorrow, moonset_tomorrow = moon_rise_set(self.latitude, self.longitude, next_day)
                moonrise_next_tomorrow, moonset_next_tomorrow = moon_rise_set(self.latitude, self.longitude, next_next_day)

                # Convertir a zona local
                events = {
                    "moonrise_today": moonrise_today,
                    "moonset_today": moonset_today,
                    "moonrise_tomorrow": moonrise_tomorrow,
                    "moonset_tomorrow": moonset_tomorrow,
                    "moonrise_next_tomorrow": moonrise_next_tomorrow,
                    "moonset_next_tomorrow": moonset_next_tomorrow,
                }
                for key, val in events.items():
                    if val:
                        events[key] = val.astimezone(tz)
                moonrise_today, moonset_today, moonrise_tomorrow, moonset_tomorrow, moonrise_next_tomorrow, moonset_next_tomorrow = (
                    events["moonrise_today"],
                    events["moonset_today"],
                    events["moonrise_tomorrow"],
                    events["moonset_tomorrow"],
                    events["moonrise_next_tomorrow"],
                    events["moonset_next_tomorrow"],
                )

                # 🧭 Determinar valores finales según el contexto
                if today_only:
                    moonrise_final = moonrise_today
                    moonset_final = moonset_today
                elif update_type == "update_set_tomorrow":
                    if existing_data and "dades" in existing_data and existing_data["dades"] and "moonrise" in existing_data["dades"][0]:
                        moonrise_str = existing_data["dades"][0]["moonrise"]
                        moonrise_final = datetime.fromisoformat(moonrise_str) if moonrise_str else None
                    else:
                        moonrise_final = moonrise_today
                    moonset_final = moonset_tomorrow if moonset_tomorrow else moonset_next_tomorrow
                    _LOGGER.debug("🌙 Actualizado moonset para mañana: %s (manteniendo moonrise: %s)", moonset_final, moonrise_final)
                elif update_type == "update_rise_tomorrow":
                    if existing_data and "dades" in existing_data and existing_data["dades"] and "moonset" in existing_data["dades"][0]:
                        moonset_str = existing_data["dades"][0]["moonset"]
                        moonset_final = datetime.fromisoformat(moonset_str) if moonset_str else None
                    else:
                        moonset_final = moonset_today
                    moonrise_final = moonrise_tomorrow if moonrise_tomorrow else moonrise_next_tomorrow
                    _LOGGER.debug("🌙 Actualizado moonrise para mañana: %s (manteniendo moonset: %s)", moonrise_final, moonset_final)
                elif update_type == "update_both_tomorrow":
                    moonrise_final = moonrise_tomorrow if moonrise_tomorrow else moonrise_next_tomorrow
                    moonset_final = moonset_tomorrow if moonset_tomorrow else moonset_next_tomorrow
                    _LOGGER.debug("🌙 Actualizados moonrise y moonset para mañana: %s / %s", moonrise_final, moonset_final)
                else:
                    moonrise_final = moonrise_today
                    moonset_final = moonset_today

                # Si algún evento final es None, intentar con el del día siguiente o el posterior
                if moonrise_final is None:
                    moonrise_final = moonrise_tomorrow if moonrise_tomorrow else moonrise_next_tomorrow
                    if moonrise_final:
                        _LOGGER.debug("🌙 Moonrise era None: usando el del día siguiente o posterior: %s", moonrise_final)
                if moonset_final is None:
                    moonset_final = moonset_tomorrow if moonset_tomorrow else moonset_next_tomorrow
                    if moonset_final:
                        _LOGGER.debug("🌙 Moonset era None: usando el del día siguiente o posterior: %s", moonset_final)

            data_with_timestamp = {
                "actualitzat": {
                    "dataUpdate": now.isoformat(),
                    # 🟢 Determinar last_lunar_update_date de forma legible
                    "last_lunar_update_date": (
                        today.isoformat()
                        if update_type in ("update_lunar_data", None) or today_only
                        else existing_data.get("actualitzat", {}).get("last_lunar_update_date", today.isoformat())
                    ),
                },
                "dades": [
                    {
                        "moon_day": moon_day_today,
                        "moon_phase": round(moon_phase_value, 2),
                        "moon_phase_name": moon_phase_name,
                        "illuminated_percentage": illum_percentage,
                        "moon_distance": distance,
                        "moon_angular_diameter": angular_diameter,
                        "lunation": lunation,
                        "lunation_duration": lunation_duration,
                        "moonrise": moonrise_final.isoformat() if moonrise_final else None,
                        "moonset": moonset_final.isoformat() if moonset_final else None,
                    }
                ],
            }

            await save_json_to_file(data_with_timestamp, self.moon_file)
            _LOGGER.debug("🌙 Datos de luna guardados correctamente → %s", data_with_timestamp)
            return {"actualizado": data_with_timestamp["actualitzat"]["dataUpdate"]}

        except Exception as err:
            _LOGGER.exception("Error al calcular datos de la luna: %s", err)
            
            # === FALLBACK SEGURO ===
            cached_data = await load_json_from_file(self.moon_file)
            if cached_data and "actualitzat" in cached_data and "dades" in cached_data:
                update_str = cached_data["actualitzat"]["dataUpdate"]
                try:
                    update_dt = datetime.fromisoformat(update_str)
                    local_dt = update_dt.astimezone(ZoneInfo(self.timezone_str))
                    display_time = local_dt.strftime("%d/%m/%Y %H:%M")
                except (ValueError, TypeError):
                    display_time = update_str.split("T")[0]
                
                moonrise = cached_data["dades"][0].get("moonrise", "unknown")
                moonset = cached_data["dades"][0].get("moonset", "unkwnown")
                phase = cached_data["dades"][0].get("moon_phase_name", "unknown")
                
                _LOGGER.warning(
                    "LUNA: Cálculo falló → usando caché local:\n"
                    "   • Archivo: %s\n"
                    "   • Última actualización: %s\n"
                    "   • Fase: %s\n"
                    "   • Salida: %s\n"
                    "   • Atardecer: %s",
                    self.moon_file.name,
                    display_time,
                    phase.title().replace("_", " "),
                    moonrise.split("T")[1][:5] if "T" in moonrise else "—",
                    moonset.split("T")[1][:5] if "T" in moonset else "—"
                )
                
                self.async_set_updated_data({
                    "actualizado": cached_data["actualitzat"]["dataUpdate"]
                })
                return {"actualizado": cached_data["actualitzat"]["dataUpdate"]}
            
            _LOGGER.error("LUNA: No hay caché disponible. Sin datos lunares.")
            self.async_set_updated_data({})
            return {}

class MeteocatMoonFileCoordinator(BaseFileCoordinator):
    """Coordinator para manejar la actualización de los datos de la luna desde moon_{town_id}.json."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        self.town_id = entry_data["town_id"]
        self.timezone_str = hass.config.time_zone or "Europe/Madrid"

        files_folder = get_storage_dir(hass, "files")
        self.moon_file = files_folder / f"moon_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            name=f"{DOMAIN} Moon File Coordinator",
            update_interval=DEFAULT_MOON_FILE_UPDATE_INTERVAL,
            min_delay=1.0,  # Rango predeterminado
            max_delay=2.0,  # Rango predeterminado
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de la luna desde el archivo JSON y verifica si siguen siendo válidos."""
        # 🔸 Añadimos un pequeño desfase aleatorio (1 a 2 segundos) basados en el BaseFileCoordinator
        await self._apply_random_delay()
        
        existing_data = await load_json_from_file(self.moon_file)

        if not existing_data or "dades" not in existing_data or not existing_data["dades"]:
            _LOGGER.warning("No se encontraron datos en %s.", self.moon_file)
            return {
                "actualizado": datetime.now(ZoneInfo(self.timezone_str)).isoformat(),
                "last_lunar_update_date": None,
                "moon_day": None,
                "moon_phase": None,
                "moon_phase_name": None,
                "illuminated_percentage": None,
                "moon_distance": None,
                "moon_angular_diameter": None,
                "lunation": None,
                "lunation_duration": None,
                "moonrise": None,
                "moonset": None,
            }

        dades = existing_data["dades"][0]
        moonrise_str = dades.get("moonrise")
        moonset_str = dades.get("moonset")
        update_date_str = existing_data.get("actualitzat", {}).get("dataUpdate", "")
        last_lunar_update_date_str = existing_data.get("actualitzat", {}).get("last_lunar_update_date", "")

        update_date = (
            datetime.fromisoformat(update_date_str)
            if update_date_str
            else datetime.now(ZoneInfo(self.timezone_str))
        )

        # Simplemente devolvemos los datos cargados, aunque estén desfasados
        return {
            "actualizado": update_date.isoformat(),
            "last_lunar_update_date": last_lunar_update_date_str,
            "moon_day": dades.get("moon_day"),
            "moon_phase": dades.get("moon_phase"),
            "moon_phase_name": dades.get("moon_phase_name"),
            "illuminated_percentage": dades.get("illuminated_percentage"),
            "moon_distance": dades.get("moon_distance"),
            "moon_angular_diameter": dades.get("moon_angular_diameter"),
            "lunation": dades.get("lunation"),
            "lunation_duration": dades.get("lunation_duration"),
            "moonrise": moonrise_str,
            "moonset": moonset_str,
        }
