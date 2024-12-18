from __future__ import annotations

import os
import json
import aiofiles
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady

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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Valores predeterminados para los intervalos de actualización
DEFAULT_SENSOR_UPDATE_INTERVAL = timedelta(minutes=90)
DEFAULT_ENTITY_UPDATE_INTERVAL = timedelta(hours=48)
DEFAULT_HOURLY_FORECAST_UPDATE_INTERVAL = timedelta(hours=24)
DEFAULT_DAYLY_FORECAST_UPDATE_INTERVAL = timedelta(hours=48)
DEFAULT_UVI_UPDATE_INTERVAL = timedelta(hours=48)
DEFAULT_UVI_SENSOR_UPDATE_INTERVAL = timedelta(minutes=5)

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

def load_json_from_file(input_file: str) -> dict | list | None:
    """Carga datos JSON desde un archivo de forma síncrona."""
    try:
        if os.path.exists(input_file):
            with open(input_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        _LOGGER.error(f"Error cargando JSON desde {input_file}: {e}")
    return None

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

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Uvi Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict:
        """Actualiza los datos de los sensores desde la API de Meteocat."""
        try:
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
            
            # Extraer la lista de datos bajo la clave 'uvi'
            uvi_data = data.get('uvi', [])
            
            # Validar que 'uvi' sea una lista de diccionarios
            if not isinstance(uvi_data, list) or not all(isinstance(item, dict) for item in uvi_data):
                _LOGGER.error("Formato inválido: 'uvi' debe ser una lista de dicts. Datos: %s", uvi_data)
                raise ValueError("Formato de datos inválido")

            # Determinar la ruta al archivo en la carpeta raíz del repositorio
            output_file = os.path.join(
                self.hass.config.path(),
                "custom_components",
                "meteocat",
                "files",
                f"uvi_{self.town_id.lower()}_data.json"
            )

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data, output_file)

            return uvi_data
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
            if isinstance(err, ConfigEntryNotReady):
                # El dispositivo no pudo inicializarse por primera vez
                _LOGGER.exception(
                    "No se pudo inicializar el dispositivo (Town ID: %s) debido a un error: %s",
                    self.town_id,
                    err,
                )
                raise  # Re-raise the exception to indicate a fundamental failure in initialization
            else:
                # Manejar error durante la actualización de datos
                _LOGGER.exception(
                    "Error inesperado al obtener datos del índice UV para (Town ID: %s): %s",
                    self.town_id,
                    err,
                )
                # Intentar cargar datos en caché si hay un error
                cached_data = load_json_from_file(output_file)
                if cached_data:
                    _LOGGER.info("Usando datos en caché para la ciudad %s.", self.town_id)
                    return cached_data
                # No se puede actualizar el estado, retornar None o un estado fallido
                return None  # o cualquier otro valor que indique un estado de error

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
            hourly_data = await asyncio.wait_for(
                self.meteocat_forecast.get_prediccion_horaria(self.town_id), timeout=30
            )
            daily_data = await asyncio.wait_for(
                self.meteocat_forecast.get_prediccion_diaria(self.town_id), timeout=30
            )

            _LOGGER.debug(
                "Predicción horaria y diaria obtenida exitosamente para %s.", self.town_id
            )

            save_json_to_file(hourly_data, hourly_file)
            save_json_to_file(daily_data, daily_file)

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
