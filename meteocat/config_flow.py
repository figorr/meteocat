from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, config_validation as cv

from .const import DEFAULT_NAME, DOMAIN
from .client import MeteocatClient

_LOGGER = logging.getLogger(__name__)

class MeteocatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Flujo de configuración para Meteocat."""

    VERSION = 1

    def __init__(self):
        self.api_key: str | None = None
        self.municipis: list[dict[str, Any]] = []
        self.selected_municipi: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Primer paso: Solicitar la API Key."""
        errors = {}

        if user_input is not None:
            self.api_key = user_input[CONF_API_KEY]

            client = MeteocatClient(
                aiohttp_client.async_get_clientsession(self.hass), self.api_key
            )

            try:
                # Valida la API Key obteniendo la lista de municipios
                self.municipis = await client.get_municipis()
            except ClientError:
                _LOGGER.error("Error al conectar con la API de Meteocat")
                errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Error inesperado: %s", ex)
                errors["base"] = "unknown"

            if not errors:
                # Si no hay errores, pasa al siguiente paso
                return await self.async_step_select_municipi()

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_municipi(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Segundo paso: Seleccionar el municipio."""
        errors = {}

        if user_input is not None:
            # Encuentra el municipio seleccionado en la lista
            selected_codi = user_input["municipi"]
            self.selected_municipi = next(
                (m for m in self.municipis if m["codi"] == selected_codi), None
            )

            if self.selected_municipi:
                # Crea la entrada con la API Key y el municipio seleccionado
                return self.async_create_entry(
                    title=self.selected_municipi["nom"],
                    data={
                        CONF_API_KEY: self.api_key,
                        "municipi": self.selected_municipi["nom"],
                        "codi": self.selected_municipi["codi"],
                    },
                )
            else:
                errors["base"] = "municipi_not_found"

        # Crear un esquema dinámico con los municipios disponibles
        schema = vol.Schema(
            {
                vol.Required("municipi"): vol.In(
                    {m["codi"]: m["nom"] for m in self.municipis}
                )
            }
        )

        return self.async_show_form(
            step_id="select_municipi", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ConfigFlowResult:
        """Devuelve el flujo de opciones para esta configuración."""
        return MeteocatOptionsFlowHandler(config_entry)


class MeteocatOptionsFlowHandler(ConfigFlow):
    """Flujo de opciones para Meteocat."""

    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Gestiona las opciones de configuración."""
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manejo de las opciones del usuario."""
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({}), errors={}
        )
