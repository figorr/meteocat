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
from homeassistant.components.weather import Forecast
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPrecipitationDepth,
    UnitOfVolumetricFlux,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

from .const import (
    DOMAIN,
    ATTRIBUTION,
)
from .coordinator import (
    HourlyForecastCoordinator,
    DailyForecastCoordinator,
)

_LOGGER = logging.getLogger(__name__)

@callback
async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Meteocat weather entity from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]

    hourly_forecast_coordinator = entry_data.get("hourly_forecast_coordinator")
    daily_forecast_coordinator = entry_data.get("daily_forecast_coordinator")

    async_add_entities([
        MeteocatWeatherEntity(hourly_forecast_coordinator, daily_forecast_coordinator, entry_data)
    ])

class MeteocatWeatherEntity(CoordinatorEntity, WeatherEntity):
    """Representation of a Meteocat Weather Entity."""
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
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
        entry_data: dict,
    ) -> None:
        """Initialize the weather entity."""
        super().__init__(hourly_forecast_coordinator)
        self._hourly_forecast_coordinator = hourly_forecast_coordinator
        self._daily_forecast_coordinator = daily_forecast_coordinator
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
        forecast_today = self._daily_forecast_coordinator.get_forecast_for_today()
        if forecast_today:
            return forecast_today.get("condition")
        return None

    @property
    def temperature(self) -> Optional[float]:
        """Return the current temperature."""
        forecast_today = self._daily_forecast_coordinator.get_forecast_for_today()
        if forecast_today:
            return (forecast_today.get("temperature_max") + forecast_today.get("temperature_min")) / 2
        return None

    @property
    def forecast(self) -> list[Forecast]:
        """Return the daily forecast."""
        daily_forecasts = self._daily_forecast_coordinator.get_all_daily_forecasts()
        return [
            Forecast(
                datetime=forecast["date"],
                temperature=forecast["temperature_max"],
                templow=forecast["temperature_min"],
                precipitation=forecast["precipitation"],
                condition=forecast["condition"],
            )
            for forecast in daily_forecasts
        ]

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        hourly_forecasts = await self._hourly_forecast_coordinator.async_forecast_hourly()
        if not hourly_forecasts:
            return None

        return [
            Forecast(
                datetime=forecast.datetime,
                temperature=forecast.temperature,
                precipitation=forecast.precipitation,
                condition=forecast.condition,
                wind_speed=forecast.wind_speed,
                wind_bearing=forecast.wind_bearing,
                humidity=forecast.humidity,
            )
            for forecast in hourly_forecasts
        ]
    
    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        # Asegúrate de que los datos estén actualizados antes de procesarlos
        await self._daily_forecast_coordinator.async_request_refresh()

        # Obtén las predicciones diarias procesadas desde el coordinador
        daily_forecasts = self._daily_forecast_coordinator.get_all_daily_forecasts()
        if not daily_forecasts:
            return None

        # Convierte las predicciones a la estructura Forecast de Home Assistant
        return [
            Forecast(
                datetime=forecast["date"],
                temperature=forecast["temperature_max"],
                templow=forecast["temperature_min"],
                precipitation=forecast["precipitation"],
                condition=forecast["condition"],
            )
            for forecast in daily_forecasts
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
