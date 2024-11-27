from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_API_KEY

from .const import DOMAIN
from meteocatpy.townstations import MeteocatTownStations
from meteocatpy.variables import MeteocatVariables
from meteocatpy.exceptions import BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError
from .config_flow import MeteocatConfigFlow

_LOGGER = logging.getLogger(__name__)

class MeteocatOptionsFlowHandler:
    """Clase para manejar el flujo de opciones de configuración de la integración Meteocat."""

    def __init__(self, config_entry: ConfigEntry):
        """Inicializa el flujo con la configuración existente."""
        self.config_entry = config_entry
        self.api_key = config_entry.data.get(CONF_API_KEY)
        self.station_id = config_entry.data.get("station_id")
        self.station_name = config_entry.data.get("station_name")
        self.variable_id = config_entry.data.get("variable_id")

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Paso donde el usuario puede actualizar opciones de la configuración."""
        errors = {}

        # Si el usuario ha proporcionado entradas
        if user_input is not None:
            if CONF_API_KEY in user_input:
                self.api_key = user_input[CONF_API_KEY]
                # Validar la nueva API Key
                if not await self._validate_api_key(self.api_key):
                    errors[CONF_API_KEY] = "Invalid API Key"
                    return self.async_show_form(step_id="user", data_schema=self._get_options_schema(), errors=errors)

            if "station" in user_input:
                self.station_id = user_input["station"]
                self.station_name = user_input.get("station_name", self.station_name)

                # Actualizar la configuración con la nueva estación
                self.config_entry.data["station_id"] = self.station_id
                self.config_entry.data["station_name"] = self.station_name

            if "variable" in user_input:
                self.variable_id = user_input["variable"]
                # Actualizar la configuración con la nueva variable
                self.config_entry.data["variable_id"] = self.variable_id

            # Almacenamos los cambios y cerramos el flujo
            self.config_entry.async_update()

            return self.async_create_entry(title="Meteocat", data=self.config_entry.data)

        # Si no hay entradas del usuario, continuamos con la solicitud de opciones
        schema = self._get_options_schema()
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _get_options_schema(self):
        """Genera el esquema para las opciones del formulario."""
        # Aquí, obtendremos las estaciones y variables disponibles para la configuración
        stations = self._get_stations()
        variables = self._get_variables()

        return vol.Schema(
            {
                vol.Optional("station", default=self.station_id): vol.In(
                    {station["codi"]: station["nom"] for station in stations}
                ),
                vol.Optional("variable", default=self.variable_id): vol.In(
                    {variable["codi"]: variable["nom"] for variable in variables}
                ),
                vol.Optional(CONF_API_KEY, default=self.api_key): str,  # Opción para introducir una nueva API Key
            }
        )

    async def _validate_api_key(self, api_key: str) -> bool:
        """Valida si la API Key es correcta al intentar conectarse con la API de Meteocat."""
        try:
            # Intentamos obtener los municipios con la API Key proporcionada
            town_client = MeteocatTownStations(api_key)
            await town_client.get_town_stations(self.config_entry.data["town_id"], self.variable_id)
            return True  # Si no hay errores, la clave es válida
        except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
            _LOGGER.error("Error al validar la API Key: %s", ex)
            return False
        except Exception as ex:
            _LOGGER.error("Error inesperado al validar la API Key: %s", ex)
            return False

    async def _get_stations(self):
        """Obtiene las estaciones disponibles para el municipio y variable actuales."""
        try:
            townstations_client = MeteocatTownStations(self.api_key)
            stations_data = await townstations_client.get_town_stations(self.config_entry.data["town_id"], self.variable_id)
            return stations_data[0]["variables"][0]["estacions"]
        except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
            _LOGGER.error("Error al obtener las estaciones: %s", ex)
            return []

    async def _get_variables(self):
        """Obtiene las variables disponibles para el municipio actual."""
        try:
            variables_client = MeteocatVariables(self.api_key)
            variables_data = await variables_client.get_variables()
            return variables_data
        except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
            _LOGGER.error("Error al obtener las variables: %s", ex)
            return []
