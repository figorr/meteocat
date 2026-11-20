"""Tests for regional alert processing."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.meteocat.coordinator import MeteocatAlertsRegionCoordinator

TIMEZONE = ZoneInfo("Europe/Madrid")
PERIODS = ("00-06", "06-12", "12-18", "18-00")


def make_region_coordinator():
    """Create a region coordinator without Home Assistant setup."""
    coordinator = object.__new__(MeteocatAlertsRegionCoordinator)
    coordinator.region_id = "1"
    return coordinator


def make_alert_data(start, end, meteor="Vent"):
    """Build alert cache data with an affected period for the current day."""
    now = datetime.now(TIMEZONE)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    periods = [
        {
            "nom": period,
            "afectacions": [
                {
                    "idComarca": 1,
                    "llindar": "Test threshold",
                    "perill": 1,
                    "nivell": 1,
                }
            ],
        }
        for period in PERIODS
    ]
    return {
        "actualitzat": {"dataUpdate": now.isoformat()},
        "dades": [
            {
                "estat": {"nom": "Obert"},
                "meteor": {"nom": meteor},
                "avisos": [
                    {
                        "dataInici": start.isoformat(),
                        "dataFi": end.isoformat(),
                        "evolucions": [
                            {
                                "dia": day.isoformat(),
                                "comentari": "Test alert",
                                "periodes": periods,
                            }
                        ],
                        "estat": "Vigent",
                    }
                ],
            }
        ],
    }


def test_expired_alert_is_not_processed():
    """An alert whose end time has passed is no longer active."""
    now = datetime.now(TIMEZONE)
    coordinator = make_region_coordinator()
    data = make_alert_data(
        now - timedelta(hours=2),
        now - timedelta(hours=1),
    )

    result = coordinator._process_alerts_data(data)

    assert result["activas"] == 0
    assert result["estado"] == "Tancat"
    assert result["detalles"]["meteor"] == {}


def test_active_alert_is_processed():
    """An alert inside its start and end window remains active."""
    now = datetime.now(TIMEZONE)
    coordinator = make_region_coordinator()
    data = make_alert_data(
        now - timedelta(hours=1),
        now + timedelta(hours=1),
    )

    result = coordinator._process_alerts_data(data)

    assert result["activas"] == 1
    assert "Vent" in result["detalles"]["meteor"]


def test_future_alert_is_processed():
    """An upcoming alert remains visible before its start time."""
    now = datetime.now(TIMEZONE)
    coordinator = make_region_coordinator()
    data = make_alert_data(
        now + timedelta(hours=1),
        now + timedelta(hours=2),
    )

    result = coordinator._process_alerts_data(data)

    assert result["activas"] == 1
    assert "Vent" in result["detalles"]["meteor"]
