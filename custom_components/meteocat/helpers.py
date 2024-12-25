from __future__ import annotations

import logging
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import as_local, as_utc
from homeassistant.helpers.sun import get_astral_event_next

_LOGGER = logging.getLogger(__name__)

def get_sun_times(hass: HomeAssistant, current_time: datetime | None = None):
    """Get the sunrise and sunset times."""
    # Usa la hora actual si no se proporciona una hora específica
    if current_time is None:
        current_time = datetime.now()

    # Asegúrate de que current_time es aware (UTC con offset)
    current_time = as_utc(current_time)

    # Obtén los tiempos de amanecer y atardecer desde el helper
    sunrise = get_astral_event_next(hass, "sunrise", utc_point_in_time=current_time)
    sunset = get_astral_event_next(hass, "sunset", utc_point_in_time=current_time)

    # Asegúrate de que no sean None y conviértelos a la zona horaria local
    if sunrise and sunset:
        return as_local(sunrise), as_local(sunset)

    # Lanza un error si no se pudieron determinar los eventos
    raise ValueError("Sunrise or sunset data is unavailable.")

def is_night(current_time: datetime, hass: HomeAssistant) -> bool:
    """Determine if it is currently night based on sunrise and sunset times."""
    # Convierte current_time a UTC si no tiene información de zona horaria
    if current_time.tzinfo is None:
        current_time = as_utc(current_time)

    # Obtén los tiempos de amanecer y atardecer
    sunrise, sunset = get_sun_times(hass, current_time)

    # Compara las horas
    return current_time < sunrise or current_time > sunset
