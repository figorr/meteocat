"""Persistent JSON cache backed by Home Assistant's Store helper."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import STORAGE_DIR, Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_CACHE_DATA_KEY = f"{DOMAIN}_cache"
_STORAGE_ROOT = DOMAIN
_INDEX_KEY = f"{_STORAGE_ROOT}/index"
_OLD_INDEX_KEY = f"{DOMAIN}.cache_index"
_OLD_STORE_KEY = f"{DOMAIN}.cache"
_STORE_VERSION = 1
_LEGACY_CACHE_DIR = "meteocat_files"


class MeteocatCache:
    """Domain-wide JSON cache stored in .storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._index_store: Store[list[str]] = Store(
            hass,
            _STORE_VERSION,
            _INDEX_KEY,
        )
        self._stores: dict[str, Store[Any]] = {}
        self._values: dict[str, Any] = {}
        self._index: set[str] | None = None
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Load the cache index, migrating legacy files on first use."""
        if self._index is not None:
            return

        async with self._lock:
            if self._index is not None:
                return

            index = await self._index_store.async_load()
            if index is None:
                index = await self._async_migrate_store_cache()
            if index is None:
                index = await self._async_migrate_legacy()

            self._index = set(index or [])

    async def _async_migrate_store_cache(self) -> list[str] | None:
        """Move the previous hashed Store cache into the shared folder."""
        old_index_store: Store[list[str]] = Store(
            self.hass,
            _STORE_VERSION,
            _OLD_INDEX_KEY,
        )
        old_index = await old_index_store.async_load()
        if old_index is None:
            return None

        keys: list[str] = []
        for key in old_index:
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
            old_store: Store[Any] = Store(
                self.hass,
                _STORE_VERSION,
                f"{_OLD_STORE_KEY}.{digest}",
            )
            value = await old_store.async_load()
            if value is not None:
                await self._store_for(key).async_save(value)
                keys.append(key)
            await old_store.async_remove()

        keys = sorted(keys)
        await self._index_store.async_save(keys)
        await old_index_store.async_remove()
        _LOGGER.info(
            "Migrated %d cache files from .storage/%s* to .storage/%s",
            len(keys),
            _OLD_STORE_KEY,
            _STORAGE_ROOT,
        )
        return keys

    async def _async_migrate_legacy(self) -> list[str]:
        """Move config/meteocat_files JSON files into individual Stores."""
        legacy_dir = Path(self.hass.config.path(_LEGACY_CACHE_DIR))
        if not await self.hass.async_add_executor_job(legacy_dir.is_dir):
            return []

        data = await self.hass.async_add_executor_job(
            self._read_legacy_files, legacy_dir
        )
        if not data:
            return []

        for key, value in data.items():
            await self._store_for(key).async_save(value)

        keys = sorted(data)
        await self._index_store.async_save(keys)
        await self.hass.async_add_executor_job(
            self._cleanup_legacy_files, legacy_dir, keys
        )
        _LOGGER.info(
            "Migrated %d cache files from %s to .storage/%s",
            len(keys),
            _LEGACY_CACHE_DIR,
            _STORAGE_ROOT,
        )
        return keys

    @staticmethod
    def _read_legacy_files(legacy_dir: Path) -> dict[str, Any]:
        """Read legacy JSON files using relative paths as keys."""
        data: dict[str, Any] = {}
        for path in legacy_dir.rglob("*.json"):
            key = path.relative_to(legacy_dir).as_posix()
            try:
                data[key] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as err:
                _LOGGER.warning("Could not migrate %s: %s", path, err)
        return data

    @staticmethod
    def _cleanup_legacy_files(legacy_dir: Path, keys: list[str]) -> None:
        """Remove migrated JSON files and empty directories only."""
        for key in keys:
            try:
                (legacy_dir / key).unlink()
            except FileNotFoundError:
                pass
            except OSError as err:
                _LOGGER.warning("Could not remove migrated file %s: %s", key, err)

        directories = sorted(
            (path for path in legacy_dir.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        )
        directories.append(legacy_dir)
        for directory in directories:
            try:
                directory.rmdir()
            except OSError:
                pass

    def _store_for(self, key: str) -> Store[Any]:
        """Return the Store dedicated to a cache key."""
        store = self._stores.get(key)
        if store is None:
            if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
                raise ValueError(f"Invalid cache key: {key}")
            store = Store[Any](
                self.hass,
                _STORE_VERSION,
                f"{_STORAGE_ROOT}/{key}",
            )
            self._stores[key] = store
        return store

    async def async_get(self, key: str) -> Any:
        """Return a copy of a cached value or None if it does not exist."""
        await self.async_load()
        assert self._index is not None

        if key not in self._index:
            return None

        if key not in self._values:
            value = await self._store_for(key).async_load()
            if value is None:
                self._index.discard(key)
                await self._index_store.async_save(sorted(self._index))
                return None
            if key not in self._index:
                return None
            self._values[key] = value

        return copy.deepcopy(self._values[key])

    async def async_exists(self, key: str) -> bool:
        """Return whether a cache key exists."""
        await self.async_load()
        assert self._index is not None
        return key in self._index

    async def async_set(self, key: str, value: Any) -> None:
        """Store a value and persist the cache."""
        await self.async_load()
        assert self._index is not None

        value = copy.deepcopy(value)
        async with self._lock:
            self._values[key] = value
            is_new = key not in self._index
            self._index.add(key)

        await self._store_for(key).async_save(value)

        if is_new:
            async with self._lock:
                assert self._index is not None
                await self._index_store.async_save(sorted(self._index))

    async def async_delete(self, key: str) -> None:
        """Delete a key if present and persist the cache."""
        await self.async_load()
        assert self._index is not None

        async with self._lock:
            existed = key in self._index
            self._index.discard(key)
            self._values.pop(key, None)

        if not existed:
            return

        await self._store_for(key).async_remove()
        self._stores.pop(key, None)
        async with self._lock:
            assert self._index is not None
            await self._index_store.async_save(sorted(self._index))

    async def async_delete_prefix(self, prefix: str) -> None:
        """Delete every key starting with prefix."""
        await self.async_load()
        assert self._index is not None
        for key in [key for key in self._index if key.startswith(prefix)]:
            await self.async_delete(key)

    async def async_keys(self) -> list[str]:
        """Return all cache keys."""
        await self.async_load()
        assert self._index is not None
        return sorted(self._index)

    async def async_remove(self) -> None:
        """Remove every persisted cache file."""
        await self.async_load()
        assert self._index is not None

        async with self._lock:
            keys = list(self._index)
            self._index.clear()
            self._values.clear()

        for key in keys:
            await self._store_for(key).async_remove()
        self._stores.clear()
        await self._index_store.async_remove()
        await self.hass.async_add_executor_job(
            shutil.rmtree,
            Path(self.hass.config.path(STORAGE_DIR, _STORAGE_ROOT)),
            True,
        )

    def get_dir(self, subdir: str | None = None) -> CacheDir:
        """Return a virtual directory backed by this cache."""
        return CacheDir(self, subdir or "")


class CacheDir:
    """Virtual cache directory supporting the / operator."""

    def __init__(self, cache: MeteocatCache, prefix: str) -> None:
        self._cache = cache
        self._prefix = prefix.strip("/")

    def __truediv__(self, name: str) -> CacheFile:
        name = str(name).strip("/")
        key = f"{self._prefix}/{name}" if self._prefix else name
        return CacheFile(self._cache, key)

    def __str__(self) -> str:
        return f".storage/{_STORAGE_ROOT}/{self._prefix or '.'}"


class CacheFile:
    """Virtual cache file providing the async operations used by the integration."""

    def __init__(self, cache: MeteocatCache, key: str) -> None:
        self._cache = cache
        self._key = key

    @property
    def name(self) -> str:
        """Return the file name portion of the key."""
        return self._key.rsplit("/", 1)[-1]

    async def async_exists(self) -> bool:
        """Return whether the file exists in the cache."""
        return await self._cache.async_exists(self._key)

    async def async_read_json(self) -> Any:
        """Read a JSON value, raising FileNotFoundError when missing."""
        value = await self._cache.async_get(self._key)
        if value is None:
            raise FileNotFoundError(self._key)
        return value

    async def async_write_json(self, data: Any) -> None:
        """Write a JSON-serializable value."""
        await self._cache.async_set(self._key, data)

    async def async_delete(self) -> None:
        """Delete this file from the cache."""
        await self._cache.async_delete(self._key)

    def __str__(self) -> str:
        return f".storage/{_STORAGE_ROOT}/{self._key}"

    def __repr__(self) -> str:
        return self.__str__()


def get_cache(hass: HomeAssistant) -> MeteocatCache:
    """Return the domain-wide cache for this Home Assistant instance."""
    cache = hass.data.get(_CACHE_DATA_KEY)
    if not isinstance(cache, MeteocatCache):
        cache = MeteocatCache(hass)
        hass.data[_CACHE_DATA_KEY] = cache
    return cache


def get_storage_dir(hass: HomeAssistant, subdir: str | None = None) -> CacheDir:
    """Return a virtual cache directory in place of the legacy filesystem path."""
    return get_cache(hass).get_dir(subdir)
