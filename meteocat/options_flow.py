from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN
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
        self.config_entry = config_entry
        self.api_key: str | None = None

    async def async_step_init(self, user_input: dict | None = None):
        """Paso inicial del flujo de opciones."""
        return await self.async_step_update_api_key()

    async def async_step_update_api_key(self, user_input: dict | None = None):
        """Permite al usuario actualizar la API Key."""
        errors = {}

        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]

            # Validar la nueva API Key utilizando MeteocatTown
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

            if not errors:
                # Actualizar la configuración de la entrada con la nueva API Key
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_API_KEY: self.api_key},
                )
                return self.async_create_entry(title="", data={})

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(
            step_id="update_api_key", data_schema=schema, errors=errors
        )
