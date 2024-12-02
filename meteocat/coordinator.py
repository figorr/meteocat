from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryNotReady

from meteocatpy.data import MeteocatStationData
from meteocatpy.exceptions import (
    BadRequestError,
    ForbiddenError,
    TooManyRequestsError,
    InternalServerError,
    UnknownAPIError,
)

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class MeteocatCoordinator(DataUpdateCoordinator):
    """Coordinator para manejar la actualización de datos de la API de Meteocat."""

    def __init__(self, hass: HomeAssistant, api_key: str, station_id: str):
        """Inicializa el coordinador de datos."""
        self.api_key = api_key
        self.station_id = station_id
        self.meteocat_station_data = MeteocatStationData(api_key)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} Coordinator",
            update_interval=timedelta(minutes=90),  # Intervalo de actualización de 90 minutos
        )

    async def _async_update_data(self):
        """
        Actualiza los datos de la estación meteorológica desde la API de Meteocat.

        Returns:
            dict: Datos actualizados de la estación.
        """
        try:
            # Obtiene los datos de la estación organizados por variables
            return await self.meteocat_station_data.get_station_data_with_variables(
                self.station_id
            )
        except ForbiddenError as err:
            _LOGGER.error("Acceso denegado: %s", err)
            raise ConfigEntryNotReady from err
        except TooManyRequestsError as err:
            _LOGGER.warning("Límite de solicitudes alcanzado: %s", err)
            raise ConfigEntryNotReady from err
        except (BadRequestError, InternalServerError, UnknownAPIError) as err:
            _LOGGER.error("Error al obtener datos de Meteocat: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Error inesperado: %s", err)
            raise
