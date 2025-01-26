from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
import aiofiles

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client, config_validation as cv

from .const import (
    DOMAIN,
    CONF_API_KEY,
    TOWN_NAME,
    TOWN_ID,
    VARIABLE_NAME,
    VARIABLE_ID,
    STATION_NAME,
    STATION_ID,
    STATION_TYPE,
    LATITUDE,
    LONGITUDE,
    ALTITUDE,
    REGION_ID,
    REGION_NAME,
    PROVINCE_ID,
    PROVINCE_NAME,
    STATION_STATUS,
    LIMIT_XEMA,
	LIMIT_PREDICCIO
)
    
from .options_flow import MeteocatOptionsFlowHandler
from meteocatpy.town import MeteocatTown
from meteocatpy.symbols import MeteocatSymbols
from meteocatpy.variables import MeteocatVariables
from meteocatpy.townstations import MeteocatTownStations
from meteocatpy.infostation import MeteocatInfoStation

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
        self._cache = {}

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
        """Descarga y guarda los símbolos y variables después de seleccionar el municipio."""

        errors = {}

        # Crear directorio de activos (assets) si no existe
        assets_dir = os.path.join(
            self.hass.config.path(),
            "custom_components",
            "meteocat",
            "assets"
        )
        os.makedirs(assets_dir, exist_ok=True)

        # Rutas para los archivos de símbolos y variables
        symbols_file = os.path.join(assets_dir, "symbols.json")
        variables_file = os.path.join(assets_dir, "variables.json")

        try:
            # Descargar y guardar los símbolos
            symbols_client = MeteocatSymbols(self.api_key)
            symbols_data = await symbols_client.fetch_symbols()

            async with aiofiles.open(symbols_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"symbols": symbols_data}, ensure_ascii=False, indent=4))
            
            _LOGGER.info(f"Símbolos guardados en {symbols_file}")

            # Descargar y guardar las variables
            variables_client = MeteocatVariables(self.api_key)
            variables_data = await variables_client.get_variables()

            async with aiofiles.open(variables_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"variables": variables_data}, ensure_ascii=False, indent=4))

            _LOGGER.info(f"Variables guardadas en {variables_file}")

            # Buscar la variable de temperatura
            self.variable_id = next(
                (v["codi"] for v in variables_data if v["nom"].lower() == "temperatura"), None
            )
            if not self.variable_id:
                _LOGGER.error("No se encontró la variable 'Temperatura'")
                errors["base"] = "variable_not_found"
        except (BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError) as ex:
            _LOGGER.error("Error al conectar con la API de Meteocat: %s", ex)
            errors["base"] = "cannot_connect"
        except Exception as ex:
            _LOGGER.error("Error inesperado al descargar los datos: %s", ex)
            errors["base"] = "unknown"

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

                # Obtener metadatos de la estación
                infostation_client = MeteocatInfoStation(self.api_key)
                try:
                    station_metadata = await infostation_client.get_infostation(self.station_id)
                    # Extraer los valores necesarios de los metadatos
                    self.station_type = station_metadata.get("tipus", "")
                    self.latitude = station_metadata.get("coordenades", {}).get("latitud", 0.0)
                    self.longitude = station_metadata.get("coordenades", {}).get("longitud", 0.0)
                    self.altitude = station_metadata.get("altitud", 0)
                    self.region_id = station_metadata.get("comarca", {}).get("codi", "")
                    self.region_name = station_metadata.get("comarca", {}).get("nom", "")
                    self.province_id = station_metadata.get("provincia", {}).get("codi", "")
                    self.province_name = station_metadata.get("provincia", {}).get("nom", "")
                    self.station_status = station_metadata.get("estats", [{}])[0].get("codi", "")
                    return await self.async_step_set_api_limits()
                except Exception as ex:
                    _LOGGER.error("Error al obtener los metadatos de la estación: %s", ex)
                    errors["base"] = "metadata_fetch_failed"
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
        
    async def async_step_set_api_limits(self, user_input=None):
        """Cuarto paso: Introducir los límites de XEMA y PREDICCIO del plan de la API."""
        errors = {}

        if user_input is not None:
            self.limit_xema = user_input.get(LIMIT_XEMA, 750)
            self.limit_prediccio = user_input.get(LIMIT_PREDICCIO, 100)
            return self.async_create_entry(
                title=self.selected_municipi["nom"],
                data={
                    CONF_API_KEY: self.api_key,
                    TOWN_NAME: self.selected_municipi["nom"],
                    TOWN_ID: self.selected_municipi["codi"],
                    VARIABLE_NAME: "Temperatura",
                    VARIABLE_ID: str(self.variable_id),
                    STATION_NAME: self.station_name,
                    STATION_ID: self.station_id,
                    STATION_TYPE: self.station_type,
                    LATITUDE: self.latitude,
                    LONGITUDE: self.longitude,
                    ALTITUDE: self.altitude,
                    REGION_ID: str(self.region_id),
                    REGION_NAME: self.region_name,
                    PROVINCE_ID: str(self.province_id),
                    PROVINCE_NAME: self.province_name,
                    STATION_STATUS: str(self.station_status),
                    LIMIT_XEMA: self.limit_xema,
                    LIMIT_PREDICCIO: self.limit_prediccio,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(LIMIT_XEMA, default=750): cv.positive_int,
                vol.Required(LIMIT_PREDICCIO, default=100): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="set_api_limits", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MeteocatOptionsFlowHandler:
        """Devuelve el flujo de opciones para esta configuración."""
        return MeteocatOptionsFlowHandler(config_entry)
