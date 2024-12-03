import json
from pathlib import Path
import logging
from .const import CONDITION_MAPPING  # Importar el mapeo desde const.py

_LOGGER = logging.getLogger(__name__)

# Ruta al archivo symbols.json dentro del directorio de la integración
SYMBOLS_FILE = Path(__file__).parent / "assets" / "symbols.json"

# Carga los símbolos desde el archivo JSON
def load_symbols():
    try:
        with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("symbols", [])
    except FileNotFoundError:
        _LOGGER.error("El archivo symbols.json no se encontró en %s", SYMBOLS_FILE)
    except json.JSONDecodeError as ex:
        _LOGGER.error("Error al decodificar symbols.json: %s", ex)
    return []

SYMBOLS = load_symbols()

def get_condition_from_statcel(codi_estatcel, is_night=False):
    """
    Convierte el código 'estatCel' en condición de Home Assistant.
    """
    # Identificar la condición basada en el código
    for condition, codes in CONDITION_MAPPING.items():
        if codi_estatcel in codes:
            # Ajustar para condiciones nocturnas si aplica
            if condition == "sunny" and is_night:
                return {"condition": "clear-night", "icon": None}
            return {"condition": condition, "icon": None}

    # Si no coincide ningún código, devolver condición desconocida
    return {"condition": "unknown", "icon": None}
