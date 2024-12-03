from __future__ import annotations

import logging
from datetime import timedelta

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


class MeteocatSensorCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de los sensores."""

    def __init__(self, hass: HomeAssistant, api_key: str, station_id: str):
        """Inicializa el coordinador de datos para sensores."""
        self.api_key = api_key
        self.station_id = station_id
        self.meteocat_station_data = MeteocatStationData(api_key)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Sensor Coordinator",
            update_interval=timedelta(minutes=30),  # Intervalo de actualización de 30 minutos
        )

    async def _async_update_data(self):
        """
        Actualiza los datos de los sensores desde la API de Meteocat.

        Returns:
            dict: Datos actualizados de los sensores.
        """
        try:
            return await self.meteocat_station_data.get_station_data_with_variables(self.station_id)
        except ForbiddenError as err:
            _LOGGER.error("Acceso denegado al obtener datos de sensores: %s", err)
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning("Límite de solicitudes alcanzado al obtener datos de sensores: %s", err)
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error("Error al obtener datos de sensores: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Error inesperado al obtener datos de sensores: %s", err)
            raise


class MeteocatEntityCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de las entidades de predicción."""

    def __init__(self, hass: HomeAssistant, api_key: str, town_id: str):
        """Inicializa el coordinador de datos para entidades de predicción."""
        self.api_key = api_key
        self.town_id = town_id
        self.meteocat_forecast = MeteocatForecast(api_key)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Entity Coordinator",
            update_interval=timedelta(hours=12),  # Intervalo de actualización de 3 horas
        )

    async def _async_update_data(self):
        """
        Actualiza los datos de las entidades de predicción desde la API de Meteocat.

        Returns:
            dict: Datos actualizados de predicción horaria y diaria.
        """
        try:
            return {
                "hourly_forecast": await self.meteocat_forecast.get_prediccion_horaria(self.town_id),
                "daily_forecast": await self.meteocat_forecast.get_prediccion_diaria(self.town_id),
            }
        except ForbiddenError as err:
            _LOGGER.error("Acceso denegado al obtener datos de predicción: %s", err)
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning("Límite de solicitudes alcanzado al obtener datos de predicción: %s", err)
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error("Error al obtener datos de predicción: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Error inesperado al obtener datos de predicción: %s", err)
            raise
