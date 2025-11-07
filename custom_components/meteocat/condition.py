from __future__ import annotations

from datetime import datetime
from typing import Any
from .const import CONDITION_MAPPING
from .helpers import is_night
import logging

_LOGGER = logging.getLogger(__name__)

def get_condition_from_statcel(
    codi_estatcel: Any,
    current_time: datetime,
    location,
    is_hourly: bool = True
) -> dict:
    """
    Convierte el código 'estatCel' en condición de Home Assistant.

    :param codi_estatcel: Código o lista de códigos del estado del cielo.
    :param current_time: Fecha y hora actual (datetime).
    :param hass: Instancia de Home Assistant.
    :param is_hourly: Indica si los datos son de predicción horaria (True) o diaria (False).
    :return: Diccionario con la condición y el icono.
    """
    
    _LOGGER.debug(
        "Entrando en get_condition_from_statcel con codi_estatcel: %s, is_hourly: %s",
        codi_estatcel,
        is_hourly,
    )

    # Asegurarse de que codi_estatcel sea una lista válida
    if codi_estatcel is None:
        codi_estatcel = []
    elif isinstance(codi_estatcel, int):  # Convertir enteros en lista
        codi_estatcel = [codi_estatcel]

    # Determinar si es de noche
    is_night_flag = is_night(current_time, location)

    # Identificar la condición basada en el código
    for condition, codes in CONDITION_MAPPING.items():
        if any(code in codes for code in codi_estatcel):
            # Ajustar para condiciones nocturnas si aplica
            if condition == "sunny" and is_night_flag:
                _LOGGER.debug(
                    "Códigos EstatCel: %s, Es Noche: %s, Condición Devuelta: clear-night",
                    codi_estatcel,
                    is_night_flag,
                )
                return {"condition": "clear-night", "icon": None}
            
            _LOGGER.debug(
                "Códigos EstatCel: %s, Es Noche: %s, Condición Devuelta: %s",
                codi_estatcel,
                is_night_flag,
                condition,
            )
            return {"condition": condition, "icon": None}

    # Si no coincide ningún código, devolver condición desconocida
    return {"condition": "unknown", "icon": None}
