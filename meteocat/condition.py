from __future__ import annotations

from .const import CONDITION_MAPPING  # Importar el mapeo desde const.py

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
