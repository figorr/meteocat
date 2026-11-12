"""Utility functions for the Meteocat integration."""

from datetime import date, datetime
from typing import Any, override

from dateutil.relativedelta import relativedelta
from homeassistant.helpers.selector import DateSelector
from homeassistant.util import dt as dt_util

from .const import API_KEY_VALIDITY_MONTHS


class OptionalDateSelector(DateSelector):
    """Date selector that allows the field to be cleared."""

    @override
    def __call__(self, data: Any) -> Any:
        """Validate the passed selection, allowing an empty value."""
        if data is None or data == "":
            return data
        return super().__call__(data)


def parse_issue_date(value: Any) -> date | None:
    """Parse a stored API key issue date."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return dt_util.parse_date(value)


def api_key_expiry_date(issue_date: date) -> date:
    """Return the expiry date for an API key issued on the given date."""
    return issue_date + relativedelta(months=API_KEY_VALIDITY_MONTHS)


def is_future_date(value: date, today: date | None = None) -> bool:
    """Return whether a date is in the future."""
    return value > (today or dt_util.now().date())
