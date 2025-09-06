from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
import voluptuous as vol

from .const import (
    CONF_API_KEY,
    LIMIT_XEMA,
    LIMIT_PREDICCIO,
    LIMIT_XDDE,
    LIMIT_QUOTA,
    LIMIT_BASIC
)
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

    async def async_step_init(self, user_input: dict | None = None):
        """Paso inicial del flujo de opciones."""
        if user_input is not None:
            if user_input["option"] == "update_api_and_limits":
                return await self.async_step_update_api_and_limits()
            elif user_input["option"] == "update_limits_only":
                return await self.async_step_update_limits_only()
            elif user_input["option"] == "regenerate_assets":
                return await self.async_step_confirm_regenerate_assets()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("option"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            "update_api_and_limits",
                            "update_limits_only",
                            "regenerate_assets"
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