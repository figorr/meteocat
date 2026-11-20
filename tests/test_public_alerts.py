"""Tests for merging API alerts with the public SMP feed."""

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import custom_components.meteocat.coordinator as coordinator_module
from custom_components.meteocat.coordinator import MeteocatAlertsRegionCoordinator

TIMEZONE = ZoneInfo("Europe/Madrid")
PERIODS = ("00-06", "06-12", "12-18", "18-00")


def make_region_coordinator():
    """Create a region coordinator without Home Assistant setup."""
    coordinator = object.__new__(MeteocatAlertsRegionCoordinator)
    coordinator.region_id = "11"
    return coordinator


def make_alert(meteor, start, end, emission, comment, day):
    """Build an alert in the API/public SMP schema."""
    periodes = [
        {
            "nom": period,
            "afectacions": [
                {
                    "idComarca": 11,
                    "llindar": "Test threshold",
                    "perill": 1,
                    "nivell": 1,
                }
            ],
        }
        for period in PERIODS
    ]
    return {
        "estat": {"nom": "Obert"},
        "meteor": {"nom": meteor},
        "avisos": [
            {
                "tipus": "Avís",
                "dataEmisio": emission.isoformat(),
                "dataInici": start.isoformat(),
                "dataFi": end.isoformat(),
                "evolucions": [
                    {
                        "dia": day.isoformat(),
                        "comentari": comment,
                        "periodes": periodes,
                    }
                ],
                "estat": "Vigent",
            }
        ],
    }


def make_payload(alerts):
    """Wrap alerts in the stored alert payload."""
    return {
        "actualitzat": {"dataUpdate": datetime.now(TIMEZONE).isoformat()},
        "dades": alerts,
    }


def test_current_api_alert_wins_over_future_public_alert():
    """A current API alert is preferred over a future public alert."""
    now = datetime.now(TIMEZONE)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    coordinator = make_region_coordinator()
    api_data = make_payload(
        [
            make_alert(
                "Vent",
                now - timedelta(hours=1),
                now + timedelta(hours=1),
                now - timedelta(hours=2),
                "API current alert",
                today,
            )
        ]
    )
    public_data = make_payload(
        [
            make_alert(
                "Vent",
                tomorrow + timedelta(hours=6),
                tomorrow + timedelta(hours=18),
                now,
                "Public future alert",
                tomorrow,
            )
        ]
    )

    result = coordinator._merge_alert_data(api_data, public_data)

    detail = result["detalles"]["meteor"]["Vent"]
    assert detail["comentario"] == "API current alert"
    assert detail["source"] == "api"
    assert result["sources"] == ["api"]
    assert result["api_alerts"] == 1
    assert result["public_alerts"] == 0


def test_newer_public_alert_wins_for_the_same_period():
    """A newer public emission wins when both sources describe the same alert."""
    now = datetime.now(TIMEZONE)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)
    coordinator = make_region_coordinator()
    api_data = make_payload(
        [
            make_alert(
                "Vent",
                start,
                end,
                now - timedelta(hours=2),
                "Older API version",
                today,
            )
        ]
    )
    public_data = make_payload(
        [
            make_alert(
                "Vent",
                start,
                end,
                now,
                "Newer public version",
                today,
            )
        ]
    )

    result = coordinator._merge_alert_data(api_data, public_data)

    detail = result["detalles"]["meteor"]["Vent"]
    assert detail["comentario"] == "Newer public version"
    assert detail["source"] == "public"
    assert result["sources"] == ["public"]
    assert result["api_alerts"] == 0
    assert result["public_alerts"] == 1


