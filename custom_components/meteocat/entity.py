# from __future__ import annotations

# import asyncio
# import logging
# from homeassistant.components.weather import WeatherEntity
# from homeassistant.const import (
#     DEGREE,
#     PERCENTAGE,
#     UnitOfPressure,
#     UnitOfSpeed,
#     UnitOfTemperature,
#     UnitOfVolumetricFlux,
# )

# from .const import (
#     DOMAIN,
#     CONF_API_KEY,
#     TOWN_ID,
#     TEMPERATURE,
#     HUMIDITY,
#     WIND_SPEED,
#     WIND_DIRECTION,
# )
# from .condition import get_condition_from_statcel
# from .coordinator import MeteocatEntityCoordinator


# _LOGGER = logging.getLogger(__name__)

# async def async_setup_entry(hass, config_entry, async_add_entities):
#     """Configura el componente weather basado en una entrada de configuración."""
#     api_key = config_entry.data[CONF_API_KEY]
#     town_id = config_entry.data[TOWN_ID]

#     # Crear el coordinador
#     coordinator = MeteocatEntityCoordinator(hass, api_key, town_id)
#     # Asegurarse de que el coordinador esté actualizado antes de agregar la entidad
#     await coordinator.async_refresh()

#     async_add_entities([MeteocatWeatherEntity(coordinator)], True)

# class MeteocatWeatherEntity(WeatherEntity):
#     """Entidad de clima para la integración Meteocat."""

#     def __init__(self, coordinator: MeteocatEntityCoordinator):
#         """Inicializa la entidad MeteocatWeather."""
#         self._coordinator = coordinator
#         self._attr_temperature_unit = UnitOfTemperature.CELSIUS
#         self._data = {}

#     async def async_update(self):
#         """Actualiza los datos meteorológicos."""
#         try:
#             # Usamos el coordinador para obtener los datos actualizados
#             if self._coordinator.data:
#                 hourly_forecast = self._coordinator.data["hourly_forecast"]
#                 current_forecast = hourly_forecast["variables"]
#                 codi_estatcel = current_forecast.get("estatCel", {}).get("valor")
#                 is_night = current_forecast.get("is_night", False)
#                 self._data = {
#                     "temperature": current_forecast.get(TEMPERATURE, {}).get("valor"),
#                     "humidity": current_forecast.get(HUMIDITY, {}).get("valor"),
#                     "wind_speed": current_forecast.get(WIND_SPEED, {}).get("valor"),
#                     "wind_bearing": current_forecast.get(WIND_DIRECTION, {}).get("valor"),
#                     "condition": get_condition_from_statcel(codi_estatcel, is_night)["condition"],
#                 }
#         except Exception as err:
#             _LOGGER.error("Error al actualizar la predicción de Meteocat: %s", err)

#     @property
#     def name(self):
#         """Retorna el nombre de la entidad."""
#         return f"Clima {self._coordinator._town_id}"

#     @property
#     def temperature(self):
#         """Retorna la temperatura actual."""
#         return self._data.get("temperature")

#     @property
#     def humidity(self):
#         """Retorna la humedad relativa actual."""
#         return self._data.get("humidity")

#     @property
#     def wind_speed(self):
#         """Retorna la velocidad del viento."""
#         return self._data.get("wind_speed")

#     @property
#     def wind_bearing(self):
#         """Retorna la dirección del viento."""
#         return self._data.get("wind_bearing")

#     @property
#     def condition(self):
#         """Retorna la condición climática."""
#         return self._data.get("condition")
