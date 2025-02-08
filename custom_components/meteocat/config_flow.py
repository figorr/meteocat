from __future__ import annotations

import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import voluptuous as vol
from aiohttp import ClientError
import aiofiles
import unicodedata

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
	LIMIT_PREDICCIO,
    LIMIT_XDDE,
    LIMIT_BASIC,
    LIMIT_QUOTA
)
    
from .options_flow import MeteocatOptionsFlowHandler
from meteocatpy.town import MeteocatTown
from meteocatpy.symbols import MeteocatSymbols
from meteocatpy.variables import MeteocatVariables
from meteocatpy.townstations import MeteocatTownStations
from meteocatpy.infostation import MeteocatInfoStation
from meteocatpy.quotes import MeteocatQuotes

from meteocatpy.exceptions import BadRequestError, ForbiddenError, TooManyRequestsError, InternalServerError, UnknownAPIError

_LOGGER = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("Europe/Madrid")

def normalize_name(name):
    """Normaliza el nombre eliminando acentos y convirtiendo a minúsculas."""
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    return name.lower()

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
        self.region_id: str | None = None
        self._cache = {}

    async def fetch_and_save_quotes(self, api_key):
        """Obtiene las cuotas de la API de Meteocat y las guarda en quotes.json."""
        meteocat_quotes = MeteocatQuotes(api_key)
        quotes_dir = os.path.join(
            self.hass.config.path(),
            "custom_components",
            "meteocat",
            "files"
        )
        os.makedirs(quotes_dir, exist_ok=True)
        quotes_file = os.path.join(quotes_dir, "quotes.json")

        try:
            data = await asyncio.wait_for(
                meteocat_quotes.get_quotes(),
                timeout=30
            )
            
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

            # Guardar los datos en el archivo JSON
            async with aiofiles.open(quotes_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps(data_with_timestamp, ensure_ascii=False, indent=4))
            
            _LOGGER.info("Cuotas guardadas exitosamente en %s", quotes_file)

        except Exception as ex:
            _LOGGER.error("Error al obtener o guardar las cuotas: %s", ex)
            raise HomeAssistantError("No se pudieron obtener las cuotas de la API")
    
    async def create_alerts_file(self):
        """Crea el archivo alerts.json si no existe."""
        alerts_dir = os.path.join(
            self.hass.config.path(),
            "custom_components",
            "meteocat",
            "files"
        )
        os.makedirs(alerts_dir, exist_ok=True)
        alerts_file = os.path.join(alerts_dir, "alerts.json")

        if not os.path.exists(alerts_file):
            initial_data = {
                "actualitzat": {
                    "dataUpdate": "1970-01-01T00:00:00+00:00"
                },
                "dades": []
            }
            async with aiofiles.open(alerts_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps(initial_data, ensure_ascii=False, indent=4))
            
            _LOGGER.info("Archivo alerts.json creado en %s", alerts_file)
    
    async def create_lightning_file(self):
        """Crea el archivo lightning_{self.region_id}.json si no existe."""
        lightning_dir = os.path.join(
            self.hass.config.path(),
            "custom_components",
            "meteocat",
            "files"
        )
        os.makedirs(lightning_dir, exist_ok=True)
        lightning_file = os.path.join(lightning_dir, f"lightning_{self.region_id}.json")

        if not os.path.exists(lightning_file):
            initial_data = {
                "actualitzat": {
                    "dataUpdate": "1970-01-01T00:00:00+00:00"
                },
                "dades": []
            }
            async with aiofiles.open(lightning_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps(initial_data, ensure_ascii=False, indent=4))
            
            _LOGGER.info("Archivo %s creado", lightning_file)

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
                # Aquí obtenemos y guardamos las cuotas
                await self.fetch_and_save_quotes(self.api_key)
                # Aquí creamos el archivo alerts.json si no existe
                await self.create_alerts_file()
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

                    # Crear el archivo lightning después de obtener region_id
                    await self.create_lightning_file()
                    
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
            self.limit_xdde = user_input.get(LIMIT_XDDE, 250)
            self.limit_quota = user_input.get(LIMIT_QUOTA, 300)
            self.limit_basic = user_input.get(LIMIT_BASIC, 300)
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
                    LIMIT_XDDE: self.limit_xdde,
                    LIMIT_QUOTA: self.limit_quota,
                    LIMIT_BASIC: self.limit_basic,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(LIMIT_XEMA, default=750): cv.positive_int,
                vol.Required(LIMIT_PREDICCIO, default=100): cv.positive_int,
                vol.Required(LIMIT_XDDE, default=250): cv.positive_int,
                vol.Required(LIMIT_QUOTA, default=300): cv.positive_int,
                vol.Required(LIMIT_BASIC, default=2000): cv.positive_int,
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
