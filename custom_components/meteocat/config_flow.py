from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import voluptuous as vol
import aiofiles
import unicodedata

from astral import LocationInfo
from astral.sun import sun
from .moon import moon_phase, moon_rise_set
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .helpers import get_storage_dir
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
    LIMIT_QUOTA,
    LIMIT_BASIC,
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

# Definir la zona horaria local
TIMEZONE = ZoneInfo("Europe/Madrid")

INITIAL_TEMPLATE = {
    "actualitzat": {"dataUpdate": "1970-01-01T00:00:00+00:00"},
    "dades": []
}

def normalize_name(name: str) -> str:
    """Normaliza el nombre eliminando acentos y convirtiendo a minúsculas."""
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    return name.lower()

def _get_moon_phase_name(phase: float) -> str:
    """Convierte el valor numérico de la fase lunar en un nombre descriptivo."""
    if 0 <= phase < 7:
        return "new_moon"
    elif 7 <= phase < 14:
        return "first_quarter"
    elif 14 <= phase < 21:
        return "full_moon"
    elif 21 <= phase < 28:
        return "last_quarter"
    return "unknown"

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
        self.region_name: str | None = None
        self.province_id: str | None = None
        self.province_name: str | None = None
        self.station_type: str | None = None
        self.latitude: float | None = None
        self.longitude: float | None = None
        self.altitude: float | None = None
        self.station_status: str | None = None

    async def fetch_and_save_quotes(self, api_key: str):
        """Obtiene las cuotas de la API de Meteocat y las guarda en quotes.json."""
        meteocat_quotes = MeteocatQuotes(api_key)
        quotes_dir = get_storage_dir(self.hass, "files")
        quotes_file = quotes_dir / "quotes.json"

        try:
            data = await asyncio.wait_for(meteocat_quotes.get_quotes(), timeout=30)

            plan_mapping = {
                "xdde_": "XDDE",
                "prediccio_": "Prediccio",
                "referencia basic": "Basic",
                "xema_": "XEMA",
                "quota": "Quota",
            }

            modified_plans = []
            for plan in data["plans"]:
                normalized_nom = normalize_name(plan["nom"])
                new_name = next(
                    (v for k, v in plan_mapping.items() if normalized_nom.startswith(k)), None
                )
                if new_name is None:
                    _LOGGER.warning(
                        "Nombre de plan desconocido en la API: %s (se usará el original)",
                        plan["nom"],
                    )
                    new_name = plan["nom"]

                modified_plans.append(
                    {
                        "nom": new_name,
                        "periode": plan["periode"],
                        "maxConsultes": plan["maxConsultes"],
                        "consultesRestants": plan["consultesRestants"],
                        "consultesRealitzades": plan["consultesRealitzades"],
                    }
                )

            current_time = datetime.now(timezone.utc).astimezone(TIMEZONE).isoformat()
            data_with_timestamp = {
                "actualitzat": {"dataUpdate": current_time},
                "client": data["client"],
                "plans": modified_plans,
            }

            async with aiofiles.open(quotes_file, "w", encoding="utf-8") as file:
                await file.write(
                    json.dumps(data_with_timestamp, ensure_ascii=False, indent=4)
                )
            _LOGGER.info("Cuotas guardadas exitosamente en %s", quotes_file)

        except Exception as ex:
            _LOGGER.error("Error al obtener o guardar las cuotas: %s", ex)
            raise HomeAssistantError("No se pudieron obtener las cuotas de la API")

    async def create_alerts_file(self):
        """Crea los archivos de alertas global y regional si no existen."""
        alerts_dir = get_storage_dir(self.hass, "files")

        # Archivo global de alertas
        alerts_file = alerts_dir / "alerts.json"
        if not alerts_file.exists():
            async with aiofiles.open(alerts_file, "w", encoding="utf-8") as file:
                await file.write(
                    json.dumps(INITIAL_TEMPLATE, ensure_ascii=False, indent=4)
                )
            _LOGGER.info("Archivo global %s creado con plantilla inicial", alerts_file)

        # Solo si existe region_id
        if self.region_id:
            # Archivo regional de alertas
            alerts_region_file = alerts_dir / f"alerts_{self.region_id}.json"
            if not alerts_region_file.exists():
                async with aiofiles.open(alerts_region_file, "w", encoding="utf-8") as file:
                    await file.write(
                        json.dumps(INITIAL_TEMPLATE, ensure_ascii=False, indent=4)
                    )
                _LOGGER.info(
                    "Archivo regional %s creado con plantilla inicial", alerts_region_file
                )

            # Archivo lightning regional
            lightning_file = alerts_dir / f"lightning_{self.region_id}.json"
            if not lightning_file.exists():
                async with aiofiles.open(lightning_file, "w", encoding="utf-8") as file:
                    await file.write(
                        json.dumps(INITIAL_TEMPLATE, ensure_ascii=False, indent=4)
                    )
                _LOGGER.info(
                    "Archivo lightning %s creado con plantilla inicial", lightning_file
                )

    async def create_sun_file(self):
        """Crea el archivo sun_{town_id}_data.json con datos iniciales de sunrise y sunset."""
        if not self.selected_municipi or not self.latitude or not self.longitude:
            _LOGGER.warning("No se puede crear sun_{town_id}_data.json: faltan municipio o coordenadas")
            return

        town_id = self.selected_municipi["codi"]
        files_dir = get_storage_dir(self.hass, "files")
        sun_file = files_dir / f"sun_{town_id}_data.json"

        if not sun_file.exists():
            try:
                # Crear objeto LocationInfo con las coordenadas y zona horaria
                location = LocationInfo(
                    name=self.selected_municipi["nom"],
                    region="Catalonia",
                    timezone="Europe/Madrid",
                    latitude=self.latitude,
                    longitude=self.longitude
                )

                # Calcular sunrise y sunset para el día actual
                current_time = datetime.now(timezone.utc).astimezone(TIMEZONE)
                sun_data = sun(location.observer, date=current_time.date(), tzinfo=TIMEZONE)

                # Formatear los datos para el archivo
                sun_data_formatted = {
                    "actualitzat": {"dataUpdate": current_time.isoformat()},
                    "dades": [
                        {
                            "sunrise": sun_data["sunrise"].isoformat(),
                            "sunset": sun_data["sunset"].isoformat(),
                            "date": current_time.date().isoformat()
                        }
                    ]
                }

                # Guardar el archivo
                async with aiofiles.open(sun_file, "w", encoding="utf-8") as file:
                    await file.write(json.dumps(sun_data_formatted, ensure_ascii=False, indent=4))
                _LOGGER.info("Archivo sun_%s_data.json creado con datos iniciales", town_id)

            except Exception as ex:
                _LOGGER.error("Error al crear sun_%s_data.json: %s", town_id, ex)

    async def create_moon_file(self):
        """Crea el archivo moon_{town_id}_data.json con datos iniciales de la fase lunar, moonrise y moonset."""
        if not self.selected_municipi or not self.latitude or not self.longitude:
            _LOGGER.warning("No se puede crear moon_{town_id}_data.json: faltan municipio o coordenadas")
            return

        town_id = self.selected_municipi["codi"]
        files_dir = get_storage_dir(self.hass, "files")
        moon_file = files_dir / f"moon_{town_id}_data.json"

        if not moon_file.exists():
            try:
                # Fecha actual en UTC
                current_time = datetime.now(timezone.utc).astimezone(TIMEZONE)
                today = current_time.date()

                # Fase lunar usando nuestro módulo
                phase = moon_phase(today)

                # Nombres de fase
                moon_phase_name = _get_moon_phase_name(phase)

                # Moonrise y moonset aproximados (UTC)
                rise_utc, set_utc = moon_rise_set(self.latitude, self.longitude, today)

                # Convertir a ISO y a TZ local si existen
                rise_local = rise_utc.astimezone(TIMEZONE).isoformat() if rise_utc else None
                set_local = set_utc.astimezone(TIMEZONE).isoformat() if set_utc else None

                # Formatear datos para guardar
                moon_data_formatted = {
                    "actualitzat": {"dataUpdate": current_time.isoformat()},
                    "dades": [
                        {
                            "moon_phase": phase,
                            "moon_phase_name": moon_phase_name,
                            "moonrise": rise_local,
                            "moonset": set_local,
                            "date": today.isoformat()
                        }
                    ]
                }

                # Guardar el archivo
                async with aiofiles.open(moon_file, "w", encoding="utf-8") as file:
                    await file.write(json.dumps(moon_data_formatted, ensure_ascii=False, indent=4))
                _LOGGER.info("Archivo moon_%s_data.json creado con datos iniciales", town_id)

            except Exception as ex:
                _LOGGER.error("Error al crear moon_%s_data.json: %s", town_id, ex)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Primer paso: solicitar API Key."""
        errors = {}
        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]
            town_client = MeteocatTown(self.api_key)
            try:
                self.municipis = await town_client.get_municipis()

                # Guardar lista de municipios en towns.json
                assets_dir = get_storage_dir(self.hass, "assets")
                towns_file = assets_dir / "towns.json"
                async with aiofiles.open(towns_file, "w", encoding="utf-8") as file:
                    await file.write(json.dumps({"towns": self.municipis}, ensure_ascii=False, indent=4))
                _LOGGER.info("Towns guardados en %s", towns_file)

                # Crea el archivo de cuotas
                await self.fetch_and_save_quotes(self.api_key)
                # Crea solo el archivo global de alertas (regional se hará después)
                await self.create_alerts_file()
            except Exception as ex:
                _LOGGER.error("Error al conectar con la API de Meteocat: %s", ex)
                errors["base"] = "cannot_connect"
            if not errors:
                return await self.async_step_select_municipi()

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_municipi(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Segundo paso: seleccionar el municipio."""
        errors = {}
        if user_input is not None:
            selected_codi = user_input["municipi"]
            self.selected_municipi = next(
                (m for m in self.municipis if m["codi"] == selected_codi), None
            )
            if self.selected_municipi:
                await self.fetch_symbols_and_variables()

        if self.selected_municipi:
            return await self.async_step_select_station()

        schema = vol.Schema(
            {vol.Required("municipi"): vol.In({m["codi"]: m["nom"] for m in self.municipis})}
        )
        return self.async_show_form(step_id="select_municipi", data_schema=schema, errors=errors)

    async def fetch_symbols_and_variables(self):
        """Descarga y guarda los símbolos y variables después de seleccionar el municipio."""
        assets_dir = get_storage_dir(self.hass, "assets")
        symbols_file = assets_dir / "symbols.json"
        variables_file = assets_dir / "variables.json"
        try:
            symbols_data = await MeteocatSymbols(self.api_key).fetch_symbols()
            async with aiofiles.open(symbols_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"symbols": symbols_data}, ensure_ascii=False, indent=4))

            variables_data = await MeteocatVariables(self.api_key).get_variables()
            async with aiofiles.open(variables_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"variables": variables_data}, ensure_ascii=False, indent=4))

            self.variable_id = next(
                (v["codi"] for v in variables_data if v["nom"].lower() == "temperatura"),
                None,
            )
        except json.JSONDecodeError as ex:
            _LOGGER.error("Archivo existente corrupto al cargar símbolos/variables: %s", ex)
            raise HomeAssistantError("Archivo corrupto de símbolos o variables")
        except Exception as ex:
            _LOGGER.error("Error al descargar símbolos o variables: %s", ex)
            raise HomeAssistantError("No se pudieron obtener símbolos o variables")

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tercer paso: seleccionar estación."""
        errors = {}
        townstations_client = MeteocatTownStations(self.api_key)

        try:
            # Obtener la lista completa de estaciones de la API
            all_stations = await townstations_client.stations_service.get_stations()
            assets_dir = get_storage_dir(self.hass, "assets")
            stations_file = assets_dir / "stations.json"
            async with aiofiles.open(stations_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"stations": all_stations}, ensure_ascii=False, indent=4))
            _LOGGER.info("Lista completa de estaciones guardadas en %s", stations_file)

            # Obtener estaciones filtradas por municipio y variable
            stations_data = await townstations_client.get_town_stations(
                self.selected_municipi["codi"], self.variable_id
            )

            town_stations_file = assets_dir / f"stations_{self.selected_municipi['codi']}.json"
            async with aiofiles.open(town_stations_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps({"town_stations": stations_data}, ensure_ascii=False, indent=4))
            _LOGGER.info("Lista de estaciones del municipio guardadas en %s", town_stations_file)

        except Exception as ex:
            _LOGGER.error("Error al obtener las estaciones: %s", ex)
            errors["base"] = "stations_fetch_failed"
            stations_data = []

        if not stations_data or "variables" not in stations_data[0]:
            errors["base"] = "no_stations"
            return self.async_show_form(step_id="select_station", errors=errors)

        if user_input is not None:
            selected_station_codi = user_input["station"]
            selected_station = next(
                (station for station in stations_data[0]["variables"][0]["estacions"]
                 if station["codi"] == selected_station_codi),
                None,
            )
            if selected_station:
                self.station_id = selected_station["codi"]
                self.station_name = selected_station["nom"]

                # Obtener metadatos de la estación
                try:
                    station_metadata = await MeteocatInfoStation(self.api_key).get_infostation(self.station_id)
                    self.station_type = station_metadata.get("tipus", "")
                    self.latitude = station_metadata.get("coordenades", {}).get("latitud", 0.0)
                    self.longitude = station_metadata.get("coordenades", {}).get("longitud", 0.0)
                    self.altitude = station_metadata.get("altitud", 0)
                    self.region_id = station_metadata.get("comarca", {}).get("codi", "")
                    self.region_name = station_metadata.get("comarca", {}).get("nom", "")
                    self.province_id = station_metadata.get("provincia", {}).get("codi", "")
                    self.province_name = station_metadata.get("provincia", {}).get("nom", "")
                    self.station_status = station_metadata.get("estats", [{}])[0].get("codi", "")

                    # Crear archivos de alertas, sol y luna
                    await self.create_alerts_file()
                    await self.create_sun_file()
                    await self.create_moon_file()
                    return await self.async_step_set_api_limits()
                except Exception as ex:
                    _LOGGER.error("Error al obtener los metadatos de la estación: %s", ex)
                    errors["base"] = "metadata_fetch_failed"
            else:
                errors["base"] = "station_not_found"

        schema = vol.Schema(
            {vol.Required("station"): vol.In(
                {station["codi"]: station["nom"] for station in stations_data[0]["variables"][0]["estacions"]}
            )}
        )
        return self.async_show_form(step_id="select_station", data_schema=schema, errors=errors)

    async def async_step_set_api_limits(self, user_input=None):
        """Cuarto paso: límites de la API."""
        errors = {}
        if user_input is not None:
            self.limit_xema = user_input.get(LIMIT_XEMA, 750)
            self.limit_prediccio = user_input.get(LIMIT_PREDICCIO, 100)
            self.limit_xdde = user_input.get(LIMIT_XDDE, 250)
            self.limit_quota = user_input.get(LIMIT_QUOTA, 300)
            self.limit_basic = user_input.get(LIMIT_BASIC, 2000)

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

        schema = vol.Schema({
            vol.Required(LIMIT_XEMA, default=750): cv.positive_int,
            vol.Required(LIMIT_PREDICCIO, default=100): cv.positive_int,
            vol.Required(LIMIT_XDDE, default=250): cv.positive_int,
            vol.Required(LIMIT_QUOTA, default=300): cv.positive_int,
            vol.Required(LIMIT_BASIC, default=2000): cv.positive_int,
        })
        return self.async_show_form(step_id="set_api_limits", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MeteocatOptionsFlowHandler:
        """Devuelve el flujo de opciones para esta configuración."""
        return MeteocatOptionsFlowHandler(config_entry)