import os
import logging
from homeassistant import core
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import aiohttp

_LOGGER = logging.getLogger(__name__)

# Constantes
DOMAIN = "meteocat"
BASE_URL = "https://api.meteo.cat"


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Meteocat component."""
    # @TODO: Add setup code.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura una entrada de configuración de Meteocat."""
    # Obtener todas las entradas para el dominio meteocat
    entries = hass.config_entries.async_entries(DOMAIN)
    found = False

    for entry in entries:
        # Verifica si la entrada corresponde al municipio específico
        if entry.data.get("municipi") == entry.data.get("municipi"):  # Ajustar la lógica según sea necesario
            api_key = entry.data.get("api_key")
            municipi = entry.data.get("municipi")
            codi = entry.data.get("codi")
            
            if not api_key:
                _LOGGER.error("No se encontró una API Key guardada. Configura la integración desde el flujo de configuración.")
                return False
            
            # Validar la API Key
            is_valid, error_message = await _validate_api_key(api_key)
            if not is_valid:
                _LOGGER.error(f"API Key no válida: {error_message}. Reconfigura la integración.")
                raise ConfigEntryNotReady("API Key no válida. Por favor, reconfigura la integración.")
            
            _LOGGER.info(f"Integración configurada correctamente. Municipio: {municipi}, Código: {codi}")
            found = True
            break

    if not found:
        _LOGGER.error("No se encontró ninguna entrada de configuración para el municipio solicitado.")
        return False
    
    return True


async def _validate_api_key(api_key: str) -> tuple[bool, str]:
    """Valida la API Key haciendo una solicitud a la API de Meteocat."""
    path_municipis = "/referencia/v1/municipis"
    url = f"{BASE_URL}{path_municipis}"
    headers = {"X-Api-Key": api_key}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True, ""
                return False, f"Código de error {response.status}: {await response.text()}"
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error en la validación de la API Key: {e}")
            return False, "Error de conexión con la API"


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Elimina una entrada de configuración de Meteocat."""
    _LOGGER.info("Eliminando la integración de Meteocat.")
    # Limpia cualquier recurso o tarea creada durante async_setup_entry
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Limpia cualquier dato adicional al desinstalar la integración."""
    _LOGGER.info(f"Eliminando datos residuales de la integración: {entry.entry_id}")

    carpeta_files = hass.config.path("custom_components", DOMAIN, "files")
    archivo_municipis = os.path.join(carpeta_files, "municipis_list.json")

    try:
        if os.path.exists(archivo_municipis):
            os.remove(archivo_municipis)
            _LOGGER.info("Archivo municipios_list.json eliminado correctamente.")
    except OSError as e:
        _LOGGER.error(f"Error al intentar eliminar el archivo municipios_list.json: {e}")
