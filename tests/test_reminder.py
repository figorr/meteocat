"""Tests for Meteocat API key expiry reminders."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.components import persistent_notification
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.meteocat import reminder
from custom_components.meteocat.const import (
    API_KEY_REMINDER_DAYS,
    API_KEY_REMINDER_HOUR,
    CONF_API_KEY_DATE,
    CONF_API_KEY_REMINDER,
    DOMAIN,
)
from custom_components.meteocat.util import api_key_expiry_date


def make_entry(
    issue_date: str | None,
    *,
    reminder_enabled: bool = True,
    entry_id: str = "test-entry",
) -> MockConfigEntry:
    """Create a config entry for reminder tests."""
    data = {}
    if issue_date is not None:
        data[CONF_API_KEY_DATE] = issue_date
    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options={CONF_API_KEY_REMINDER: reminder_enabled},
        entry_id=entry_id,
    )


def patch_notifications(monkeypatch) -> tuple[Mock, Mock]:
    """Patch persistent notification helpers."""
    create = Mock()
    dismiss = Mock()
    monkeypatch.setattr(persistent_notification, "async_create", create)
    monkeypatch.setattr(persistent_notification, "async_dismiss", dismiss)
    return create, dismiss


def patch_tracking(monkeypatch) -> list[tuple]:
    """Capture scheduled callbacks without waiting for the clock."""
    scheduled = []

    def fake_track(hass, action, point_in_time):
        scheduled.append((action, point_in_time))
        return Mock()

    monkeypatch.setattr(reminder, "async_track_point_in_utc_time", fake_track)
    return scheduled


@pytest.mark.usefixtures("freezer")
def test_schedules_expiry_and_reminder(hass, monkeypatch, freezer) -> None:
    """Test scheduling both the expiry and reminder callbacks."""
    freezer.move_to("2025-01-01 12:00:00+00:00")
    scheduled = patch_tracking(monkeypatch)
    create, _dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-02")
    entry.async_start_reauth = Mock()

    cancel = reminder.async_schedule_api_key_reminder(hass, entry)

    assert cancel is not None
    assert len(scheduled) == 2
    create.assert_not_called()
    for action, _point_in_time in scheduled:
        action()
    assert create.call_count == 1
    entry.async_start_reauth.assert_called_once_with(hass)
    cancel()


@pytest.mark.usefixtures("freezer")
def test_notifies_when_inside_reminder_window(hass, monkeypatch, freezer) -> None:
    """Test notifying immediately when the reminder window already started."""
    freezer.move_to("2026-01-01 12:00:00+00:00")
    scheduled = patch_tracking(monkeypatch)
    create, _dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-02")

    reminder.async_schedule_api_key_reminder(hass, entry)

    create.assert_called_once()
    assert create.call_args.kwargs["notification_id"] == (
        "meteocat_api_key_expiry_test-entry"
    )
    assert "2026-01-02" in create.call_args.args[1]
    assert len(scheduled) == 1


@pytest.mark.usefixtures("freezer")
def test_expired_key_starts_reauth(hass, monkeypatch, freezer) -> None:
    """Test requesting reauthentication when the key has expired."""
    freezer.move_to("2026-01-02 12:00:00+00:00")
    scheduled = patch_tracking(monkeypatch)
    _create, dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-01")
    entry.async_start_reauth = Mock()

    result = reminder.async_schedule_api_key_reminder(hass, entry)

    assert result is None
    assert scheduled == []
    entry.async_start_reauth.assert_called_once_with(hass)
    dismiss.assert_called_once()


@pytest.mark.usefixtures("freezer")
def test_disabled_reminder_only_schedules_expiry(hass, monkeypatch, freezer) -> None:
    """Test that disabling reminders only schedules expiry handling."""
    freezer.move_to("2025-01-01 12:00:00+00:00")
    scheduled = patch_tracking(monkeypatch)
    create, _dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-02", reminder_enabled=False)

    cancel = reminder.async_schedule_api_key_reminder(hass, entry)

    assert cancel is not None
    assert len(scheduled) == 1
    create.assert_not_called()


@pytest.mark.usefixtures("freezer")
def test_missing_date_does_not_schedule(hass, monkeypatch, freezer) -> None:
    """Test that entries without an issue date do not schedule reminders."""
    freezer.move_to("2025-01-01 12:00:00+00:00")
    scheduled = patch_tracking(monkeypatch)
    _create, dismiss = patch_notifications(monkeypatch)
    entry = make_entry(None)

    result = reminder.async_schedule_api_key_reminder(hass, entry)

    assert result is None
    assert scheduled == []
    dismiss.assert_called_once()


def test_cancel_reminder(hass, monkeypatch) -> None:
    """Test cancelling the timer and dismissing the notification."""
    _create, dismiss = patch_notifications(monkeypatch)
    unsub = Mock()
    entry = make_entry("2025-01-02")
    entry.runtime_data = SimpleNamespace(reminder_unsub=unsub)

    reminder.async_cancel_api_key_reminder(hass, entry)

    unsub.assert_called_once()
    assert entry.runtime_data.reminder_unsub is None
    dismiss.assert_called_once()


def test_scheduled_callback_reauthenticates(hass, monkeypatch) -> None:
    """Test that the expiry callback dismisses the notification and reauths."""
    _create, dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-02")
    entry.async_start_reauth = Mock()

    reminder._async_handle_api_key_expired(hass, entry, datetime(2026, 1, 2, 12, 0, 0))

    entry.async_start_reauth.assert_called_once_with(hass)
    dismiss.assert_called_once()


@pytest.mark.usefixtures("freezer")
async def test_reminder_fires_after_real_time_jump(hass, monkeypatch, freezer) -> None:
    """The reminder notification fires when the clock reaches the window."""
    freezer.move_to("2025-01-01 12:00:00+00:00")
    create, _dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-02")

    cancel = reminder.async_schedule_api_key_reminder(hass, entry)
    assert cancel is not None
    create.assert_not_called()

    expiry = api_key_expiry_date(date(2025, 1, 2))
    reminder_day = expiry - timedelta(days=API_KEY_REMINDER_DAYS)
    fire_at = dt_util.start_of_local_day(reminder_day) + timedelta(
        hours=API_KEY_REMINDER_HOUR, seconds=1
    )
    freezer.move_to(fire_at)
    async_fire_time_changed(hass, fire_at)
    await hass.async_block_till_done()

    create.assert_called_once()
    assert create.call_args.kwargs["notification_id"] == (
        "meteocat_api_key_expiry_test-entry"
    )
    cancel()


@pytest.mark.usefixtures("freezer")
async def test_disabled_reminder_reauths_after_real_time_jump(
    hass, monkeypatch, freezer
) -> None:
    """The expiry timer starts reauth when the clock reaches expiry."""
    freezer.move_to("2025-01-01 12:00:00+00:00")
    create, dismiss = patch_notifications(monkeypatch)
    entry = make_entry("2025-01-02", reminder_enabled=False)
    entry.async_start_reauth = Mock()

    cancel = reminder.async_schedule_api_key_reminder(hass, entry)
    assert cancel is not None
    create.assert_not_called()

    fire_at = dt_util.start_of_local_day(api_key_expiry_date(date(2025, 1, 2))) + (
        timedelta(seconds=1)
    )
    freezer.move_to(fire_at)
    async_fire_time_changed(hass, fire_at)
    await hass.async_block_till_done()

    entry.async_start_reauth.assert_called_once_with(hass)
    dismiss.assert_called_with(hass, "meteocat_api_key_expiry_test-entry")
    create.assert_not_called()
    cancel()
