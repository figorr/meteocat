from __future__ import annotations

import os
import json
import aiofiles
import logging
from datetime import timedelta
from typing import Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady

from meteocatpy.data import MeteocatStationData
# from meteocatpy.forecast import MeteocatForecast
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
DEFAULT_ENTITY_UPDATE_INTERVAL = timedelta(hours=12)

async def save_json_to_file(data: dict, output_file: str) -> None:
    """Save the JSON data to a file asynchronously."""
    try:
        # Crea el directorio si no existe
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Escribe los datos JSON de forma asíncrona
        async with aiofiles.open(output_file, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        raise RuntimeError(f"Error saving JSON to {output_file}: {e}")

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
            # Obtener datos desde la API
            data = await self.meteocat_station_data.get_station_data(self.station_id)
            _LOGGER.debug("Datos de sensores actualizados exitosamente: %s", data)

            # Determinar la ruta al archivo en la carpeta raíz del repositorio
            output_file = os.path.join(
                self.hass.config.path(), "custom_components", "meteocat", "files", "station_data.json"
            )

            # Guardar los datos en un archivo JSON
            await save_json_to_file(data, output_file)

            return data
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
            _LOGGER.exception(
                "Error inesperado al obtener datos de sensores (Station ID: %s): %s",
                self.station_id,
                err,
            )
            raise

# class MeteocatEntityCoordinator(DataUpdateCoordinator):
#     """Coordinator para manejar la actualización de datos de las entidades de predicción."""

#     def __init__(
#         self,
#         hass: HomeAssistant,
#         entry_data: dict,
#         update_interval: timedelta = DEFAULT_ENTITY_UPDATE_INTERVAL,
#     ):
#         """
#         Inicializa el coordinador de datos para entidades de predicción.

#         Args:
#             hass (HomeAssistant): Instancia de Home Assistant.
#             entry_data (dict): Datos de configuración obtenidos de core.config_entries.
#             update_interval (timedelta): Intervalo de actualización.
#         """
#         self.api_key = entry_data["api_key"]
#         self.town_name = entry_data["town_name"]
#         self.town_id = entry_data["town_id"]
#         self.station_name = entry_data["station_name"]
#         self.station_id = entry_data["station_id"]
#         self.variable_name = entry_data["variable_name"]
#         self.variable_id = entry_data["variable_id"]
#         self.meteocat_forecast = MeteocatForecast(self.api_key)

#         super().__init__(
#             hass,
#             _LOGGER,
#             name=f"{DOMAIN} Entity Coordinator",
#             update_interval=update_interval,
#         )

#     async def _async_update_data(self) -> Dict:
#         """Actualiza los datos de las entidades de predicción desde la API de Meteocat."""
#         try:
#             hourly_forecast = await self.meteocat_forecast.get_prediccion_horaria(self.town_id)
#             daily_forecast = await self.meteocat_forecast.get_prediccion_diaria(self.town_id)
#             _LOGGER.debug(
#                 "Datos de predicción actualizados exitosamente (Town ID: %s)", self.town_id
#             )
#             return {
#                 "hourly_forecast": hourly_forecast,
#                 "daily_forecast": daily_forecast,
#             }
#         except ForbiddenError as err:
#             _LOGGER.error(
#                 "Acceso denegado al obtener datos de predicción (Town ID: %s): %s",
#                 self.town_id,
#                 err,
#             )
#             raise ConfigEntryNotReady from err
#         except TooManyRequestsError as err:
#             _LOGGER.warning(
#                 "Límite de solicitudes alcanzado al obtener datos de predicción (Town ID: %s): %s",
#                 self.town_id,
#                 err,
#             )
#             raise ConfigEntryNotReady from err
#         except (BadRequestError, InternalServerError, UnknownAPIError) as err:
#             _LOGGER.error(
#                 "Error al obtener datos de predicción (Town ID: %s): %s",
#                 self.town_id,
#                 err,
#             )
#             raise
#         except Exception as err:
#             _LOGGER.exception(
#                 "Error inesperado al obtener datos de predicción (Town ID: %s): %s",
#                 self.town_id,
#                 err,
#             )
#             raise
