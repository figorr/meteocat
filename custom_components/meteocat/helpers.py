from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import as_local, as_utc, start_of_local_day
from homeassistant.helpers.sun import get_astral_event_date

_LOGGER = logging.getLogger(__name__)

# Ruta base para guardar archivos persistentes que se descargan de la API y que son utilizados por los coordinadores
def get_storage_dir(hass: HomeAssistant, subdir: str | None = None) -> Path:
    """Devuelve una ruta persistente en config/meteocat_files[/subdir]."""
    base_dir = Path(hass.config.path("meteocat_files"))
    if subdir:
        base_dir = base_dir / subdir
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

# Cálculo de amanecer y atardecer para definir cuando es de noche
def get_sun_times(hass, current_time=None):
    """Obtén las horas de amanecer y atardecer para el día actual."""
    if current_time is None:
        current_time = datetime.now()

    # Asegúrate de que current_time es aware (UTC)
    current_time = as_utc(current_time)
    today = start_of_local_day(as_local(current_time))

    # Obtén los eventos de amanecer y atardecer del día actual
    sunrise = get_astral_event_date(hass, "sunrise", today)
    sunset = get_astral_event_date(hass, "sunset", today)

    _LOGGER.debug(
        "Sunrise: %s, Sunset: %s, Current Time: %s",
        sunrise,
        sunset,
        as_local(current_time),
    )

    if sunrise and sunset:
        return sunrise, sunset

    raise ValueError("No se pudieron determinar los datos de amanecer y atardecer.")

def is_night(current_time, hass):
    """Determina si actualmente es de noche."""
    # Asegúrate de que current_time es aware (UTC)
    if current_time.tzinfo is None:
        current_time = as_utc(current_time)

    sunrise, sunset = get_sun_times(hass, current_time)

    _LOGGER.debug(
        "Hora actual: %s, Amanecer: %s, Atardecer: %s",
        as_local(current_time),
        as_local(sunrise),
        as_local(sunset),
    )

    # Es de noche si es antes del amanecer o después del atardecer
    return current_time < sunrise or current_time > sunset