def test_public_alert_is_used_when_api_has_no_data():
    """A public alert is shown when the API cache has no data."""
    now = datetime.now(TIMEZONE)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    coordinator = make_region_coordinator()
    public_data = make_payload(
        [
            make_alert(
                "Vent",
                tomorrow + timedelta(hours=6),
                tomorrow + timedelta(hours=18),
                now,
                "Public future alert",
                tomorrow,
            )
        ]
    )

    result = coordinator._merge_alert_data(None, public_data)

    detail = result["detalles"]["meteor"]["Vent"]
    assert detail["comentario"] == "Public future alert"
    assert detail["source"] == "public"
    assert result["sources"] == ["public"]
    assert result["api_updated"] is None
    assert result["public_updated"] is not None


def test_expired_public_alert_does_not_hide_current_api_alert():
    """An expired public alert is skipped before the current API alert."""
    now = datetime.now(TIMEZONE)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    coordinator = make_region_coordinator()
    api_data = make_payload(
        [
            make_alert(
                "Vent",
                now - timedelta(minutes=30),
                now + timedelta(hours=1),
                now - timedelta(hours=2),
                "API current alert",
                today,
            )
        ]
    )
    public_data = make_payload(
        [
            make_alert(
                "Vent",
                now - timedelta(hours=3),
                now - timedelta(hours=2),
                now,
                "Expired public alert",
                today,
            )
        ]
    )

    result = coordinator._merge_alert_data(api_data, public_data)

    detail = result["detalles"]["meteor"]["Vent"]
    assert detail["comentario"] == "API current alert"
    assert detail["source"] == "api"


def test_expired_public_alert_closes_region():
    """An expired public alert leaves the region in the closed state."""
    now = datetime.now(TIMEZONE)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    coordinator = make_region_coordinator()
    public_data = make_payload(
        [
            make_alert(
                "Vent",
                now - timedelta(hours=3),
                now - timedelta(hours=2),
                now,
                "Expired public alert",
                today,
            )
        ]
    )

    result = coordinator._merge_alert_data(None, public_data)

    assert result["activas"] == 0
    assert result["estado"] == "Tancat"
    assert result["detalles"]["meteor"] == {}
    assert result["sources"] == []
    assert result["api_alerts"] == 0
    assert result["public_alerts"] == 0


def test_region_reports_mixed_sources():
    """The region sensor metadata reflects alerts selected from both sources."""
    now = datetime.now(TIMEZONE)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    coordinator = make_region_coordinator()
    api_data = make_payload(
        [
            make_alert(
                "Vent",
                now - timedelta(hours=1),
                now + timedelta(hours=1),
                now - timedelta(hours=2),
                "API current alert",
                today,
            )
        ]
    )
    public_data = make_payload(
        [
            make_alert(
                "Neu",
                tomorrow + timedelta(hours=6),
                tomorrow + timedelta(hours=18),
                now,
                "Public future alert",
                tomorrow,
            )
        ]
    )

    result = coordinator._merge_alert_data(api_data, public_data)

    assert result["sources"] == ["api", "public"]
    assert result["api_alerts"] == 1
    assert result["public_alerts"] == 1
    assert result["api_updated"] is not None
    assert result["public_updated"] is not None
    assert result["detalles"]["meteor"]["Vent"]["source"] == "api"
    assert result["detalles"]["meteor"]["Neu"]["source"] == "public"


def test_force_bypasses_public_feed_cache(monkeypatch):
    """A forced fetch ignores the shared five-minute public feed cache."""

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        async def json(self, content_type=None):
            return [{"meteor": {"nom": "Vent"}}]

    class FakeSession:
        def __init__(self):
            self.calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            return FakeResponse()

    session = FakeSession()
    hass = SimpleNamespace(data={})
    monkeypatch.setattr(
        coordinator_module,
        "async_get_clientsession",
        lambda hass: session,
    )

    async def scenario():
        first = await coordinator_module._async_fetch_public_alerts(hass)
        cached = await coordinator_module._async_fetch_public_alerts(hass)
        forced = await coordinator_module._async_fetch_public_alerts(hass, force=True)
        return first, cached, forced

    first, cached, forced = asyncio.run(scenario())

    assert first is cached
    assert forced is not first
    assert session.calls == 6
