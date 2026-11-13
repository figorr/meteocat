from __future__ import annotations

import asyncio
import logging
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from meteocatpy.infostation import MeteocatInfoStation
from meteocatpy.quotes import MeteocatQuotes
from meteocatpy.symbols import MeteocatSymbols
from meteocatpy.town import MeteocatTown
from meteocatpy.townstations import MeteocatTownStations
from meteocatpy.variables import MeteocatVariables
from solarmoonpy.location import Location, LocationInfo
from solarmoonpy.moon import (
    get_lunation_duration,
    get_moon_phase_name,
    illuminated_percentage,
    lunation_number,
    moon_angular_diameter,
    moon_day,
    moon_distance,
    moon_phase,
    moon_rise_set,
)

from .const import (
    ALTITUDE,
    API_KEY_URL,
    CONF_API_KEY,
    CONF_API_KEY_DATE,
    CONF_API_KEY_REMINDER,
    DOMAIN,
    LATITUDE,
    LIMIT_BASIC,
    LIMIT_PREDICCIO,
    LIMIT_QUOTA,
    LIMIT_XDDE,
    LIMIT_XEMA,
    LONGITUDE,
    PROVINCE_ID,
    PROVINCE_NAME,
    REGION_ID,
    REGION_NAME,
    STATION_ID,
    STATION_NAME,
    STATION_STATUS,
    STATION_TYPE,
    TOWN_ID,
    TOWN_NAME,
    VARIABLE_ID,
    VARIABLE_NAME,
)
from .helpers import (
    async_delete_unused_quotes_file,
    async_migrate_legacy_quotes,
    get_quotes_file,
    get_quotes_lock,
    get_storage_dir,
)
from .options_flow import MeteocatOptionsFlowHandler
from .reminder import async_cancel_api_key_reminder
from .util import OptionalDateSelector, is_future_date, parse_issue_date

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

class MeteocatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Flujo de configuración para Meteocat."""

    VERSION = 1

    def __init__(self):
        self.api_key: str | None = None
        self.api_key_date: str | None = None
        self.api_key_reminder: bool = False
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
        self.location: Location | None = None
        self.timezone_str: str | None = None

    async def fetch_and_save_quotes(self, api_key: str):
        """Obtiene las cuotas de la API de Meteocat y las guarda por API key."""
        meteocat_quotes = MeteocatQuotes(
            api_key, async_get_clientsession(self.hass)
        )
        quotes_file = get_quotes_file(self.hass, api_key)

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

            current_time = datetime.now(UTC).astimezone(TIMEZONE).isoformat()
            data_with_timestamp = {
                "actualitzat": {"dataUpdate": current_time},
                "plans": modified_plans,
            }

            async with get_quotes_lock(self.hass, api_key):
                await async_migrate_legacy_quotes(self.hass, api_key)
                await quotes_file.async_write_json(data_with_timestamp)
            _LOGGER.info("Cuotas guardadas exitosamente en %s", quotes_file)

        except Exception as ex:
            _LOGGER.error("Error al obtener o guardar las cuotas: %s", ex)
            raise HomeAssistantError(
                "No se pudieron obtener las cuotas de la API"
            ) from ex

    async def create_alerts_file(self):
        """Crea los archivos de alertas global y regional si no existen."""
        alerts_dir = get_storage_dir(self.hass, "files")

        # Archivo global de alertas
        alerts_file = alerts_dir / "alerts.json"
        if not await alerts_file.async_exists():
            await alerts_file.async_write_json(INITIAL_TEMPLATE)
            _LOGGER.info("Archivo global %s creado con plantilla inicial", alerts_file)

        # Solo si existe region_id
        if self.region_id:
            # Archivo regional de alertas
            alerts_region_file = alerts_dir / f"alerts_{self.region_id}.json"
            if not await alerts_region_file.async_exists():
                await alerts_region_file.async_write_json(INITIAL_TEMPLATE)
                _LOGGER.info(
                    "Archivo regional %s creado con plantilla inicial", alerts_region_file
                )

            # Archivo lightning regional
            lightning_file = alerts_dir / f"lightning_{self.region_id}.json"
            if not await lightning_file.async_exists():
                await lightning_file.async_write_json(INITIAL_TEMPLATE)
                _LOGGER.info(
                    "Archivo lightning %s creado con plantilla inicial", lightning_file
                )

    async def create_sun_file(self):
        """Crea el archivo sun_{town_id}_data.json con eventos solares + posición inicial del sol."""
        if not self.selected_municipi or self.latitude is None or self.longitude is None:
            _LOGGER.warning("No se puede crear sun_{town_id}_data.json: faltan municipio o coordenadas")
            return

        town_id = self.selected_municipi["codi"]
        files_dir = get_storage_dir(self.hass, "files")
        sun_file = files_dir / f"sun_{town_id.lower()}_data.json"

        if await sun_file.async_exists():
            _LOGGER.debug("El archivo %s ya existe, no se crea de nuevo.", sun_file)
            return

        try:
            # ZONA HORARIA DEL HASS
            self.timezone_str = self.hass.config.time_zone or "Europe/Madrid"
            tz = ZoneInfo(self.timezone_str)

            # CREAR UBICACIÓN
            self.location = Location(LocationInfo(
                name=self.selected_municipi.get("nom", "Municipio"),
                region="Spain",
                timezone=self.timezone_str,
                latitude=self.latitude,
                longitude=self.longitude,
                elevation=self.altitude or 0.0,
            ))

            now = datetime.now(tz)
            today = now.date()
            tomorrow = today + timedelta(days=1)

            # EVENTOS HOY Y MAÑANA
            events_today = self.location.sun_events(date=today, local=True)
            events_tomorrow = self.location.sun_events(date=tomorrow, local=True)

            # LÓGICA DE EVENTOS (igual que en el coordinador)
            expected = {}
            events_list = [
                "dawn_astronomical", "dawn_nautical", "dawn_civil",
                "sunrise", "noon", "sunset",
                "dusk_civil", "dusk_nautical", "dusk_astronomical",
                "midnight",
            ]

            for event in events_list:
                event_time = events_today.get(event)
                if event_time and now >= event_time:
                    expected[event] = events_tomorrow.get(event)
                else:
                    expected[event] = event_time

            # daylight_duration según sunrise
            sunrise = expected["sunrise"]
            expected["daylight_duration"] = (
                events_tomorrow["daylight_duration"]
                if sunrise == events_tomorrow["sunrise"]
                else events_today["daylight_duration"]
            )

            # POSICIÓN ACTUAL DEL SOL
            sun_pos = self.location.sun_position(dt=now, local=True)

            # CONSTRUIR DADES 
            dades_dict = {
                "dawn_civil": expected["dawn_civil"].isoformat() if expected["dawn_civil"] else None,
                "dawn_nautical": expected["dawn_nautical"].isoformat() if expected["dawn_nautical"] else None,
                "dawn_astronomical": expected["dawn_astronomical"].isoformat() if expected["dawn_astronomical"] else None,
                "sunrise": expected["sunrise"].isoformat() if expected["sunrise"] else None,
                "noon": expected["noon"].isoformat() if expected["noon"] else None,
                "sunset": expected["sunset"].isoformat() if expected["sunset"] else None,
                "dusk_civil": expected["dusk_civil"].isoformat() if expected["dusk_civil"] else None,
                "dusk_nautical": expected["dusk_nautical"].isoformat() if expected["dusk_nautical"] else None,
                "dusk_astronomical": expected["dusk_astronomical"].isoformat() if expected["dusk_astronomical"] else None,
                "midnight": expected["midnight"].isoformat() if expected["midnight"] else None,
                "daylight_duration": expected["daylight_duration"],

                # CAMPOS DE POSICIÓN SOLAR
                "sun_elevation": round(sun_pos["elevation"], 2),
                "sun_azimuth": round(sun_pos["azimuth"], 2),
                "sun_horizon_position": sun_pos["horizon_position"],
                "sun_rising": sun_pos["rising"],
                "sun_position_updated": now.isoformat(),
            }

            # JSON FINAL
            data_with_timestamp = {
                "actualitzat": {"dataUpdate": now.isoformat()},
                "dades": [dades_dict],
            }

            # GUARDAR
            await sun_file.async_write_json(data_with_timestamp)

            _LOGGER.info(
                "Archivo sun_%s_data.json creado con eventos + posición solar inicial (elev=%.2f°, az=%.2f°)",
                town_id, sun_pos["elevation"], sun_pos["azimuth"]
            )

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

        if not await moon_file.async_exists():
            try:
                # Fecha actual en UTC
                current_time = datetime.now(UTC).astimezone(TIMEZONE)
                today = current_time.date()

                # Inicializar parámetros con valores por defecto
                phase = None
                moon_day_today = None
                lunation = None
                illuminated = None
                distance = None
                angular_diameter = None
                moon_phase_name = None
                lunation_duration = None

                # Calcular parámetros con manejo de errores individual
                try:
                    phase = round(moon_phase(today), 2)
                except Exception as ex:
                    _LOGGER.error("Error al calcular moon_phase: %s", ex)

                try:
                    moon_day_today = moon_day(today)
                except Exception as ex:
                    _LOGGER.error("Error al calcular moon_day: %s", ex)

                try:
                    lunation = lunation_number(today)
                except Exception as ex:
                    _LOGGER.error("Error al calcular lunation_number: %s", ex)

                try:
                    illuminated = round(illuminated_percentage(today), 2)
                except Exception as ex:
                    _LOGGER.error("Error al calcular illuminated_percentage: %s", ex)

                try:
                    distance = round(moon_distance(today), 0)
                except Exception as ex:
                    _LOGGER.error("Error al calcular moon_distance: %s", ex)

                try:
                    angular_diameter = round(moon_angular_diameter(today), 2)
                except Exception as ex:
                    _LOGGER.error("Error al calcular moon_angular_diameter: %s", ex)

                try:
                    moon_phase_name = get_moon_phase_name(today)
                except Exception as ex:
                    _LOGGER.error("Error al calcular moon_phase_name: %s", ex)
                
                try:
                    lunation_duration = get_lunation_duration(today)
                except Exception as ex:
                    _LOGGER.error("Error al calcular lunation_duration: %s", ex)

                # Moonrise y moonset aproximados (UTC)
                try:
                    rise_utc, set_utc = moon_rise_set(self.latitude, self.longitude, today)
                    rise_local = rise_utc.astimezone(TIMEZONE).isoformat() if rise_utc else None
                    set_local = set_utc.astimezone(TIMEZONE).isoformat() if set_utc else None
                except Exception as ex:
                    _LOGGER.error("Error al calcular moon_rise_set: %s", ex)
                    rise_local = None
                    set_local = None

                # Formatear datos para guardar
                moon_data_formatted = {
                    "actualitzat": {"dataUpdate": current_time.isoformat()},
                    "last_lunar_update_date": today.isoformat(),
                    "dades": [
                        {
                            "moon_day": moon_day_today,
                            "moon_phase": phase,
                            "moon_phase_name": moon_phase_name,
                            "illuminated_percentage": illuminated,
                            "moon_distance": distance,
                            "moon_angular_diameter": angular_diameter,
                            "lunation": lunation,
                            "lunation_duration": lunation_duration,
                            "moonrise": rise_local,
                            "moonset": set_local
                        }
                    ]
                }

                # Guardar el archivo
                await moon_file.async_write_json(moon_data_formatted)
                _LOGGER.info("Archivo moon_%s_data.json creado con datos iniciales", town_id)

            except Exception as ex:
                _LOGGER.error("Error general al crear moon_%s_data.json: %s", town_id, ex)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Primer paso: solicitar API Key."""
        errors = {}
        today = dt_util.now().date()

        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]
            self.api_key_reminder = user_input.get(CONF_API_KEY_REMINDER, False)
            issue_date_input = user_input.get(CONF_API_KEY_DATE)
            issue_date = parse_issue_date(issue_date_input)

            if issue_date_input and issue_date is None or issue_date is not None and is_future_date(issue_date, today):
                errors[CONF_API_KEY_DATE] = "invalid_date"
            else:
                if issue_date is None:
                    issue_date = today
                self.api_key_date = issue_date.isoformat()

            if not errors:
                town_client = MeteocatTown(
                    self.api_key, async_get_clientsession(self.hass)
                )
                try:
                    self.municipis = await town_client.get_municipis()

                    # Guardar lista de municipios en towns.json
                    assets_dir = get_storage_dir(self.hass, "assets")
                    towns_file = assets_dir / "towns.json"
                    await towns_file.async_write_json({"towns": self.municipis})
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

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(
                    CONF_API_KEY_DATE, default=today.isoformat()
                ): OptionalDateSelector(),
                vol.Optional(CONF_API_KEY_REMINDER, default=False): bool,
            }
        )
        suggested = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                {
                    CONF_API_KEY_DATE: suggested.get(
                        CONF_API_KEY_DATE, today.isoformat()
                    ),
                    CONF_API_KEY_REMINDER: suggested.get(
                        CONF_API_KEY_REMINDER, False
                    ),
                },
            ),
            errors=errors,
            description_placeholders={"api_key_url": API_KEY_URL},
        )

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
            session = async_get_clientsession(self.hass)
            symbols_data = await MeteocatSymbols(self.api_key, session).fetch_symbols()
            await symbols_file.async_write_json({"symbols": symbols_data})

            variables_data = await MeteocatVariables(
                self.api_key, session
            ).get_variables()
            await variables_file.async_write_json({"variables": variables_data})

            self.variable_id = next(
                (v["codi"] for v in variables_data if v["nom"].lower() == "temperatura"),
                None,
            )
        except Exception as ex:
            _LOGGER.error("Error al descargar símbolos o variables: %s", ex)
            raise HomeAssistantError("No se pudieron obtener símbolos o variables")

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tercer paso: seleccionar estación."""
        errors = {}
        townstations_client = MeteocatTownStations(
            self.api_key, async_get_clientsession(self.hass)
        )

        try:
            # Obtener la lista completa de estaciones de la API
            all_stations = await townstations_client.stations_service.get_stations()
            assets_dir = get_storage_dir(self.hass, "assets")
            stations_file = assets_dir / "stations.json"
            await stations_file.async_write_json({"stations": all_stations})
            _LOGGER.info("Lista completa de estaciones guardadas en %s", stations_file)

            # Obtener estaciones filtradas por municipio y variable
            stations_data = await townstations_client.get_town_stations(
                self.selected_municipi["codi"], self.variable_id
            )

            town_stations_file = assets_dir / f"stations_{self.selected_municipi['codi']}.json"
            await town_stations_file.async_write_json(
                {"town_stations": stations_data}
            )
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
                    station_metadata = await MeteocatInfoStation(
                        self.api_key, async_get_clientsession(self.hass)
                    ).get_infostation(self.station_id)
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
                    CONF_API_KEY_DATE: self.api_key_date
                    or dt_util.now().date().isoformat(),
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
                options={CONF_API_KEY_REMINDER: self.api_key_reminder},
            )

        schema = vol.Schema({
            vol.Required(LIMIT_XEMA, default=750): cv.positive_int,
            vol.Required(LIMIT_PREDICCIO, default=100): cv.positive_int,
            vol.Required(LIMIT_XDDE, default=250): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required(LIMIT_QUOTA, default=300): cv.positive_int,
            vol.Required(LIMIT_BASIC, default=2000): cv.positive_int,
        })
        return self.async_show_form(step_id="set_api_limits", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication of the API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Request and validate a new API key."""
        errors: dict[str, str] = {}
        today = dt_util.now().date()

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            issue_date_input = user_input.get(CONF_API_KEY_DATE)
            issue_date = parse_issue_date(issue_date_input)

            if issue_date_input and issue_date is None or issue_date is not None and is_future_date(issue_date, today):
                errors[CONF_API_KEY_DATE] = "invalid_date"

            if not errors:
                try:
                    await MeteocatTown(
                        api_key, async_get_clientsession(self.hass)
                    ).get_municipis()
                except Exception:  # noqa: BLE001
                    errors["base"] = "connection_error"

            if not errors:
                entry = self._get_reauth_entry()
                old_api_key = entry.options.get(CONF_API_KEY) or entry.data.get(
                    CONF_API_KEY
                )
                if old_api_key and old_api_key != api_key:
                    await async_delete_unused_quotes_file(
                        self.hass,
                        old_api_key,
                        exclude_entry_id=entry.entry_id,
                    )

                existing_issue_date = parse_issue_date(
                    entry.data.get(CONF_API_KEY_DATE)
                )
                if old_api_key == api_key:
                    new_issue_date = issue_date or existing_issue_date
                else:
                    new_issue_date = issue_date or today

                data_updates = {CONF_API_KEY: api_key}
                if new_issue_date is not None:
                    data_updates[CONF_API_KEY_DATE] = new_issue_date.isoformat()

                options_update = {}
                if CONF_API_KEY in entry.options:
                    options_update["options"] = {
                        **entry.options,
                        CONF_API_KEY: api_key,
                    }

                async_cancel_api_key_reminder(self.hass, entry)
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data_updates,
                    **options_update,
                )

        entry = self._get_reauth_entry()
        existing_issue_date = parse_issue_date(entry.data.get(CONF_API_KEY_DATE))
        suggested = user_input or {}
        suggested_date = suggested.get(
            CONF_API_KEY_DATE,
            existing_issue_date.isoformat()
            if existing_issue_date is not None
            else today.isoformat(),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_API_KEY_DATE): OptionalDateSelector(),
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                schema, {CONF_API_KEY_DATE: suggested_date}
            ),
            errors=errors,
            description_placeholders={"api_key_url": API_KEY_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MeteocatOptionsFlowHandler:
        """Devuelve el flujo de opciones para esta configuración."""
        return MeteocatOptionsFlowHandler(config_entry)