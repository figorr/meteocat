from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteocat.cache import CacheFile, get_storage_dir
from custom_components.meteocat.coordinator import _update_quotes
from custom_components.meteocat.helpers import (
    async_delete_unused_quotes_file,
    async_migrate_legacy_quotes,
    get_quotes_file,
    get_quotes_id,
)


async def test_quotes_file_is_scoped_to_api_key(hass: HomeAssistant) -> None:
    file_a = get_quotes_file(hass, "key-a")
    file_b = get_quotes_file(hass, "key-b")

    assert file_a.name == f"quotes_{get_quotes_id('key-a')}.json"
    assert file_a.name == get_quotes_file(hass, "key-a").name
    assert file_a.name != file_b.name
    assert "key-a" not in file_a.name
    assert "key-b" not in file_b.name


async def test_update_quotes_uses_api_key_file(hass: HomeAssistant) -> None:
    data_a = {
        "plans": [
            {
                "nom": "XEMA",
                "consultesRealitzades": 1,
                "consultesRestants": 9,
            }
        ]
    }
    data_b = {
        "plans": [
            {
                "nom": "XEMA",
                "consultesRealitzades": 5,
                "consultesRestants": 5,
            }
        ]
    }
    file_a = get_quotes_file(hass, "key-a")
    file_b = get_quotes_file(hass, "key-b")
    await file_a.async_write_json(data_a)
    await file_b.async_write_json(data_b)

    await _update_quotes(hass, "key-a", "XEMA")

    assert (await file_a.async_read_json())["plans"][0]["consultesRealitzades"] == 2
    assert (await file_a.async_read_json())["plans"][0]["consultesRestants"] == 8
    assert (await file_b.async_read_json())["plans"][0]["consultesRealitzades"] == 5
    assert (await file_b.async_read_json())["plans"][0]["consultesRestants"] == 5


async def test_legacy_quotes_migration_strips_client(hass: HomeAssistant) -> None:
    legacy_file = get_storage_dir(hass, "files") / "quotes.json"
    await legacy_file.async_write_json(
        {
            "client": {"nom": "Private User"},
            "actualitzat": {"dataUpdate": "2026-01-01T00:00:00+00:00"},
            "plans": [],
        }
    )

    await async_migrate_legacy_quotes(hass, "key-a")

    migrated = await get_quotes_file(hass, "key-a").async_read_json()
    assert migrated == {
        "actualitzat": {"dataUpdate": "2026-01-01T00:00:00+00:00"},
        "plans": [],
    }
    assert not await legacy_file.async_exists()


async def test_legacy_quotes_kept_when_read_fails(
    hass: HomeAssistant, monkeypatch
) -> None:
    legacy_file = get_storage_dir(hass, "files") / "quotes.json"
    await legacy_file.async_write_json({"plans": []})
    original_read = CacheFile.async_read_json

    async def fail_legacy_read(self):
        if self.name == "quotes.json":
            raise ValueError("corrupt cache")
        return await original_read(self)

    monkeypatch.setattr(CacheFile, "async_read_json", fail_legacy_read)

    await async_migrate_legacy_quotes(hass, "key-a")

    assert await legacy_file.async_exists()
    assert not await get_quotes_file(hass, "key-a").async_exists()


async def test_delete_unused_quotes_file(hass: HomeAssistant) -> None:
    entry_a = MockConfigEntry(
        domain="meteocat",
        data={"api_key": "key-a"},
        entry_id="entry-a",
    )
    entry_b = MockConfigEntry(
        domain="meteocat",
        data={"api_key": "key-b"},
        entry_id="entry-b",
    )
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    file_a = get_quotes_file(hass, "key-a")
    file_b = get_quotes_file(hass, "key-b")
    await file_a.async_write_json({"plans": []})
    await file_b.async_write_json({"plans": []})

    await async_delete_unused_quotes_file(hass, "key-a", exclude_entry_id="entry-a")

    assert not await file_a.async_exists()
    assert await file_b.async_exists()


async def test_delete_quotes_file_kept_for_shared_api_key(
    hass: HomeAssistant,
) -> None:
    entry_a = MockConfigEntry(
        domain="meteocat",
        data={"api_key": "key-a"},
        entry_id="entry-a",
    )
    entry_b = MockConfigEntry(
        domain="meteocat",
        data={"api_key": "key-a"},
        entry_id="entry-b",
    )
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    quotes_file = get_quotes_file(hass, "key-a")
    await quotes_file.async_write_json({"plans": []})

    await async_delete_unused_quotes_file(hass, "key-a", exclude_entry_id="entry-a")

    assert await quotes_file.async_exists()
