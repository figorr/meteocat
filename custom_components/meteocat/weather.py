from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
    Forecast,
)
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

from .const import (
    DOMAIN,
    ATTRIBUTION,
    WIND_SPEED_CODE,
    WIND_DIRECTION_CODE,
    TEMPERATURE_CODE,
    HUMIDITY_CODE,
    PRESSURE_CODE,
    PRECIPITATION_CODE,
    WIND_GUST_CODE,
)
from .coordinator import (
    HourlyForecastCoordinator,
    DailyForecastCoordinator,
    MeteocatSensorCoordinator,
    MeteocatUviFileCoordinator,
    MeteocatConditionCoordinator,
)

_LOGGER = logging.getLogger(__name__)

@callback
async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Meteocat weather entity from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]

    hourly_forecast_coordinator = entry_data.get("hourly_forecast_coordinator")
    daily_forecast_coordinator = entry_data.get("daily_forecast_coordinator")
    sensor_coordinator = entry_data.get("sensor_coordinator")
    uvi_file_coordinator = entry_data.get("uvi_file_coordinator")
    condition_coordinator = entry_data.get("condition_coordinator")

    async_add_entities([
        MeteocatWeatherEntity(
            hourly_forecast_coordinator,
            daily_forecast_coordinator,
            sensor_coordinator,
            uvi_file_coordinator,
            condition_coordinator,
            entry_data
        )
    ])

class MeteocatWeatherEntity(CoordinatorEntity, WeatherEntity):
    """Representation of a Meteocat Weather Entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_precipitation_probability_unit = PERCENTAGE
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_wind_bearing_unit = DEGREE
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )

    def __init__(
        self,
        hourly_forecast_coordinator: HourlyForecastCoordinator,
        daily_forecast_coordinator: DailyForecastCoordinator,
        sensor_coordinator: MeteocatSensorCoordinator,
        uvi_file_coordinator: MeteocatUviFileCoordinator,
        condition_coordinator: MeteocatConditionCoordinator,
        entry_data: dict,
    ) -> None:
        """Initialize the weather entity."""
        super().__init__(daily_forecast_coordinator)
        self._hourly_forecast_coordinator = hourly_forecast_coordinator
        self._daily_forecast_coordinator = daily_forecast_coordinator
        self._sensor_coordinator = sensor_coordinator
        self._uvi_file_coordinator = uvi_file_coordinator
        self._condition_coordinator = condition_coordinator
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"Weather {self._town_name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return f"weather.{DOMAIN}_{self._station_id}"

    @property
    def condition(self) -> Optional[str]:
        """Return the current weather condition."""
        condition_data = self._condition_coordinator.data or {}
        return condition_data.get("condition")

    def _get_latest_sensor_value(self, code: str) -> Optional[float]:
        """Helper method to retrieve the latest sensor value."""
        sensor_code = code
        if not sensor_code:
            return None

        stations = self._sensor_coordinator.data or []
        for station in stations:
            variables = station.get("variables", [])
            variable_data = next(
                (var for var in variables if var.get("codi") == sensor_code),
                None,
            )
            if variable_data:
                lectures = variable_data.get("lectures", [])
                if lectures:
                    return lectures[-1].get("valor")
        return None

    @property
    def native_temperature(self) -> Optional[float]:
        return self._get_latest_sensor_value(TEMPERATURE_CODE)

    @property
    def humidity(self) -> Optional[float]:
        return self._get_latest_sensor_value(HUMIDITY_CODE)

    @property
    def native_pressure(self) -> Optional[float]:
        return self._get_latest_sensor_value(PRESSURE_CODE)

    @property
    def native_wind_speed(self) -> Optional[float]:
        return self._get_latest_sensor_value(WIND_SPEED_CODE)

    @property
    def native_wind_gust_speed(self) -> Optional[float]:
        return self._get_latest_sensor_value(WIND_GUST_CODE)
    
    @property
    def wind_bearing(self) -> Optional[float]:
        return self._get_latest_sensor_value(WIND_DIRECTION_CODE)

    @property
    def uv_index(self) -> Optional[float]:
        """Return the UV index."""
        uvi_data = self._uvi_file_coordinator.data or {}
        return uvi_data.get("uvi")

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        await self._daily_forecast_coordinator.async_request_refresh()
        daily_forecasts = self._daily_forecast_coordinator.get_all_daily_forecasts()
        if not daily_forecasts:
            return None

        return [
            Forecast(
                datetime=forecast["date"],
                temperature=forecast["temperature_max"],
                templow=forecast["temperature_min"],
                precipitation_probability=forecast["precipitation"],
                condition=forecast["condition"],
            )
            for forecast in daily_forecasts
        ]
    
    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        await self._hourly_forecast_coordinator.async_request_refresh()
        hourly_forecasts = self._hourly_forecast_coordinator.get_all_hourly_forecasts()
        if not hourly_forecasts:
            return None

        return [
            Forecast(
                datetime=forecast["datetime"],
                temperature=forecast["temperature"],
                precipitation=forecast["precipitation"],
                condition=forecast["condition"],
                wind_speed=forecast["wind_speed"],
                wind_bearing=forecast["wind_bearing"],
                humidity=forecast["humidity"],
            )
            for forecast in hourly_forecasts
        ]

    async def async_update(self) -> None:
        """Update the weather entity."""
        await self._hourly_forecast_coordinator.async_request_refresh()
        await self._daily_forecast_coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=f"Meteocat {self._station_id}",
            manufacturer="Meteocat",
            model="Meteocat API",
        )
