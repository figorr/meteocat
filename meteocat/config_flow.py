import logging
import requests
import os
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)
DOMAIN = "meteocat"
BASE_URL = "https://api.meteo.cat"


class MeteocatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Manejo del flujo de configuración para Meteocat."""

    VERSION = 1

    def __init__(self):
        self.api_key = None
        self.municipis_list = []
        self.selected_municipi = None
        self.path_municipis = "/referencia/v1/municipis"

    async def async_step_user(self, user_input=None):
        """Primer paso: Ingreso y validación de la API Key."""
        errors = {}

        if user_input is not None:
            if "cancel" in user_input:
                return self.async_abort(reason="user_cancelled")
            
            self.api_key = user_input[CONF_API_KEY]
            status_code, municipios_data = await self._validate_and_download_municipis(self.api_key)

            if status_code == 200:
                self.municipis_list = municipios_data
                await self._save_municipis(municipios_data)
                return await self.async_step_select_municipi()
            else:
                errors["base"] = self._map_error_code_to_user_message(status_code)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str
            }),
            description_placeholders={"step_description": "Ingresa tu API Key para validarla."},
            errors=errors,
        )

    async def async_step_select_municipi(self, user_input=None):
        """Segundo paso: Selección de un municipio."""
        errors = {}

        if user_input is not None:
            if "cancel" in user_input:
                return self.async_abort(reason="user_cancelled")

            selected_municipi = user_input.get("municipi")
            matching_municipis = [
                m for m in self.municipis_list if m["nom"].lower() == selected_municipi.lower()
            ]

            if matching_municipis:
                self.selected_municipi = matching_municipis[0]
                return await self.async_step_final()
            else:
                errors["municipi"] = "invalid_municipi"

        municipis_names = [m["nom"] for m in self.municipis_list]
        return self.async_show_form(
            step_id="select_municipi",
            data_schema=vol.Schema({
                vol.Required("municipi"): vol.In(municipis_names)
            }),
            description_placeholders={"step_description": "Selecciona un municipio de la lista."},
            errors=errors,
        )

    async def async_step_final(self, user_input=None):
        """Paso final: Confirmación de la integración."""
        if user_input is not None:
            if "cancel" in user_input:
                return self.async_abort(reason="user_cancelled")

            if "accept" in user_input:
                return self.async_create_entry(
                    title="Meteocat",
                    data={
                        CONF_API_KEY: self.api_key,
                        "municipi": self.selected_municipi["nom"],
                        "codi": self.selected_municipi["codi"],
                    }
                )

        return self.async_show_form(
            step_id="final",
            data_schema=vol.Schema({}),
            description_placeholders={
                "message": (
                    f"Integración configurada correctamente. "
                    f"El municipio elegido es {self.selected_municipi['nom']} "
                    f"con código {self.selected_municipi['codi']}."
                )
            },
            errors={},
        )

    async def _validate_and_download_municipis(self, api_key):
        """Valida la API Key y descarga la lista de municipios."""
        url = f"{BASE_URL}{self.path_municipis}"
        headers = {"X-Api-Key": api_key}

        try:
            response = await self.hass.async_add_executor_job(requests.get, url, headers=headers)
            status_code = response.status_code

            if status_code == 200:
                return status_code, response.json()

            error_details = self._process_api_error(response)
            _LOGGER.warning(f"Error {status_code}: {error_details}")
            return status_code, error_details

        except requests.exceptions.RequestException as e:
            _LOGGER.critical(f"Error en la conexión: {e}")
            return -1, "Error de conexión"

    async def _save_municipis(self, municipios_data):
        """Guarda los datos de municipios en un archivo JSON."""
        if not municipios_data:
            _LOGGER.error("No se obtuvieron datos de los municipios para guardar.")
            return

        carpeta_files = self.hass.config.path("custom_components", DOMAIN, "files")
        os.makedirs(carpeta_files, exist_ok=True)

        archivo_salida = os.path.join(carpeta_files, "municipis_list.json")
        try:
            with open(archivo_salida, "w", encoding="utf-8") as file:
                json.dump(municipios_data, file, ensure_ascii=False, indent=4)
            _LOGGER.info(f"Municipios guardados en {archivo_salida}")
        except OSError as e:
            _LOGGER.error(f"No se pudo guardar el archivo JSON: {e}")

    def _map_error_code_to_user_message(self, status_code):
        """Mapea códigos de error HTTP a mensajes amigables para el usuario."""
        return {
            400: "bad_request",
            403: "forbidden",
            429: "rate_limit_exceeded",
            500: "server_error",
            -1: "connection_error",
        }.get(status_code, "unknown_error")
