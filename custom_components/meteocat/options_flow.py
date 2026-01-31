from __future__ import annotations

import logging
import asyncio
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_API_KEY,
    LIMIT_XEMA,
    LIMIT_PREDICCIO,
    LIMIT_XDDE,
    LIMIT_QUOTA,
    LIMIT_BASIC,
    LATITUDE,
    LONGITUDE,
    ALTITUDE,
)
from .helpers import get_storage_dir
from meteocatpy.town import MeteocatTown
from meteocatpy.exceptions import (
    BadRequestError,
    ForbiddenError,
    TooManyRequestsError,
    InternalServerError,
    UnknownAPIError,
)

_LOGGER = logging.getLogger(__name__)

class MeteocatOptionsFlowHandler(OptionsFlow):
    """Manejo del flujo de opciones para Meteocat."""

    def __init__(self, config_entry: ConfigEntry):
        """Inicializa el flujo de opciones."""
        self._config_entry = config_entry
        self.api_key: str | None = None
        self.limit_xema: int | None = None
        self.limit_prediccio: int | None = None
        self.limit_xdde: int | None = None
        self.limit_quota: int | None = None
        self.limit_basic: int | None = None
        self.latitude: float | None = None
        self.longitude: float | None = None
        self.altitude: float | None = None

    async def async_step_init(self, user_input: dict | None = None):
        """Paso inicial del flujo de opciones."""
        if user_input is not None:
            if user_input["option"] == "update_api_and_limits":
                return await self.async_step_update_api_and_limits()
            elif user_input["option"] == "update_limits_only":
                return await self.async_step_update_limits_only()
            elif user_input["option"] == "regenerate_assets":
                return await self.async_step_confirm_regenerate_assets()
            elif user_input["option"] == "update_coordinates":
                return await self.async_step_update_coordinates()
            elif user_input["option"] == "force_data_update":
                return await self.async_step_confirm_force_data_update()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("option"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            "update_api_and_limits",
                            "update_limits_only",
                            "regenerate_assets",
                            "update_coordinates",
                            "force_data_update"
                        ],
                        translation_key="option"
                    )
                )
            })
        )

    async def async_step_update_api_and_limits(self, user_input: dict | None = None):
        """Permite al usuario actualizar la API Key y los límites."""
        errors = {}

        if user_input is not None:
            self.api_key = user_input.get(CONF_API_KEY)
            self.limit_xema = user_input.get(LIMIT_XEMA)
            self.limit_prediccio = user_input.get(LIMIT_PREDICCIO)
            self.limit_xdde = user_input.get(LIMIT_XDDE)
            self.limit_quota = user_input.get(LIMIT_QUOTA)
            self.limit_basic = user_input.get(LIMIT_BASIC)

            # Validar la nueva API Key utilizando MeteocatTown
            if self.api_key:
                town_client = MeteocatTown(self.api_key)
                try:
                    await town_client.get_municipis()  # Verificar que la API Key sea válida
                except (
                    BadRequestError,
                    ForbiddenError,
                    TooManyRequestsError,
                    InternalServerError,
                    UnknownAPIError,
                ) as ex:
                    _LOGGER.error("Error al validar la nueva API Key: %s", ex)
                    errors["base"] = "cannot_connect"
                except Exception as ex:
                    _LOGGER.error("Error inesperado al validar la nueva API Key: %s", ex)
                    errors["base"] = "unknown"

            # Validar que los límites sean números positivos
            limits_to_validate = [self.limit_xema, self.limit_prediccio, self.limit_xdde, self.limit_quota, self.limit_basic]
            if not all(cv.positive_int(limit) for limit in limits_to_validate if limit is not None):
                errors["base"] = "invalid_limit"

            if not errors:
                # Actualizar la configuración de la entrada con la nueva API Key y límites
                data_update = {}
                if self.api_key:
                    data_update[CONF_API_KEY] = self.api_key
                if self.limit_xema:
                    data_update[LIMIT_XEMA] = self.limit_xema
                if self.limit_prediccio:
                    data_update[LIMIT_PREDICCIO] = self.limit_prediccio
                if self.limit_xdde:
                    data_update[LIMIT_XDDE] = self.limit_xdde
                if self.limit_quota:
                    data_update[LIMIT_QUOTA] = self.limit_quota
                if self.limit_basic:
                    data_update[LIMIT_BASIC] = self.limit_basic

                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={**self._config_entry.data, **data_update},
                )
                # Recargar la integración para aplicar los cambios dinámicamente
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)

                return self.async_create_entry(title="", data={})

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(LIMIT_XEMA, default=self._config_entry.data.get(LIMIT_XEMA)): cv.positive_int,
            vol.Required(LIMIT_PREDICCIO, default=self._config_entry.data.get(LIMIT_PREDICCIO)): cv.positive_int,
            vol.Required(LIMIT_XDDE, default=self._config_entry.data.get(LIMIT_XDDE)): cv.positive_int,
            vol.Required(LIMIT_QUOTA, default=self._config_entry.data.get(LIMIT_QUOTA)): cv.positive_int,
            vol.Required(LIMIT_BASIC, default=self._config_entry.data.get(LIMIT_BASIC)): cv.positive_int,
        })
        return self.async_show_form(
            step_id="update_api_and_limits", data_schema=schema, errors=errors
        )

    async def async_step_update_limits_only(self, user_input: dict | None = None):
        """Permite al usuario actualizar solo los límites de la API."""
        errors = {}

        if user_input is not None:
            self.limit_xema = user_input.get(LIMIT_XEMA)
            self.limit_prediccio = user_input.get(LIMIT_PREDICCIO)
            self.limit_xdde = user_input.get(LIMIT_XDDE)
            self.limit_quota = user_input.get(LIMIT_QUOTA)
            self.limit_basic = user_input.get(LIMIT_BASIC)

            # Validar que los límites sean números positivos
            limits_to_validate = [self.limit_xema, self.limit_prediccio, self.limit_xdde, self.limit_quota, self.limit_basic]
            if not all(cv.positive_int(limit) for limit in limits_to_validate if limit is not None):
                errors["base"] = "invalid_limit"

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={
                        **self._config_entry.data,
                        LIMIT_XEMA: self.limit_xema,
                        LIMIT_PREDICCIO: self.limit_prediccio,
                        LIMIT_XDDE: self.limit_xdde,
                        LIMIT_QUOTA: self.limit_quota,
                        LIMIT_BASIC: self.limit_basic
                    },
                )
                # Recargar la integración para aplicar los cambios dinámicamente
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)

                return self.async_create_entry(title="", data={})

        schema = vol.Schema({
            vol.Required(LIMIT_XEMA, default=self._config_entry.data.get(LIMIT_XEMA)): cv.positive_int,
            vol.Required(LIMIT_PREDICCIO, default=self._config_entry.data.get(LIMIT_PREDICCIO)): cv.positive_int,
            vol.Required(LIMIT_XDDE, default=self._config_entry.data.get(LIMIT_XDDE)): cv.positive_int,
            vol.Required(LIMIT_QUOTA, default=self._config_entry.data.get(LIMIT_QUOTA)): cv.positive_int,
            vol.Required(LIMIT_BASIC, default=self._config_entry.data.get(LIMIT_BASIC)): cv.positive_int,
        })
        return self.async_show_form(
            step_id="update_limits_only", data_schema=schema, errors=errors
        )

    async def async_step_update_coordinates(self, user_input: dict | None = None):
        """Permite al usuario actualizar las coordenadas (latitude, longitude)."""
        errors = {}

        if user_input is not None:
            self.latitude = user_input.get(LATITUDE)
            self.longitude = user_input.get(LONGITUDE)
            self.altitude = user_input.get(ALTITUDE)

            # Validar que las coordenadas estén dentro del rango de Cataluña
            if not (40.5 <= self.latitude <= 42.5 and 0.1 <= self.longitude <= 3.3):
                _LOGGER.error(
                    "Coordenadas fuera del rango de Cataluña (latitude: %s, longitude: %s).",
                    self.latitude, self.longitude
                )
                errors["base"] = "invalid_coordinates"
            # Validar que la altitud sea positiva
            elif self.altitude < 0:
                _LOGGER.error("Altitud inválida: %s. Debe ser >= 0.", self.altitude)
                errors["base"] = "invalid_altitude"
            else:
                # Actualizar la configuración con las nuevas coordenadas
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={
                        **self._config_entry.data,
                        LATITUDE: self.latitude,
                        LONGITUDE: self.longitude,
                        ALTITUDE: self.altitude
                    },
                )
                # Recargar la integración para aplicar los cambios
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)
                _LOGGER.info(
                    "Coordenadas actualizadas a latitude: %s, longitude: %s, altitude=%s.",
                    self.latitude, self.longitude, self.altitude
                )
                return self.async_create_entry(title="", data={})

        schema = vol.Schema({
            vol.Required(LATITUDE, default=self._config_entry.data.get(LATITUDE)): cv.latitude,
            vol.Required(LONGITUDE, default=self._config_entry.data.get(LONGITUDE)): cv.longitude,
            vol.Required(ALTITUDE, default=self._config_entry.data.get(ALTITUDE)): vol.Coerce(float),
        })
        return self.async_show_form(
            step_id="update_coordinates",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "current_latitude": self._config_entry.data.get(LATITUDE),
                "current_longitude": self._config_entry.data.get(LONGITUDE),
                "current_altitude": self._config_entry.data.get(ALTITUDE, 0.0)
            }
        )

    async def async_step_confirm_regenerate_assets(self, user_input: dict | None = None):
        """Confirma si el usuario realmente quiere regenerar los assets."""
        if user_input is not None:
            if user_input.get("confirm") is True:
                return await self.async_step_regenerate_assets()
            else:
                # Volver al menú inicial si el usuario cancela
                return await self.async_step_init()

        schema = vol.Schema({
            vol.Required("confirm", default=False): bool
        })
        return self.async_show_form(
            step_id="confirm_regenerate_assets",
            data_schema=schema,
            description_placeholders={
                "warning": "Esto regenerará los archivos faltantes de towns.json, stations.json, variables.json, symbols.json y stations_<town_id>.json. ¿Desea continuar?"
            }
        )

    async def async_step_regenerate_assets(self, user_input: dict | None = None):
        """Regenera los archivos de assets."""
        from . import ensure_assets_exist  # importamos la función desde __init__.py

        errors = {}
        try:
            # Llamar a la función que garantiza que los assets existan
            await ensure_assets_exist(self.hass, self._config_entry.data)

            _LOGGER.info("Archivos de assets regenerados correctamente.")
            # Forzar recarga de la integración
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)

            return self.async_create_entry(title="", data={})

        except Exception as ex:
            _LOGGER.error("Error al regenerar assets: %s", ex)
            errors["base"] = "regenerate_failed"

        return self.async_show_form(step_id="regenerate_assets", errors=errors)
    
    async def async_step_confirm_force_data_update(self, user_input: dict | None = None):
        """Confirma si el usuario quiere proceder a forzar actualizaciones de datos."""
        if user_input is not None:
            if user_input.get("confirm") is True:
                return await self.async_step_select_data_to_force()
            else:
                # Volver al menú inicial si cancela
                return await self.async_step_init()

        schema = vol.Schema({
            vol.Required("confirm", default=False): bool
        })
        return self.async_show_form(
            step_id="confirm_force_data_update",
            data_schema=schema,
            description_placeholders={
                "warning": "Esto forzará llamadas a la API de Meteocat para actualizar los datos seleccionados, ignorando las comprobaciones de validez temporal. Puede consumir cuota de API. ¿Desea continuar?"
            }
        )

    async def async_step_select_data_to_force(self, user_input: dict | None = None):
        """Permite seleccionar qué datos forzar la actualización (multi-select)."""
        errors = {}

        if user_input is not None:
            selected = user_input.get("data_types", [])
            if not selected:
                errors["base"] = "no_selection"
            else:
                try:
                    town_id = self._config_entry.data.get("town_id")
                    if not town_id:
                        raise HomeAssistantError("No se encontró town_id en la configuración.")

                    # No borramos archivos: seteamos flags en coordinadores
                    domain_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})

                    # UVI
                    if "force_uvi_update" in selected:
                        uvi_coord = domain_data.get("uvi_coordinator")
                        if uvi_coord:
                            uvi_coord.force_next_update()
                            await uvi_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización UVI via flag para town=%s", town_id)

                            # Pequeño delay para asegurar que el JSON se haya escrito
                            await asyncio.sleep(1)  # 1 segundo; ajusta si es necesario

                            # Refrescar dependiente: uvi_file_coordinator
                            uvi_file_coord = domain_data.get("uvi_file_coordinator")
                            if uvi_file_coord:
                                await uvi_file_coord.async_request_refresh()
                                _LOGGER.debug("Refrescado uvi_file_coordinator dependiente")
                            else:
                                _LOGGER.warning("Coordinador uvi_file no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador UVI no encontrado; no se pudo forzar.")

                    # Predicciones horarias y diarias
                    if "force_hourly_forecast_update" in selected or "force_daily_forecast_update" in selected:
                        entity_coord = domain_data.get("entity_coordinator")
                        if entity_coord:
                            if "force_hourly_forecast_update" in selected:
                                entity_coord.force_next_update()
                            if "force_daily_forecast_update" in selected:
                                entity_coord.force_next_update()
                            await entity_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización de predicciones via flags para town=%s", town_id)

                            # Pequeño delay para asegurar que el JSON se haya escrito
                            await asyncio.sleep(1)  # 1 segundo; ajusta si es necesario

                            # Refrescar dependientes selectivos
                            if "force_hourly_forecast_update" in selected:
                                # Hourly
                                hourly_coord = domain_data.get("hourly_forecast_coordinator")
                                if hourly_coord:
                                    await hourly_coord.async_request_refresh()
                                    _LOGGER.debug("Refrescado hourly_forecast_coordinator dependiente")
                                else:
                                    _LOGGER.warning("Coordinador hourly_forecast no encontrado; se actualizará en su próximo ciclo.")

                                # Condition (basado en hourly)
                                condition_coord = domain_data.get("condition_coordinator")
                                if condition_coord:
                                    await condition_coord.async_request_refresh()
                                    _LOGGER.debug("Refrescado condition_coordinator dependiente")
                                else:
                                    _LOGGER.warning("Coordinador condition no encontrado; se actualizará en su próximo ciclo.")

                            if "force_daily_forecast_update" in selected:
                                # Daily
                                daily_coord = domain_data.get("daily_forecast_coordinator")
                                if daily_coord:
                                    await daily_coord.async_request_refresh()
                                    _LOGGER.debug("Refrescado daily_forecast_coordinator dependiente")
                                else:
                                    _LOGGER.warning("Coordinador daily_forecast no encontrado; se actualizará en su próximo ciclo.")

                                # Temp Forecast (basado en daily)
                                temp_coord = domain_data.get("temp_forecast_coordinator")
                                if temp_coord:
                                    await temp_coord.async_request_refresh()
                                    _LOGGER.debug("Refrescado temp_forecast_coordinator dependiente")
                                else:
                                    _LOGGER.warning("Coordinador temp_forecast no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador de entidades no encontrado; no se pudo forzar.")
                    
                    # Alertas
                    if "force_alerts_update" in selected:
                        alerts_coord = domain_data.get("alerts_coordinator")
                        if alerts_coord:
                            alerts_coord.force_next_update()
                            await alerts_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización de alertas via flag para town=%s", town_id)

                            # Pequeño delay para asegurar que los JSONs se hayan escrito
                            await asyncio.sleep(1)  # 1 segundo; ajusta si es necesario

                            # Refrescar dependiente: alerts_region_coordinator
                            alerts_region_coord = domain_data.get("alerts_region_coordinator")
                            if alerts_region_coord:
                                await alerts_region_coord.async_request_refresh()
                                _LOGGER.debug("Refrescado alerts_region_coordinator dependiente")
                            else:
                                _LOGGER.warning("Coordinador alerts_region no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador de alertas no encontrado; no se pudo forzar.")
                    
                    # Datos de la estación (sensores XEMA)
                    if "force_station_update" in selected:
                        sensor_coord = domain_data.get("sensor_coordinator")
                        if sensor_coord:
                            sensor_coord.force_next_update()
                            await sensor_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización de datos de estación via flag para station=%s", town_id)

                        else:
                            _LOGGER.warning("Coordinador sensor no encontrado; no se pudo forzar.")
                    
                    # Rayos
                    if "force_lightning_update" in selected:
                        lightning_coord = domain_data.get("lightning_coordinator")
                        if lightning_coord:
                            lightning_coord.force_next_update()
                            await lightning_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización de datos de rayos via flag para region=%s", town_id)

                            # Pequeño delay para asegurar que lightning_{region_id}.json se haya escrito
                            await asyncio.sleep(1)

                            # Refrescar el coordinador dependiente
                            lightning_file_coord = domain_data.get("lightning_file_coordinator")
                            if lightning_file_coord:
                                await lightning_file_coord.async_request_refresh()
                                _LOGGER.debug("Refrescado lightning_file_coordinator dependiente")
                            else:
                                _LOGGER.warning("Coordinador lightning_file no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador lightning no encontrado; no se pudo forzar.")
                    
                    # Cuotas
                    if "force_quotes_update" in selected:
                        quotes_coord = domain_data.get("quotes_coordinator")
                        if quotes_coord:
                            quotes_coord.force_next_update()
                            await quotes_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización de datos de cuotas")

                            # Pequeño delay para asegurar que quotes.json se haya escrito
                            await asyncio.sleep(1)

                            # Refrescar el coordinador dependiente: quotes_file_coordinator
                            quotes_file_coord = domain_data.get("quotes_file_coordinator")
                            if quotes_file_coord:
                                await quotes_file_coord.async_request_refresh()
                                _LOGGER.debug("Refrescado quotes_file_coordinator dependiente")
                            else:
                                _LOGGER.warning("Coordinador quotes_file no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador quotes no encontrado; no se pudo forzar.")
                    
                    # Sol
                    if "force_sun_update" in selected:
                        sun_coord = domain_data.get("sun_coordinator")
                        if sun_coord:
                            sun_coord.force_next_update()
                            await sun_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización datos de sol via flag para town=%s", town_id)

                            # Pequeño delay para asegurar que el JSON se haya escrito
                            await asyncio.sleep(1)  # 1 segundo; ajusta si es necesario

                            # Refrescar dependiente: sun_file_coordinator
                            sun_file_coord = domain_data.get("sun_file_coordinator")
                            if sun_file_coord:
                                await sun_file_coord.async_request_refresh()
                                _LOGGER.debug("Refrescado sun_file_coordinator dependiente")
                            else:
                                _LOGGER.warning("Coordinador sun_file no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador sun no encontrado; no se pudo forzar.")
                    
                    # Luna
                    if "force_moon_update" in selected:
                        moon_coord = domain_data.get("moon_coordinator")
                        if moon_coord:
                            moon_coord.force_next_update()
                            await moon_coord.async_request_refresh()
                            _LOGGER.info("Forzando actualización datos de la luna via flag para town=%s", town_id)

                            # Pequeño delay para asegurar que el JSON se haya escrito
                            await asyncio.sleep(1)  # 1 segundo; ajusta si es necesario

                            # Refrescar dependiente: moon_file_coordinator
                            moon_file_coord = domain_data.get("moon_file_coordinator")
                            if moon_file_coord:
                                await moon_file_coord.async_request_refresh()
                                _LOGGER.debug("Refrescado moon_file_coordinator dependiente")
                            else:
                                _LOGGER.warning("Coordinador moon_file no encontrado; se actualizará en su próximo ciclo.")
                        else:
                            _LOGGER.warning("Coordinador moon no encontrado; no se pudo forzar.")

                    return self.async_create_entry(title="", data={})

                except Exception as ex:
                    _LOGGER.error("Error al forzar actualización de datos: %s", ex)
                    errors["base"] = "force_update_failed"

        schema = vol.Schema({
            vol.Optional("data_types"): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        "force_uvi_update",
                        "force_hourly_forecast_update",
                        "force_daily_forecast_update",
                        "force_alerts_update",
                        "force_station_update",
                        "force_lightning_update",
                        "force_quotes_update",
                        "force_sun_update",
                        "force_moon_update"
                    ],
                    multiple=True,
                    translation_key="data_types"
                )
            )
        })

        return self.async_show_form(
            step_id="select_data_to_force",
            data_schema=schema,
            errors=errors
        )