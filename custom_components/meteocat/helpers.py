from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from solarmoonpy.location import Location

from .cache import CacheFile, get_storage_dir
from .const import CONF_API_KEY, DOMAIN

__all__ = [
    "async_delete_unused_quotes_file",
    "async_migrate_legacy_quotes",
    "get_quotes_file",
    "get_quotes_id",
    "get_quotes_lock",
    "get_storage_dir",
    "get_sun_times",
    "is_night",
]

_LOGGER = logging.getLogger(__name__)

_QUOTES_LOCKS_KEY = f"{DOMAIN}_quotes_locks"
_LEGACY_QUOTES_FILE = "quotes.json"


def get_quotes_id(api_key: str) -> str:
    """Return a stable, non-reversible identifier for an API key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:32]


def get_quotes_file(hass: HomeAssistant, api_key: str) -> CacheFile:
    """Return the quotes cache file shared by an API key."""
    return get_storage_dir(hass, "files") / f"quotes_{get_quotes_id(api_key)}.json"


def get_quotes_lock(hass: HomeAssistant, api_key: str) -> asyncio.Lock:
    """Return the lock used to serialize writes for an API key."""
    locks: dict[str, asyncio.Lock] = hass.data.setdefault(_QUOTES_LOCKS_KEY, {})
    return locks.setdefault(get_quotes_id(api_key), asyncio.Lock())


def _entry_api_key(entry: ConfigEntry) -> str | None:
    """Return the effective API key for a config entry."""
    return entry.options.get(CONF_API_KEY) or entry.data.get(CONF_API_KEY)


async def async_migrate_legacy_quotes(hass: HomeAssistant, api_key: str) -> None:
    """Move the old global quotes file to the per-API-key cache file."""
    files = get_storage_dir(hass, "files")
    legacy_file = files / _LEGACY_QUOTES_FILE
    if not await legacy_file.async_exists():
        return

    target_file = get_quotes_file(hass, api_key)
    if not await target_file.async_exists():
        try:
            data = await legacy_file.async_read_json()
        except Exception:
            _LOGGER.exception("Could not read legacy quotes cache")
            return

        if not isinstance(data, dict):
            _LOGGER.warning("Ignoring invalid legacy quotes cache")
            return

        data.pop("client", None)
        await target_file.async_write_json(data)

    await legacy_file.async_delete()


async def async_delete_unused_quotes_file(
    hass: HomeAssistant,
    api_key: str | None,
    *,
    exclude_entry_id: str | None = None,
) -> None:
    """Delete an API key quotes file when no other entry uses it."""
    if not api_key:
        return

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude_entry_id:
            continue
        if _entry_api_key(entry) == api_key:
            return

    await get_quotes_file(hass, api_key).async_delete()


# Cálculo de amanecer y atardecer para definir cuando es de noche
def get_sun_times(
    location: Location, current_time: datetime | None = None
) -> tuple[datetime, datetime]:
    """Obtiene las horas de amanecer y atardecer para una ubicación usando solarmoonpy."""
    now = dt_util.as_local(current_time or dt_util.now())
    today = now.date()
    sunrise = location.sunrise(date=today, local=True)
    sunset = location.sunset(date=today, local=True)

    if not sunrise or not sunset:
        raise ValueError("No se pudieron calcular amanecer o atardecer.")

    _LOGGER.debug(
        "[solarmoonpy] Amanecer: %s, Atardecer: %s, Hora actual: %s",
        sunrise,
        sunset,
        now,
    )
    return sunrise, sunset


def is_night(current_time, location: Location) -> bool:
    """Determina si actualmente es de noche usando una instancia de Location."""
    # Asegurarse de que current_time sea aware y en zona local
    if current_time.tzinfo is None:
        _LOGGER.warning("current_time has no timezone; assuming UTC")
        current_time = dt_util.as_local(dt_util.utc_to_local(current_time))
    else:
        current_time = dt_util.as_local(current_time)

    try:
        sunrise, sunset = get_sun_times(location, current_time)
    except Exception as e:  # noqa: BLE001
        _LOGGER.warning("Error calculating sunrise/sunset with solarmoonpy: %s", e)
        return False  # fallback seguro

    is_night_now = current_time < sunrise or current_time > sunset
    _LOGGER.debug(
        "[solarmoonpy] Current time: %s | Sunrise: %s | Sunset: %s -> Night: %s",
        current_time,
        sunrise,
        sunset,
        is_night_now,
    )
    return is_night_now
