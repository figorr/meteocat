from __future__ import annotations

from datetime import datetime
from .const import CONDITION_MAPPING
from .helpers import is_night  # Importar la función is_night de helpers.py

def get_condition_from_statcel(codi_estatcel, current_time: datetime, hass) -> dict:
    """
    Convierte el código 'estatCel' en condición de Home Assistant.

    :param codi_estatcel: Código del estado del cielo (celestial state code).
    :param current_time: Fecha y hora actual (datetime).
    :param hass: Instancia de Home Assistant.
    :return: Diccionario con la condición y el icono.
    """
    # Determinar si es de noche usando la lógica centralizada en helpers.py
    is_night_flag = is_night(current_time, hass)

    # Identificar la condición basada en el código
    for condition, codes in CONDITION_MAPPING.items():
        if codi_estatcel in codes:
            # Ajustar para condiciones nocturnas si aplica
            if condition == "sunny" and is_night_flag:
                return {"condition": "clear-night", "icon": None}
            return {"condition": condition, "icon": None}

    # Si no coincide ningún código, devolver condición desconocida
    return {"condition": "unknown", "icon": None}
