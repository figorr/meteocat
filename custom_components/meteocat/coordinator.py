from __future__ import annotations

import os
import json
import aiofiles
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.weather import Forecast

from meteocatpy.data import MeteocatStationData
from meteocatpy.uvi import MeteocatUviData
from meteocatpy.forecast import MeteocatForecast

from meteocatpy.exceptions import (
    BadRequestError,
    ForbiddenError,
    TooManyRequestsError,
    InternalServerError,
    UnknownAPIError,
)

from .condition import get_condition_from_statcel
from .const import (
    DOMAIN,
    CONDITION_MAPPING,
)

_LOGGER = logging.getLogger(__name__)

# Valores predeterminados para los intervalos de actualización
DEFAULT_SENSOR_UPDATE_INTERVAL = timedelta(minutes=90)
DEFAULT_STATIC_SENSOR_UPDATE_INTERVAL = timedelta(hours=24)
DEFAULT_ENTITY_UPDATE_INTERVAL = timedelta(hours=48)
DEFAULT_HOURLY_FORECAST_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_DAILY_FORECAST_UPDATE_INTERVAL = timedelta(minutes=15)
DEFAULT_UVI_UPDATE_INTERVAL = timedelta(hours=48)
DEFAULT_UVI_SENSOR_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_CONDITION_SENSOR_UPDATE_INTERVAL = timedelta(minutes=5)

async def save_json_to_file(data: dict, output_file: str) -> None:
    """Guarda datos JSON en un archivo de forma asíncrona."""
    try:
        # Crea el directorio si no existe
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Escribe los datos JSON de forma asíncrona
        async with aiofiles.open(output_file, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        raise RuntimeError(f"Error guardando JSON to {output_file}: {e}")

async def load_json_from_file(input_file: str) -> dict:
    """
    Carga un archivo JSON de forma asincrónica.
    
    Args:
        input_file (str): Ruta del archivo JSON.
    
    Returns:
        dict: Datos JSON cargados.
    """
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

class MeteocatSensorCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de los sensores."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
        update_interval: timedelta = DEFAULT_SENSOR_UPDATE_INTERVAL,
    ):
        """
        Inicializa el coordinador de sensores de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
            update_interval (timedelta): Intervalo de actualización.
        """
        self.api_key = entry_data["api_key"]  # Usamos la API key de la configuración
        self.town_name = entry_data["town_name"]  # Usamos el nombre del municipio
        self.town_id = entry_data["town_id"]  # Usamos el ID del municipio
        self.station_name = entry_data["station_name"]  # Usamos el nombre de la estación
        self.station_id = entry_data["station_id"]  # Usamos el ID de la estación
        self.variable_name = entry_data["variable_name"]  # Usamos el nombre de la variable
        self.variable_id = entry_data["variable_id"]  # Usamos el ID de la variable
        self.meteocat_station_data = MeteocatStationData(self.api_key)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Sensor Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de los sensores desde la API de Meteocat."""
        try:
            # Obtener datos desde la API con manejo de tiempo límite
            data = await asyncio.wait_for(
                self.meteocat_station_data.get_station_data(self.station_id),
                timeout=30  # Tiempo límite de 30 segundos
            )
            _LOGGER.debug("Datos de sensores actualizados exitosamente: %s", data)

            # Validar que los datos sean una lista de diccionarios
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                _LOGGER.error(
                    "Formato inválido: Se esperaba una lista de dicts, pero se obtuvo %s. Datos: %s",
                    type(data).__name__,
                    data,
                )
                raise ValueError("Formato de datos inválido")

            # Determinar la ruta al archivo en la carpeta raíz del repositorio
            output_file = os.path.join(
                self.hass.config.path(),
                "custom_components",
                "meteocat",
                "files",
                f"station_{self.station_id.lower()}_data.json"
            )

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data, output_file)

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
                # El dispositivo no pudo inicializarse por primera vez
                _LOGGER.exception(
                    "No se pudo inicializar el dispositivo (Station ID: %s) debido a un error: %s",
                    self.station_id,
                    err,
                )
                raise  # Re-raise the exception to indicate a fundamental failure in initialization
            else:
                # Manejar error durante la actualización de datos
                _LOGGER.exception(
                    "Error inesperado al obtener datos de los sensores para (Station ID: %s): %s",
                    self.station_id,
                    err,
                )
                # Intentar cargar datos en caché si hay un error
                cached_data = load_json_from_file(output_file)
                if cached_data:
                    _LOGGER.info("Usando datos en caché para la estación %s.", self.station_id)
                    return cached_data
                # No se puede actualizar el estado, retornar None o un estado fallido
                return None  # o cualquier otro valor que indique un estado de error

class MeteocatStaticSensorCoordinator(DataUpdateCoordinator):
    """Coordinator to manage and update static sensor data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
        update_interval: timedelta = DEFAULT_STATIC_SENSOR_UPDATE_INTERVAL,
    ):
        """
        Initialize the MeteocatStaticSensorCoordinator.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            entry_data (dict): Configuration data from core.config_entries.
            update_interval (timedelta): Update interval for the coordinator.
        """
        self.town_name = entry_data["town_name"]  # Nombre del municipio
        self.town_id = entry_data["town_id"]  # ID del municipio
        self.station_name = entry_data["station_name"]  # Nombre de la estación
        self.station_id = entry_data["station_id"]  # ID de la estación

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Static Sensor Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """
        Fetch and return static sensor data.

        Since static sensors use entry_data, this method simply logs the process.
        """
        _LOGGER.debug(
            "Updating static sensor data for town: %s (ID: %s), station: %s (ID: %s)",
            self.town_name,
            self.town_id,
            self.station_name,
            self.station_id,
        )
        return {
            "town_name": self.town_name,
            "town_id": self.town_id,
            "station_name": self.station_name,
            "station_id": self.station_id,
        }

class MeteocatUviCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de los sensores."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
        update_interval: timedelta = DEFAULT_UVI_UPDATE_INTERVAL,
    ):
        """
        Inicializa el coordinador del sensor del Índice UV de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
            update_interval (timedelta): Intervalo de actualización.
        """
        self.api_key = entry_data["api_key"]  # Usamos la API key de la configuración
        self.town_id = entry_data["town_id"]  # Usamos el ID del municipio
        self.meteocat_uvi_data = MeteocatUviData(self.api_key)
        self.output_file = os.path.join(
            hass.config.path(),
            "custom_components",
            "meteocat",
            "files",
            f"uvi_{self.town_id.lower()}_data.json"
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Uvi Coordinator",
            update_interval=update_interval,
        )

    async def is_uvi_data_valid(self) -> dict:
        """Comprueba si el archivo JSON contiene datos válidos para el día actual y devuelve los datos si son válidos."""
        try:
            if not os.path.exists(self.output_file):
                return None

            async with aiofiles.open(self.output_file, "r", encoding="utf-8") as file:
                content = await file.read()
                data = json.loads(content)

            # Verificar que el formato sea correcto
            if not isinstance(data, dict) or "uvi" not in data:
                return None

            uvi_data = data["uvi"]
            if not isinstance(uvi_data, list) or not uvi_data:
                return None

            # Validar la fecha del primer elemento
            first_date = uvi_data[0].get("date")
            if first_date != datetime.now(timezone.utc).strftime("%Y-%m-%d"):
                return None

            return data
        except Exception as e:
            _LOGGER.error("Error al validar el archivo JSON del índice UV: %s", e)
            return None

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de los sensores desde la API de Meteocat."""
        try:
            # Validar el archivo JSON existente
            valid_data = await self.is_uvi_data_valid()
            if valid_data and "uvi" in valid_data:
                _LOGGER.info("Los datos del índice UV están actualizados. No se realiza llamada a la API.")
                return valid_data['uvi']

            # Obtener datos desde la API con manejo de tiempo límite
            data = await asyncio.wait_for(
                self.meteocat_uvi_data.get_uvi_index(self.town_id),
                timeout=30  # Tiempo límite de 30 segundos
            )
            _LOGGER.debug("Datos de sensores actualizados exitosamente: %s", data)

            # Validar que los datos sean un dict con una clave 'uvi'
            if not isinstance(data, dict) or 'uvi' not in data:
                _LOGGER.error("Formato inválido: Se esperaba un dict con la clave 'uvi'. Datos: %s", data)
                raise ValueError("Formato de datos inválido")

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data, self.output_file)

            return data['uvi']
        except asyncio.TimeoutError as err:
            _LOGGER.warning("Tiempo de espera agotado al obtener datos de la API de Meteocat.")
            raise ConfigEntryNotReady from err
        except ForbiddenError as err:
            _LOGGER.error(
                "Acceso denegado al obtener datos del índice UV para (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning(
                "Límite de solicitudes alcanzado al obtener datos del índice UV para (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error(
                "Error al obtener datos del índice UV para (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise
        except Exception as err:
            _LOGGER.exception(
                "Error inesperado al obtener datos del índice UV para (Town ID: %s): %s",
                self.town_id,
                err,
            )
            # Intentar cargar datos en caché si hay un error
            cached_data = load_json_from_file(self.output_file)
            if cached_data:
                _LOGGER.info("Usando datos en caché para la ciudad %s.", self.town_id)
                return cached_data.get('uvi', [])
            return None

class MeteocatUviFileCoordinator(DataUpdateCoordinator):
    """Coordinator to read and process UV data from a file."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
        update_interval: timedelta = DEFAULT_UVI_SENSOR_UPDATE_INTERVAL,
    ):
        """
        Inicializa el coordinador del sensor del Índice UV de Meteocat.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
            update_interval (timedelta): Intervalo de actualización.
        """
        self.town_id = entry_data["town_id"]  # Usamos el ID del municipio

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Uvi File Coordinator",
            update_interval=update_interval,
        )
        self._file_path = os.path.join(
            hass.config.path("custom_components/meteocat/files"),
            f"uvi_{self.town_id.lower()}_data.json",
        )

    async def _async_update_data(self):
        """Read and process UV data for the current hour from the file asynchronously."""
        try:
            async with aiofiles.open(self._file_path, "r", encoding="utf-8") as file:
                raw_data = await file.read()
                raw_data = json.loads(raw_data)  # Parse JSON data
        except FileNotFoundError:
            _LOGGER.error(
                "No se ha encontrado el archivo JSON con datos del índice UV en %s.",
                self._file_path,
            )
            return {}
        except json.JSONDecodeError:
            _LOGGER.error(
                "Error al decodificar el archivo JSON del índice UV en %s.",
                self._file_path,
            )
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
            if day_data["date"] == current_date:
                # Encuentra los datos de la hora actual
                for hour_data in day_data.get("hours", []):
                    if hour_data["hour"] == current_hour:
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
        update_interval: timedelta = DEFAULT_ENTITY_UPDATE_INTERVAL,
    ):
        """
        Inicializa el coordinador de datos para entidades de predicción.

        Args:
            hass (HomeAssistant): Instancia de Home Assistant.
            entry_data (dict): Datos de configuración obtenidos de core.config_entries.
            update_interval (timedelta): Intervalo de actualización.
        """
        self.api_key = entry_data["api_key"]
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.variable_name = entry_data["variable_name"]
        self.variable_id = entry_data["variable_id"]
        self.meteocat_forecast = MeteocatForecast(self.api_key)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Entity Coordinator",
            update_interval=update_interval,
        )

    async def _is_data_valid(self, file_path: str) -> bool:
        """Verifica si los datos en el archivo JSON son válidos y actuales."""
        if not os.path.exists(file_path):
            return False

        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            if not data or "dies" not in data or not data["dies"]:
                return False

            # Obtener la fecha del primer día
            first_date = datetime.fromisoformat(data["dies"][0]["data"].rstrip("Z")).date()
            return first_date == datetime.now(timezone.utc).date()
        except Exception as e:
            _LOGGER.warning("Error validando datos en %s: %s", file_path, e)
            return False

    async def _fetch_and_save_data(self, api_method, file_path: str) -> dict:
        """Obtiene datos de la API y los guarda en un archivo JSON."""
        data = await asyncio.wait_for(api_method(self.town_id), timeout=30)
        await save_json_to_file(data, file_path)
        return data

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de predicción desde la API de Meteocat."""
        hourly_file = os.path.join(
            self.hass.config.path(),
            "custom_components",
            "meteocat",
            "files",
            f"forecast_{self.town_id.lower()}_hourly_data.json",
        )
        daily_file = os.path.join(
            self.hass.config.path(),
            "custom_components",
            "meteocat",
            "files",
            f"forecast_{self.town_id.lower()}_daily_data.json",
        )

        try:
            hourly_data = (
                load_json_from_file(hourly_file)
                if await self._is_data_valid(hourly_file)
                else await self._fetch_and_save_data(
                    self.meteocat_forecast.get_prediccion_horaria, hourly_file
                )
            )
            daily_data = (
                load_json_from_file(daily_file)
                if await self._is_data_valid(daily_file)
                else await self._fetch_and_save_data(
                    self.meteocat_forecast.get_prediccion_diaria, daily_file
                )
            )

            _LOGGER.debug(
                "Datos de predicción horaria y diaria actualizados correctamente para %s.",
                self.town_id,
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
            return {
                "hourly": load_json_from_file(hourly_file) or {},
                "daily": load_json_from_file(daily_file) or {},
            }

def get_condition_from_code(code: int) -> str:
    """Devuelve la condición meteorológica basada en el código."""
    return next((key for key, codes in CONDITION_MAPPING.items() if code in codes), "unknown")

class HourlyForecastCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar las predicciones horarias desde archivos locales."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
        update_interval: timedelta = DEFAULT_HOURLY_FORECAST_UPDATE_INTERVAL,
    ):
        """Inicializa el coordinador para predicciones horarias."""
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.file_path = os.path.join(
            hass.config.path(),
            "custom_components",
            "meteocat",
            "files",
            f"forecast_{self.town_id.lower()}_hourly_data.json",
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Hourly Forecast Coordinator",
            update_interval=update_interval,
        )

    async def _is_data_valid(self) -> bool:
        """Verifica si los datos en el archivo JSON son válidos y actuales."""
        if not os.path.exists(self.file_path):
            return False

        try:
            async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            if not data or "dies" not in data or not data["dies"]:
                return False

            # Validar que los datos sean para la fecha actual
            first_date = datetime.fromisoformat(data["dies"][0]["data"].rstrip("Z")).date()
            return first_date == datetime.now(timezone.utc).date()
        except Exception as e:
            _LOGGER.warning("Error validando datos horarios en %s: %s", self.file_path, e)
            return False

    async def _async_update_data(self) -> dict:
        """Lee los datos de predicción horaria desde el archivo local."""
        if await self._is_data_valid():
            try:
                async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content)
            except Exception as e:
                _LOGGER.warning("Error leyendo archivo de predicción horaria: %s", e)

        return {}

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Devuelve una lista de objetos Forecast para las próximas horas."""
        if not self.data or "dies" not in self.data:
            return None

        forecasts = []
        now = datetime.now(timezone.utc)

        for dia in self.data["dies"]:
            for forecast in dia.get("variables", {}).get("estatCel", {}).get("valors", []):
                forecast_time = datetime.fromisoformat(forecast["data"].rstrip("Z")).replace(tzinfo=timezone.utc)
                if forecast_time >= now:
                    # Usar la función para obtener la condición meteorológica
                    condition = get_condition_from_code(int(forecast["valor"]))

                    forecast_data = {
                        "datetime": forecast_time,
                        "temperature": self._get_variable_value(dia, "temp", forecast_time),
                        "precipitation": self._get_variable_value(dia, "precipitacio", forecast_time),
                        "condition": condition,  # Se usa la condición traducida
                        "wind_speed": self._get_variable_value(dia, "velVent", forecast_time),
                        "wind_bearing": self._get_variable_value(dia, "dirVent", forecast_time),
                        "humidity": self._get_variable_value(dia, "humitat", forecast_time),
                    }
                    forecasts.append(Forecast(**forecast_data))

        return forecasts if forecasts else None

    def _get_variable_value(self, dia, variable_name, target_time):
        """Devuelve el valor de una variable específica para una hora determinada."""
        variable = dia.get("variables", {}).get(variable_name, {})
        for valor in variable.get("valors", []):
            data_hora = datetime.fromisoformat(valor["data"].rstrip("Z"))
            if data_hora == target_time:
                return valor["valor"]
        return None
    
class DailyForecastCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar las predicciones diarias desde archivos locales."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_data: dict,
        update_interval: timedelta = DEFAULT_DAILY_FORECAST_UPDATE_INTERVAL,
    ):
        """Inicializa el coordinador para predicciones diarias."""
        self.town_name = entry_data["town_name"]
        self.town_id = entry_data["town_id"]
        self.station_name = entry_data["station_name"]
        self.station_id = entry_data["station_id"]
        self.file_path = os.path.join(
            hass.config.path(),
            "custom_components",
            "meteocat",
            "files",
            f"forecast_{self.town_id.lower()}_daily_data.json",
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Daily Forecast Coordinator",
            update_interval=update_interval,
        )

    async def _is_data_valid(self) -> bool:
        """Verifica si hay datos válidos y actuales en el archivo JSON."""
        if not os.path.exists(self.file_path):
            return False

        try:
            async with aiofiles.open(self.file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

            if not data or "dies" not in data or not data["dies"]:
                return False

            today = datetime.now(timezone.utc).date()
            for dia in data["dies"]:
                forecast_date = datetime.fromisoformat(dia["data"].rstrip("Z")).date()
                if forecast_date >= today:
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
                today = datetime.now(timezone.utc).date()
                data["dies"] = [
                    dia for dia in data["dies"]
                    if datetime.fromisoformat(dia["data"].rstrip("Z")).date() >= today
                ]
                return data
            except Exception as e:
                _LOGGER.warning("Error leyendo archivo de predicción diaria: %s", e)

        return {}

    def get_forecast_for_today(self) -> dict | None:
        """Obtiene los datos diarios para el día actual."""
        if not self.data or "dies" not in self.data or not self.data["dies"]:
            return None

        today = datetime.now(timezone.utc).date()
        for dia in self.data["dies"]:
            forecast_date = datetime.fromisoformat(dia["data"].rstrip("Z")).date()
            if forecast_date == today:
                return dia
        return None

    def parse_forecast(self, dia: dict) -> dict:
        """Convierte un día de predicción en un diccionario con los datos necesarios."""
        variables = dia.get("variables", {})
        condition_code = variables.get("estatCel", {}).get("valor", -1)
        condition = get_condition_from_code(int(condition_code))

        forecast_data = {
            "date": datetime.fromisoformat(dia["data"].rstrip("Z")).date(),
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
        update_interval: timedelta = DEFAULT_CONDITION_SENSOR_UPDATE_INTERVAL,
    ):
        """
        Initialize the Meteocat Condition Coordinator.

        Args:
            hass (HomeAssistant): Instance of Home Assistant.
            entry_data (dict): Configuration data from core.config_entries.
            update_interval (timedelta): Update interval for the sensor.
        """
        self.town_id = entry_data["town_id"]  # Municipality ID
        self.hass = hass

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Condition Coordinator",
            update_interval=update_interval,
        )

        self._file_path = os.path.join(
            hass.config.path("custom_components/meteocat/files"),
            f"forecast_{self.town_id.lower()}_hourly_data.json",
        )

    async def _async_update_data(self):
        """Read and process condition data for the current hour from the file asynchronously."""
        try:
            async with aiofiles.open(self._file_path, "r", encoding="utf-8") as file:
                raw_data = await file.read()
                raw_data = json.loads(raw_data)  # Parse JSON data
        except FileNotFoundError:
            _LOGGER.error(
                "No se ha encontrado el archivo JSON con datos del estado del cielo en %s.",
                self._file_path,
            )
            return self.DEFAULT_CONDITION
        except json.JSONDecodeError:
            _LOGGER.error(
                "Error al decodificar el archivo JSON del estado del cielo en %s.",
                self._file_path,
            )
            return self.DEFAULT_CONDITION
        except Exception as e:
            _LOGGER.error("Error inesperado al leer los datos del archivo %s: %s", self._file_path, e)
            return self.DEFAULT_CONDITION

        return self._get_condition_for_current_hour(raw_data) or self.DEFAULT_CONDITION

    def _get_condition_for_current_hour(self, raw_data):
        """Get condition data for the current hour."""
        # Fecha y hora actual
        current_datetime = datetime.now()
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_hour = current_datetime.hour

        # Busca los datos para la fecha actual
        for day in raw_data.get("dies", []):
            if day["data"].startswith(current_date):
                for value in day["variables"]["estatCel"]["valors"]:
                    data_hour = datetime.fromisoformat(value["data"])
                    if data_hour.hour == current_hour:
                        codi_estatcel = value["valor"]
                        condition = get_condition_from_statcel(
                            codi_estatcel,
                            current_datetime,
                            self.hass,
                            is_hourly=True,
                        )
                        # Añadir hora y fecha a los datos de la condición
                        condition.update({
                            "hour": current_hour,
                            "date": current_date,
                        })
                        return condition
                break  # Sale del bucle una vez encontrada la fecha actual

        # Si no se encuentran datos, devuelve un diccionario vacío con valores predeterminados
        _LOGGER.warning(
            "No se encontraron datos del Estado del Cielo para hoy (%s) y la hora actual (%s).",
            current_date,
            current_hour,
        )
        return {"condition": "unknown", "hour": current_hour, "icon": None, "date": current_date}

