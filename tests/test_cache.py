from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from homeassistant.helpers.storage import Store

from custom_components.meteocat.cache import (
    MeteocatCache,
    get_cache,
    get_storage_dir,
)


async def test_cache_roundtrip_and_delete(hass) -> None:
    cache = get_cache(hass)

    await cache.async_set("files/example.json", {"value": 1})

    value = await cache.async_get("files/example.json")
    assert value == {"value": 1}

    value["value"] = 2
    assert await cache.async_get("files/example.json") == {"value": 1}
    assert await cache.async_exists("files/example.json") is True
    assert await cache.async_keys() == ["files/example.json"]

    await cache.async_delete("files/example.json")
    assert await cache.async_exists("files/example.json") is False
    assert await cache.async_get("files/example.json") is None
    assert await cache.async_keys() == []


async def test_cache_uses_shared_storage_folder(hass, hass_storage) -> None:
    cache = get_cache(hass)

    await cache.async_set("files/example.json", {"value": 1})

    assert "meteocat/files/example.json" in hass_storage
    assert "meteocat/index" in hass_storage
    assert not any(key.startswith("meteocat.cache") for key in hass_storage)


async def test_cache_migrates_hashed_store_files(hass, hass_storage) -> None:
    key = "files/legacy-store.json"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    old_store = Store[dict[str, bool]](hass, 1, f"meteocat.cache.{digest}")
    await old_store.async_save({"legacy": True})
    old_index = Store[list[str]](hass, 1, "meteocat.cache_index")
    await old_index.async_save([key])

    cache = MeteocatCache(hass)
    await cache.async_load()

    assert await cache.async_get(key) == {"legacy": True}
    assert "meteocat/files/legacy-store.json" in hass_storage
    assert "meteocat.cache_index" not in hass_storage
    assert f"meteocat.cache.{digest}" not in hass_storage


async def test_cache_file_api(hass) -> None:
    files = get_storage_dir(hass, "files")
    cache_file = files / "example.json"

    assert cache_file.name == "example.json"
    assert await cache_file.async_exists() is False
    with pytest.raises(FileNotFoundError):
        await cache_file.async_read_json()

    await cache_file.async_write_json({"plans": []})
    assert await cache_file.async_exists() is True
    assert await cache_file.async_read_json() == {"plans": []}

    await cache_file.async_delete()
    assert await cache_file.async_exists() is False


async def test_cache_delete_prefix(hass) -> None:
    cache = get_cache(hass)
    await cache.async_set("files/a.json", 1)
    await cache.async_set("files/b.json", 2)
    await cache.async_set("assets/c.json", 3)

    await cache.async_delete_prefix("files/")

    assert await cache.async_keys() == ["assets/c.json"]


async def test_legacy_cache_migration(hass) -> None:
    legacy_dir = Path(hass.config.path("meteocat_files"))
    legacy_file = legacy_dir / "files" / "legacy.json"

    def create_legacy_file() -> None:
        legacy_file.parent.mkdir(parents=True)
        legacy_file.write_text(json.dumps({"legacy": True}), encoding="utf-8")

    await hass.async_add_executor_job(create_legacy_file)

    cache = MeteocatCache(hass)
    await cache.async_load()

    assert await cache.async_get("files/legacy.json") == {"legacy": True}
    assert await hass.async_add_executor_job(legacy_dir.exists) is False


async def test_get_cache_returns_singleton(hass) -> None:
    assert get_cache(hass) is get_cache(hass)
