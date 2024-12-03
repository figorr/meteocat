from __future__ import annotations

from datetime import datetime, time
from homeassistant.helpers import entity_registry

def get_sun_times(hass) -> tuple:
    """
    Obtiene las horas de amanecer y atardecer desde la integración sun.

    :param hass: Instancia de Home Assistant.
    :return: Tupla con las horas de amanecer y atardecer (datetime).
    """
    sun_entity = hass.states.get("sun.sun")
    if sun_entity:
        sunrise = sun_entity.attributes.get("next_rising")
        sunset = sun_entity.attributes.get("next_setting")
        if sunrise and sunset:
            return (
                hass.util.dt.as_local(hass.util.dt.parse_datetime(sunrise)),
                hass.util.dt.as_local(hass.util.dt.parse_datetime(sunset)),
            )
    raise ValueError("No se pudo obtener las horas de amanecer y atardecer de sun.sun")


def is_night(current_time: datetime, hass) -> bool:
    """
    Determina si la hora actual está fuera del rango entre el amanecer y el atardecer.

    :param current_time: Hora actual como objeto datetime.
    :param hass: Instancia de Home Assistant.
    :return: True si es de noche, False si es de día.
    """
    # Obtener las horas de amanecer y atardecer de la integración sun
    sunrise, sunset = get_sun_times(hass)

    # Convertimos a objetos time para comparar solo las horas
    current_time_only = current_time.time()
    sunrise_time_only = sunrise.time()
    sunset_time_only = sunset.time()

    # Devuelve True si la hora está fuera del rango del día
    return current_time_only < sunrise_time_only or current_time_only > sunset_time_only
