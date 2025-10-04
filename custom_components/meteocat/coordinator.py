from __future__ import annotations

import json
import aiofiles
import logging
import asyncio
import unicodedata
from pathlib import Path
from astral.sun import sun
from .moon import moon_phase, moon_rise_set
from astral import LocationInfo
from datetime import date, datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from typing import Dict, Any

from homeassistant.core import HomeAssistant, EVENT_HOMEASSISTANT_START
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.weather import Forecast

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
    DEFAULT_ALERT_VALIDITY_TIME,
    DEFAULT_QUOTES_VALIDITY_TIME,
    ALERT_VALIDITY_MULTIPLIER_100,
    ALERT_VALIDITY_MULTIPLIER_200,
    ALERT_VALIDITY_MULTIPLIER_500,
    ALERT_VALIDITY_MULTIPLIER_DEFAULT,
    DEFAULT_LIGHTNING_VALIDITY_TIME,
    DEFAULT_LIGHTNING_VALIDITY_HOURS,
    DEFAULT_LIGHTNING_VALIDITY_MINUTES
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
                _LOGGER.exception(
                    "No se pudo inicializar el dispositivo (Station ID: %s): %s",
                    self.station_id,
                    err,
                )
                raise
            else:
                _LOGGER.exception(
                    "Error inesperado al obtener datos de los sensores (Station ID: %s): %s",
                    self.station_id,
                    err,
                )

        # Cargar datos en caché si la API falla
        cached_data = await load_json_from_file(self.station_file)
        if cached_data:
            _LOGGER.warning("Usando datos en caché para la estación %s.", self.station_id)
            return cached_data

        _LOGGER.error("No se pudo obtener datos actualizados ni cargar datos en caché.")
        return None

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

    async def is_uvi_data_valid(self) -> dict | None:
        """Comprueba si el archivo JSON contiene datos válidos para el día actual y devuelve los datos si son válidos."""
        try:
            if not self.uvi_file.exists():
                _LOGGER.info("El archivo %s no existe. Se considerará inválido.", self.uvi_file)
                return None

            async with aiofiles.open(self.uvi_file, "r", encoding="utf-8") as file:
                content = await file.read()
                data = json.loads(content)

            # Validaciones de estructura
            if not isinstance(data, dict) or "uvi" not in data or not isinstance(data["uvi"], list) or not data["uvi"]:
                _LOGGER.warning("Estructura inválida o sin datos en %s: %s", self.uvi_file, data)
                return None

            # Obtener la fecha del primer elemento con protección
            try:
                first_date = datetime.strptime(data["uvi"][0].get("date"), "%Y-%m-%d").date()
            except Exception as exc:
                _LOGGER.warning("Fecha inválida en %s: %s", self.uvi_file, exc)
                return None

            today = datetime.now(timezone.utc).date()
            current_time = datetime.now(timezone.utc).time()

            _LOGGER.debug(
                "Validando datos UVI en %s: Fecha de hoy: %s, Fecha del primer elemento: %s, Hora actual: %s",
                self.uvi_file,
                today,
                first_date,
                current_time,
            )

            if (today - first_date).days > DEFAULT_VALIDITY_DAYS and current_time >= time(DEFAULT_VALIDITY_HOURS, DEFAULT_VALIDITY_MINUTES):
                _LOGGER.info("Los datos en %s son antiguos. Se procederá a llamar a la API.", self.uvi_file)
                return None

            _LOGGER.info("Los datos en %s son válidos. Se usarán sin llamar a la API.", self.uvi_file)
            return data

        except json.JSONDecodeError:
            _LOGGER.error("El archivo %s contiene JSON inválido o está corrupto.", self.uvi_file)
            return None
        except Exception as e:
            _LOGGER.error("Error al validar el archivo JSON del índice UV: %s", e)
            return None

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de UVI desde la API de Meteocat."""
        try:
            valid_data = await self.is_uvi_data_valid()
            if valid_data:
                _LOGGER.debug("Los datos del índice UV están actualizados. No se realiza llamada a la API.")
                return valid_data["uvi"]

            data = await asyncio.wait_for(
                self.meteocat_uvi_data.get_uvi_index(self.town_id),
                timeout=30,
            )
            _LOGGER.debug("Datos UVI obtenidos desde API: %s", data)

            await _update_quotes(self.hass, "Prediccio")

            if not isinstance(data, dict) or "uvi" not in data or not isinstance(data["uvi"], list):
                _LOGGER.error("Formato inválido: se esperaba un dict con 'uvi' -> %s", data)
                raise ValueError("Formato de datos inválido")

            await save_json_to_file(data, self.uvi_file)
            return data["uvi"]

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

        # Fallback a caché en disco
        cached_data = await load_json_from_file(self.uvi_file)
        if cached_data:
            _LOGGER.warning("Usando datos en caché para la ciudad %s.", self.town_id)
            return cached_data.get("uvi", [])
        _LOGGER.error("No se pudo obtener datos UVI ni cargar caché.")
        return None


class MeteocatUviFileCoordinator(DataUpdateCoordinator):
    """Coordinator to read and process UV data from a file."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        self.town_id = entry_data["town_id"]

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Uvi File Coordinator",
            update_interval=DEFAULT_UVI_SENSOR_UPDATE_INTERVAL,
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self._file_path = files_folder / f"uvi_{self.town_id.lower()}_data.json"

    async def _async_update_data(self):
        """Read and process UV data for the current hour from the file asynchronously."""
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

    async def validate_forecast_data(self, file_path: Path) -> dict:
        """Valida y retorna datos de predicción si son válidos."""
        if not file_path.exists():
            _LOGGER.info("El archivo %s no existe. Se considerará inválido.", file_path)
            return None
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            # Obtener la fecha del primer día
            first_date = datetime.fromisoformat(data["dies"][0]["data"].rstrip("Z")).date()
            today = datetime.now(timezone.utc).date()
            current_time = datetime.now(timezone.utc).time()

            # Log detallado
            _LOGGER.info(
                "Validando datos en %s: Fecha de hoy: %s, Fecha del primer elemento: %s",
                file_path,
                today,
                first_date,
                current_time,
            )

            # Verificar si la antigüedad es mayor a un día
            if (today - first_date).days > DEFAULT_VALIDITY_DAYS and current_time >= time(
                DEFAULT_VALIDITY_HOURS, DEFAULT_VALIDITY_MINUTES
            ):
                _LOGGER.info(
                    "Los datos en %s son antiguos. Se procederá a llamar a la API.",
                    file_path,
                )
                return None
            _LOGGER.info("Los datos en %s son válidos. Se usarán sin llamar a la API.", file_path)
            return data
        except Exception as e:
            _LOGGER.warning("Error validando datos en %s: %s", file_path, e)
            return None

    async def _fetch_and_save_data(self, api_method, file_path: Path) -> dict:
        """Obtiene datos de la API y los guarda en un archivo JSON."""
        try:
            data = await asyncio.wait_for(api_method(self.town_id), timeout=30)

            # Procesar los datos antes de guardarlos
            for day in data.get("dies", []):
                for var, details in day.get("variables", {}).items():
                    if (
                        var == "precipitacio"
                        and isinstance(details.get("valor"), str)
                        and details["valor"].startswith("-")
                    ):
                        details["valor"] = "0.0"

            await save_json_to_file(data, file_path)

            # Actualizar cuotas dependiendo del tipo de predicción
            if api_method.__name__ in ("get_prediccion_horaria", "get_prediccion_diaria"):
                await _update_quotes(self.hass, "Prediccio")

            return data
        except Exception as err:
            _LOGGER.error(f"Error al obtener datos de la API para {file_path}: {err}")
            raise

    async def _async_update_data(self) -> dict:
        """Actualiza los datos de predicción horaria y diaria."""
        try:
            # Validar o actualizar datos horarios
            hourly_data = await self.validate_forecast_data(self.hourly_file)
            if not hourly_data:
                hourly_data = await self._fetch_and_save_data(
                    self.meteocat_forecast.get_prediccion_horaria, self.hourly_file
                )

            # Validar o actualizar datos diarios
            daily_data = await self.validate_forecast_data(self.daily_file)
            if not daily_data:
                daily_data = await self._fetch_and_save_data(
                    self.meteocat_forecast.get_prediccion_diaria, self.daily_file
                )

            return {"hourly": hourly_data, "daily": daily_data}

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

        # Si ocurre un error, intentar cargar datos desde los archivos locales
        hourly_cache = await load_json_from_file(self.hourly_file) or {}
        daily_cache = await load_json_from_file(self.daily_file) or {}

        _LOGGER.warning(
            "Cargando datos desde caché para %s. Datos horarios: %s, Datos diarios: %s",
            self.town_id,
            "Encontrados" if hourly_cache else "No encontrados",
            "Encontrados" if daily_cache else "No encontrados",
        )

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
            hass=self.hass,
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

        _LOGGER.info("No se encontró un valor válido para '%s' en %s.", variable_name, target_time)
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
        self.town_id = entry_data["town_id"]  # Municipality ID
        self.hass = hass

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
                            self.hass,
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
            _LOGGER.exception("Error inesperado al obtener datos de alertas: %s", err)

        # Intentar cargar datos en caché si hay un error
        cached_data = await load_json_from_file(self.alerts_file)
        if self._is_valid_alert_data(cached_data):
            _LOGGER.warning(
                "Usando datos en caché para las alertas. Última actualización: %s",
                cached_data["actualitzat"]["dataUpdate"],
            )
            return {"actualizado": cached_data['actualitzat']['dataUpdate']}

        # Si no se puede actualizar ni cargar datos en caché, retornar None
        _LOGGER.error("No se pudo obtener datos actualizados ni cargar datos en caché de alertas.")
        return None

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
        _LOGGER.info("Datos cargados desde %s: %s", self._file_path, data)  # Log de la carga de datos

        if not data:
            _LOGGER.error("No se pudo cargar el archivo JSON de alertas en %s.", self._file_path)
            return {}

        return self._process_alerts_data(data)

    def _process_alerts_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa los datos de alertas y devuelve un diccionario filtrado por región."""
        if not data.get("dades"):
            _LOGGER.info("No hay alertas activas para la región %s.", self.region_id)
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
            _LOGGER.exception("Error inesperado al obtener cuotas de la API de Meteocat: %s", err)
        
        # Intentar cargar datos en caché si hay un error
        cached_data = await load_json_from_file(self.quotes_file)
        if cached_data:
            _LOGGER.warning("Usando datos en caché para las cuotas de la API de Meteocat.")
            return {"actualizado": cached_data['actualitzat']['dataUpdate']}

        _LOGGER.error("No se pudo obtener datos actualizados ni cargar datos en caché.")
        return None
    
class MeteocatQuotesFileCoordinator(DataUpdateCoordinator):
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
            _LOGGER,
            name="Meteocat Quotes File Coordinator",
            update_interval=DEFAULT_QUOTES_FILE_UPDATE_INTERVAL,
        )
        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.quotes_file = files_folder / "quotes.json"

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de quotes.json y devuelve el estado de las cuotas."""
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
            _LOGGER.exception("Error inesperado al obtener los datos de rayos de la API de Meteocat: %s", err)

        # Intentar cargar datos en caché si la API falla
        cached_data = await load_json_from_file(self.lightning_file)
        if cached_data:
            _LOGGER.warning("Usando datos en caché para los datos de rayos de la API de Meteocat.")
            return {"actualizado": cached_data['actualitzat']['dataUpdate']}

        _LOGGER.error("No se pudo obtener datos actualizados ni cargar datos en caché.")
        return None

class MeteocatLightningFileCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de rayos desde lightning_{region_id}.json."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
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

        super().__init__(
            hass,
            _LOGGER,
            name="Meteocat Lightning File Coordinator",
            update_interval=DEFAULT_LIGHTNING_FILE_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de rayos desde el archivo JSON y procesa la información."""
        existing_data = await load_json_from_file(self.lightning_file)

        if not existing_data:
            _LOGGER.warning("No se encontraron datos en %s.", self.lightning_file)
            return {
                "actualizado": datetime.now(TIMEZONE).isoformat(),
                "region": self._reset_data(),
                "town": self._reset_data()
            }

        # Convertir la cadena de fecha a un objeto datetime y ajustar a la zona horaria local
        update_date = datetime.fromisoformat(existing_data.get("actualitzat", {}).get("dataUpdate", ""))
        update_date = update_date.astimezone(TIMEZONE)
        now = datetime.now(TIMEZONE)

        if update_date.date() != now.date():  # Si la fecha no es la de hoy
            _LOGGER.info("Los datos de rayos son de un día diferente. Reiniciando valores a cero.")
            region_data = town_data = self._reset_data()
            update_date = datetime.now(TIMEZONE).isoformat()  # Usar la fecha actual
        else:
            region_data = self._process_region_data(existing_data.get("dades", []))
            town_data = self._process_town_data(existing_data.get("dades", []))

        return {
            "actualizado": update_date,
            "region": region_data,
            "town": town_data
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
            "total": 0
        }

class MeteocatSunCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de sol calculados con Astral."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
    ):
        """
        Inicializa el coordinador de sol de Meteocat.
        
        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
        """
        self.latitude = entry_data.get("latitude")
        self.longitude = entry_data.get("longitude")
        self.timezone_str = hass.config.time_zone or "Europe/Madrid"
        self.town_id = entry_data.get("town_id")
        
        # Creamos un LocationInfo "custom" con los datos de configuración.
        # Nota: No dependemos de la base de datos interna de Astral (ni de lookup),
        # por lo que el town_name puede ser cualquier cadena descriptiva.
        # Esta es precisamente la opción recomendada por la documentación de Astral
        # cuando la localización no está en su base de datos.
        self.location = LocationInfo(
            name=entry_data.get("town_name", "Municipio"),
            region="Spain",
            timezone=self.timezone_str,
            latitude=self.latitude,
            longitude=self.longitude,
        )

        # Ruta persistente en /config/meteocat_files/files
        files_folder = get_storage_dir(hass, "files")
        self.sun_file = files_folder / f"sun_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Sun Coordinator",
            update_interval=DEFAULT_SUN_UPDATE_INTERVAL,  # Ej. timedelta(minutes=1)
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de sol calculados o usa datos en caché según si los eventos han pasado."""
        existing_data = await load_json_from_file(self.sun_file) or {}

        now = datetime.now(tz=ZoneInfo(self.timezone_str))

        if not existing_data or "dades" not in existing_data or not existing_data["dades"]:
            return await self._calculate_and_save_new_data()

        last_update_str = existing_data.get('actualitzat', {}).get('dataUpdate')
        if not last_update_str:
            return await self._calculate_and_save_new_data()

        last_update = datetime.fromisoformat(last_update_str)

        dades = existing_data["dades"][0]
        saved_sunrise = datetime.fromisoformat(dades["sunrise"])
        saved_sunset = datetime.fromisoformat(dades["sunset"])

        # Verificar si los datos necesitan actualización
        if now > saved_sunrise or now > saved_sunset:
            return await self._calculate_and_save_new_data()
        else:
            _LOGGER.debug("Usando datos existentes de sol: %s", existing_data)
            return {"actualizado": existing_data['actualitzat']['dataUpdate']}

    async def _calculate_and_save_new_data(self):
        """Calcula nuevos datos de sol y los guarda en el archivo JSON."""
        try:
            now = datetime.now(tz=ZoneInfo(self.timezone_str))
            today = now.date()
            
            sun_data_today = sun(self.location.observer, date=today, tzinfo=ZoneInfo(self.timezone_str))
            sunrise = sun_data_today["sunrise"]
            sunset = sun_data_today["sunset"]
            
            if now > sunset:
                next_day = today + timedelta(days=1)
                sun_data_next = sun(self.location.observer, date=next_day, tzinfo=ZoneInfo(self.timezone_str))
                sunrise = sun_data_next["sunrise"]
                sunset = sun_data_next["sunset"]
            elif now > sunrise:
                next_day = today + timedelta(days=1)
                sun_data_next = sun(self.location.observer, date=next_day, tzinfo=ZoneInfo(self.timezone_str))
                sunrise = sun_data_next["sunrise"]
                # sunset permanece como el de hoy
            
            # Estructurar los datos en el formato correcto
            current_time = now.isoformat()
            data_with_timestamp = {
                "actualitzat": {
                    "dataUpdate": current_time
                },
                "dades": [
                    {
                        "sunrise": sunrise.isoformat(),
                        "sunset": sunset.isoformat()
                    }
                ]
            }

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data_with_timestamp, self.sun_file)

            _LOGGER.debug("Datos de sol actualizados exitosamente: %s", data_with_timestamp)

            return {"actualizado": data_with_timestamp['actualitzat']['dataUpdate']}

        except Exception as err:
            _LOGGER.exception("Error inesperado al calcular los datos de sol: %s", err)

        # Intentar cargar datos en caché si falla el cálculo (aunque es improbable)
        cached_data = await load_json_from_file(self.sun_file)
        if cached_data:
            _LOGGER.warning("Usando datos en caché para los datos de sol.")
            return {"actualizado": cached_data['actualitzat']['dataUpdate']}

        _LOGGER.error("No se pudo calcular datos actualizados ni cargar datos en caché.")
        return None

