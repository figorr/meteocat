from __future__ import annotations

from homeassistant.components.weather import WeatherEntity
from homeassistant.const import TEMP_CELSIUS, TEMP_FAHRENHEIT
from meteocatpy.forecast import MeteocatForecast
import asyncio
import logging

from .const import (
    DOMAIN,
    CONF_API_KEY,
    TOWN_ID,
    TEMPERATURE,
    HUMIDITY,
    WIND_SPEED,
    WIND_DIRECTION
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configura el componente weather basado en una entrada de configuración."""
    api_key = config_entry.data[CONF_API_KEY]
    town_id = config_entry.data[TOWN_ID]

    forecast = MeteocatForecast(api_key)
    async_add_entities([MeteocatWeatherEntity(forecast, town_id)], True)


class MeteocatWeatherEntity(WeatherEntity):
    """Entidad de clima para la integración Meteocat."""

    def __init__(self, forecast: MeteocatForecast, town_id: str):
        """Inicializa la entidad MeteocatWeather."""
        self._forecast = forecast
        self._town_id = town_id
        self._attr_temperature_unit = TEMP_CELSIUS
        self._data = {}

    async def async_update(self):
        """Actualiza los datos meteorológicos."""
        try:
            # Obtener predicción horaria
            hourly_forecast = await self._forecast.get_prediccion_horaria(self._town_id)
            if hourly_forecast:
                # Procesar datos para extraer la temperatura y otra información relevante
                current_forecast = hourly_forecast["variables"]
                self._data = {
                    "temperature": current_forecast.get(TEMPERATURE, {}).get("valor", None),  # Código 32: Temperatura
                    "humidity": current_forecast.get(HUMIDITY, {}).get("valor", None),  # Código 33: Humedad relativa
                    "wind_speed": current_forecast.get(WIND_SPEED, {}).get("valor", None),  # Código 30: Velocidad del viento
                    "wind_bearing": current_forecast.get(WIND_DIRECTION, {}).get("valor", None),  # Código 31: Dirección del viento
                    "condition": self._get_condition(current_forecast),
                }
        except Exception as err:
            _LOGGER.error("Error al actualizar la predicción de Meteocat: %s", err)

    @property
    def name(self):
        """Retorna el nombre de la entidad."""
        return f"Clima {self._town_id}"

    @property
    def temperature(self):
        """Retorna la temperatura actual."""
        return self._data.get("temperature")

    @property
    def humidity(self):
        """Retorna la humedad relativa actual."""
        return self._data.get("humidity")

    @property
    def wind_speed(self):
        """Retorna la velocidad del viento."""
        return self._data.get("wind_speed")

    @property
    def wind_bearing(self):
        """Retorna la dirección del viento."""
        return self._data.get("wind_bearing")

    @property
    def condition(self):
        """Retorna la condición climática."""
        return self._data.get("condition")

    def _get_condition(self, variables):
        """Determina la condición del clima con base en los datos proporcionados."""
        # Mapea las condiciones basadas en variables específicas, como el código del tiempo
        # Esto puede ser modificado según las necesidades específicas de la API de Meteocat
        if variables.get("precipitation", {}).get("valor", 0) > 0:
            return "rainy"
        return "clear"
