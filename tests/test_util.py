"""Tests for Meteocat utility functions."""

from datetime import date, datetime

import pytest

from custom_components.meteocat.util import (
    OptionalDateSelector,
    api_key_expiry_date,
    is_future_date,
    parse_issue_date,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        (date(2026, 1, 15), date(2026, 1, 15)),
        (datetime(2026, 1, 15, 12, 30), date(2026, 1, 15)),
        ("2026-01-15", date(2026, 1, 15)),
        ("not-a-date", None),
    ],
)
def test_parse_issue_date(value, expected):
    """Test parsing stored API key issue dates."""
    assert parse_issue_date(value) == expected


@pytest.mark.parametrize(
    ("issue_date", "expected"),
    [
        (date(2024, 1, 31), date(2025, 1, 31)),
        (date(2024, 2, 29), date(2025, 2, 28)),
        (date(2025, 12, 1), date(2026, 12, 1)),
    ],
)
def test_api_key_expiry_date(issue_date, expected):
    """Test calculating the API key expiry date."""
    assert api_key_expiry_date(issue_date) == expected


def test_is_future_date():
    """Test checking whether a date is in the future."""
    today = date(2026, 1, 15)

    assert not is_future_date(today, today)
    assert not is_future_date(date(2026, 1, 14), today)
    assert is_future_date(date(2026, 1, 16), today)


def test_optional_date_selector_allows_empty_values():
    """Test that the date selector accepts empty values."""
    selector = OptionalDateSelector()

    assert selector(None) is None
    assert selector("") == ""
    assert selector("2026-01-15") == "2026-01-15"
