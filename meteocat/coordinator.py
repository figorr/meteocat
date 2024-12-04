from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady

from meteocatpy.data import MeteocatStationData
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
DEFAULT_ENTITY_UPDATE_INTERVAL = timedelta(hours=12)


class MeteocatSensorCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de los sensores."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        town_name: str,
        town_id: str,
        station_name: str,
        station_id: str,
        variable_name: str,
        variable_id: str,
        update_interval: timedelta = DEFAULT_SENSOR_UPDATE_INTERVAL,
    ):
        """Inicializa el coordinador de sensores de Meteocat."""
        self.api_key = api_key
        self.town_name = town_name
        self.town_id = town_id
        self.station_name = station_name
        self.station_id = station_id
        self.variable_name = variable_name
        self.variable_id = variable_id
        self.meteocat_station_data = MeteocatStationData(api_key)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Sensor Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict:
        """
        Actualiza los datos de los sensores desde la API de Meteocat.

        Returns:
            dict: Datos actualizados de los sensores.
        """
        try:
            data = await self.meteocat_station_data.get_station_data_with_variables(self.station_id)
            _LOGGER.debug("Datos de sensores actualizados exitosamente: %s", data)
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


class MeteocatEntityCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de las entidades de predicción."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        town_name: str,
        town_id: str,
        station_name: str,
        station_id: str,
        variable_name: str,
        variable_id: str,
        update_interval: timedelta = DEFAULT_ENTITY_UPDATE_INTERVAL,
    ):
        """Inicializa el coordinador de datos para entidades de predicción."""
        self.api_key = api_key
        self.town_name = town_name
        self.town_id = town_id
        self.station_name = station_name
        self.station_id = station_id
        self.variable_name = variable_name
        self.variable_id = variable_id
        self.meteocat_forecast = MeteocatForecast(api_key)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Entity Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict:
        """
        Actualiza los datos de las entidades de predicción desde la API de Meteocat.

        Returns:
            dict: Datos actualizados de predicción horaria y diaria.
        """
        try:
            hourly_forecast = await self.meteocat_forecast.get_prediccion_horaria(self.town_id)
            daily_forecast = await self.meteocat_forecast.get_prediccion_diaria(self.town_id)
            _LOGGER.debug(
                "Datos de predicción actualizados exitosamente (Town ID: %s)", self.town_id
            )
            return {
                "hourly_forecast": hourly_forecast,
                "daily_forecast": daily_forecast,
            }
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
            _LOGGER.exception(
                "Error inesperado al obtener datos de predicción (Town ID: %s): %s",
                self.town_id,
                err,
            )
            raise