class MeteocatSunFileCoordinator(DataUpdateCoordinator):
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
            _LOGGER,
            name="Meteocat Sun File Coordinator",
            update_interval=DEFAULT_SUN_FILE_UPDATE_INTERVAL,  # Ej. timedelta(seconds=30)
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de sol desde el archivo JSON y procesa la información."""
        existing_data = await load_json_from_file(self.sun_file)

        if not existing_data or "dades" not in existing_data or not existing_data["dades"]:
            _LOGGER.warning("No se encontraron datos en %s.", self.sun_file)
            return self._reset_data()

        update_date_str = existing_data.get("actualitzat", {}).get("dataUpdate", "")
        update_date = datetime.fromisoformat(update_date_str) if update_date_str else None
        now = datetime.now(ZoneInfo(self.timezone_str))

        dades = existing_data["dades"][0]
        saved_sunrise = datetime.fromisoformat(dades["sunrise"])
        saved_sunset = datetime.fromisoformat(dades["sunset"])

        if saved_sunrise < now and saved_sunset < now:
            _LOGGER.info("Los datos de sol están caducados. Reiniciando valores.")
            return self._reset_data()
        else:
            return {
                "actualizado": update_date.isoformat() if update_date else now.isoformat(),
                "sunrise": dades.get("sunrise"),
                "sunset": dades.get("sunset")
            }

    def _reset_data(self):
        """Resetea los datos a valores nulos."""
        return {
            "actualizado": datetime.now(ZoneInfo(self.timezone_str)).isoformat(),
            "sunrise": None,
            "sunset": None
        }

class MeteocatMoonCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de la fase lunar calculados con moon.py."""

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

    def _get_moon_phase_name(self, phase: float) -> str:
        """Convierte el valor numérico de la fase lunar en un nombre descriptivo."""
        if 0 <= phase < 7:
            return "new_moon"
        elif 7 <= phase < 14:
            return "first_quarter"
        elif 14 <= phase < 21:
            return "full_moon"
        elif 21 <= phase < 28:
            return "last_quarter"
        return "unknown"

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de la fase lunar según validez de moonrise/moonset."""
        existing_data = await load_json_from_file(self.moon_file) or {}
        now = datetime.now(tz=ZoneInfo(self.timezone_str))

        # Si no hay datos guardados → calcular directamente
        if not existing_data or "dades" not in existing_data or not existing_data["dades"]:
            return await self._calculate_and_save_new_data()

        dades = existing_data["dades"][0]
        moonrise_str = dades.get("moonrise")
        moonset_str = dades.get("moonset")

        moonrise = datetime.fromisoformat(moonrise_str) if moonrise_str else None
        moonset = datetime.fromisoformat(moonset_str) if moonset_str else None

        # Si ya pasó el moonrise de hoy → recalcular todo (fase incluida)
        if moonrise and now > moonrise:
            return await self._calculate_and_save_new_data(force_next_day=True)

        # Si ya pasó el moonset de hoy → recalcular solo el moonset
        if moonset and now > moonset:
            return await self._calculate_and_save_new_data(update_only="moonset")

        # En cualquier otro caso seguimos con los datos existentes
        _LOGGER.debug("Usando datos existentes de la luna: %s", existing_data)
        return {"actualizado": existing_data['actualitzat']['dataUpdate']}

    async def _calculate_and_save_new_data(self, force_next_day: bool = False, update_only: str = None):
        """Calcula y guarda nuevos datos de la luna (moonrise, moonset, fase)."""
        try:
            now = datetime.now(tz=ZoneInfo(self.timezone_str))
            today = now.date()
            target_date = today

            if force_next_day:
                target_date = today + timedelta(days=1)

            # Calcular fase lunar
            moon_phase_value = moon_phase(target_date)
            moon_phase_name = self._get_moon_phase_name(moon_phase_value)

            # Calcular eventos
            moonrise, moonset = moon_rise_set(self.latitude, self.longitude, target_date)
            if moonrise:
                moonrise = moonrise.astimezone(ZoneInfo(self.timezone_str))
            if moonset:
                moonset = moonset.astimezone(ZoneInfo(self.timezone_str))

            # Cargar datos existentes si solo queremos actualizar moonset
            if update_only == "moonset":
                existing_data = await load_json_from_file(self.moon_file) or {}
                if existing_data and "dades" in existing_data and existing_data["dades"]:
                    dades = existing_data["dades"][0]
                    moonrise_str = dades.get("moonrise")
                    moon_phase_value = dades.get("moon_phase")
                    moon_phase_name = dades.get("moon_phase_name")
                    moonrise = datetime.fromisoformat(moonrise_str) if moonrise_str else moonrise
                # aquí sí sustituimos solo moonset

            # Normalizar a ISO string
            moonrise_str = moonrise.isoformat() if moonrise else None
            moonset_str = moonset.isoformat() if moonset else None

            data_with_timestamp = {
                "actualitzat": {"dataUpdate": now.isoformat()},
                "dades": [
                    {
                        "moon_phase": moon_phase_value,
                        "moon_phase_name": moon_phase_name,
                        "moonrise": moonrise_str,
                        "moonset": moonset_str,
                    }
                ],
            }

            await save_json_to_file(data_with_timestamp, self.moon_file)
            _LOGGER.debug("Datos de la luna actualizados: %s", data_with_timestamp)

            return {"actualizado": data_with_timestamp['actualitzat']['dataUpdate']}

        except Exception as err:
            _LOGGER.exception("Error calculando los datos de la luna: %s", err)

            cached_data = await load_json_from_file(self.moon_file)
            if cached_data:
                _LOGGER.warning("Usando datos en caché para los datos de la luna.")
                return {"actualizado": cached_data['actualitzat']['dataUpdate']}

            _LOGGER.error("No se pudo calcular datos de la luna ni cargar datos en caché.")
            return None

class MeteocatMoonFileCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de los datos de la luna desde moon_{town_id}.json."""

    def __init__(self, hass: HomeAssistant, entry_data: dict):
        self.town_id = entry_data["town_id"]
        self.timezone_str = hass.config.time_zone or "Europe/Madrid"

        files_folder = get_storage_dir(hass, "files")
        self.moon_file = files_folder / f"moon_{self.town_id.lower()}_data.json"

        super().__init__(
            hass,
            _LOGGER,
            name="Meteocat Moon File Coordinator",
            update_interval=DEFAULT_MOON_FILE_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Carga los datos de la luna desde el archivo JSON y procesa la información."""
        existing_data = await load_json_from_file(self.moon_file)

        if not existing_data or "dades" not in existing_data or not existing_data["dades"]:
            _LOGGER.warning("No se encontraron datos en %s.", self.moon_file)
            return self._reset_data()

        update_date_str = existing_data.get("actualitzat", {}).get("dataUpdate", "")
        update_date = datetime.fromisoformat(update_date_str) if update_date_str else None
        now = datetime.now(ZoneInfo(self.timezone_str))

        if update_date and update_date.date() < now.date():
            _LOGGER.info("Los datos de la luna están caducados. Reiniciando valores.")
            return self._reset_data()
        else:
            dades = existing_data["dades"][0]
            return {
                "actualizado": update_date.isoformat() if update_date else now.isoformat(),
                "moon_phase": dades.get("moon_phase"),
                "moon_phase_name": dades.get("moon_phase_name"),
                "moonrise": dades.get("moonrise"),
                "moonset": dades.get("moonset"),
            }

    def _reset_data(self):
        """Resetea los datos a valores nulos."""
        return {
            "actualizado": datetime.now(ZoneInfo(self.timezone_str)).isoformat(),
            "moon_phase": None,
            "moon_phase_name": None,
            "moonrise": None,
            "moonset": None,
        }
