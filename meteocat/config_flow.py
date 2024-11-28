from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
import aiofiles

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client, config_validation as cv

from .const import DEFAULT_NAME, DOMAIN
from meteocatpy.town import MeteocatTown
from meteocatpy.symbols import MeteocatSymbols
from meteocatpy.variables import MeteocatVariables
from meteocatpy.townstations import MeteocatTownStations
from meteocatpy.exceptions import BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError

_LOGGER = logging.getLogger(__name__)

class MeteocatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Flujo de configuración para Meteocat."""

    VERSION = 1

    def __init__(self):
        self.api_key: str | None = None
        self.municipis: list[dict[str, Any]] = []
        self.selected_municipi: dict[str, Any] | None = None
        self.variable_id: str | None = None
        self.station_id: str | None = None
        self.station_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Primer paso: Solicitar la API Key."""
        errors = {}

        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]

            town_client = MeteocatTown(self.api_key)

            try:
                self.municipis = await town_client.get_municipis()
            except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
                _LOGGER.error("Error al conectar con la API de Meteocat: %s", ex)
                errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Error inesperado al validar la API Key: %s", ex)
                errors["base"] = "unknown"

            if not errors:
                return await self.async_step_select_municipi()

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_municipi(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Segundo paso: Seleccionar el municipio."""
        errors = {}

        if user_input is not None:
            selected_codi = user_input["municipi"]
            self.selected_municipi = next(
                (m for m in self.municipis if m["codi"] == selected_codi), None
            )

            if self.selected_municipi:
                await self.fetch_symbols_and_variables()

        if not errors and self.selected_municipi:
            return await self.async_step_select_station()

        schema = vol.Schema(
            {vol.Required("municipi"): vol.In({m["codi"]: m["nom"] for m in self.municipis})}
        )

        return self.async_show_form(step_id="select_municipi", data_schema=schema, errors=errors)

    async def fetch_symbols_and_variables(self):
        """Descarga los símbolos y las variables después de seleccionar el municipio."""

        errors = {}

        # Descargar y guardar los símbolos
        assets_dir = Path(__file__).parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        symbols_file = assets_dir / "symbols.json"
        symbols_client = MeteocatSymbols(self.api_key)

        try:
            symbols_data = await symbols_client.fetch_symbols()
            async with aiofiles.open(symbols_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"symbols": symbols_data}, ensure_ascii=False, indent=4))
        except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
            _LOGGER.error("Error al descargar o guardar los símbolos: %s", ex)
            errors["base"] = "symbols_download_failed"

        if not errors:
            variables_client = MeteocatVariables(self.api_key)
            try:
                variables_data = await variables_client.get_variables()
                self.variable_id = next(
                    (v["codi"] for v in variables_data if v["nom"].lower() == "temperatura"), None
                )
                if not self.variable_id:
                    _LOGGER.error("No se encontró la variable 'Temperatura'")
                    errors["base"] = "variable_not_found"
            except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
                _LOGGER.error("Error al obtener las variables: %s", ex)
                errors["base"] = "variables_fetch_failed"

        if errors:
            raise HomeAssistantError(errors)

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tercer paso: Seleccionar la estación para la variable seleccionada."""
        errors = {}

        townstations_client = MeteocatTownStations(self.api_key)
        try:
            stations_data = await townstations_client.get_town_stations(
                self.selected_municipi["codi"], self.variable_id
            )
        except Exception as ex:
            _LOGGER.error("Error al obtener las estaciones: %s", ex)
            errors["base"] = "stations_fetch_failed"
            stations_data = []

        if user_input is not None:
            selected_station_codi = user_input["station"]
            selected_station = next(
                (station for station in stations_data[0]["variables"][0]["estacions"] if station["codi"] == selected_station_codi),
                None
            )

            if selected_station:
                self.station_id = selected_station["codi"]
                self.station_name = selected_station["nom"]

                return self.async_create_entry(
                    title=self.selected_municipi["nom"],
                    data={
                        CONF_API_KEY: self.api_key,
                        "town_name": self.selected_municipi["nom"],
                        "town_id": self.selected_municipi["codi"],
                        "variable_name": "Temperatura",
                        "variable_id": self.variable_id,
                        "station_name": self.station_name,
                        "station_id": self.station_id
                    },
                )
            else:
                errors["base"] = "station_not_found"

        schema = vol.Schema(
            {
                vol.Required("station"): vol.In(
                    {station["codi"]: station["nom"] for station in stations_data[0]["variables"][0]["estacions"]}
                )
            }
        )

        return self.async_show_form(
            step_id="select_station", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ConfigFlowResult:
        """Devuelve el flujo de opciones para esta configuración."""
        return MeteocatOptionsFlowHandler(config_entry)
