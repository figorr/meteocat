from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from solarmoonpy.location import Location

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
def get_sun_times(location: Location, current_time: datetime | None = None) -> tuple[datetime, datetime]:
    """Obtiene las horas de amanecer y atardecer para una ubicación usando solarmoonpy."""
    now = dt_util.as_local(current_time or dt_util.now())
    today = now.date()
    sunrise = location.sunrise(date=today, local=True)
    sunset = location.sunset(date=today, local=True)

    if not sunrise or not sunset:
        raise ValueError("No se pudieron calcular amanecer o atardecer.")

    _LOGGER.debug(
        "[solarmoonpy] Amanecer: %s, Atardecer: %s, Hora actual: %s",
        sunrise, sunset, now
    )
    return sunrise, sunset

def is_night(current_time, location: Location) -> bool:
    """Determina si actualmente es de noche usando una instancia de Location."""
    # Asegurarse de que current_time sea aware y en zona local
    if current_time.tzinfo is None:
        _LOGGER.warning("current_time sin zona horaria, asumiendo UTC")
        current_time = dt_util.as_local(dt_util.utc_to_local(current_time))
    else:
        current_time = dt_util.as_local(current_time)

    try:
        sunrise, sunset = get_sun_times(location, current_time)
    except Exception as e:
        _LOGGER.warning("Fallo al calcular amanecer/atardecer con solarmoonpy: %s", e)
        return False  # fallback seguro

    is_night_now = current_time < sunrise or current_time > sunset
    _LOGGER.debug(
        "[solarmoonpy] Hora actual: %s | Amanecer: %s | Atardecer: %s → Noche: %s",
        current_time, sunrise, sunset, is_night_now
    )
    return is_night_now
