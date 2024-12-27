# Constantes generales
DOMAIN = "meteocat"
BASE_URL = "https://api.meteo.cat"
CONF_API_KEY = "api_key"
TOWN_NAME = "town_name"
TOWN_ID = "town_id"
VARIABLE_NAME = "variable_name"
VARIABLE_ID = "variable_id"
STATION_NAME = "station_name"
STATION_ID = "station_id"

from homeassistant.const import Platform

ATTRIBUTION = "Powered by Meteocatpy"
PLATFORMS = [Platform.SENSOR, Platform.WEATHER]
DEFAULT_NAME = "METEOCAT"


# Códigos de sensores de la API
WIND_SPEED = "wind_speed"  # Velocidad del viento
WIND_DIRECTION = "wind_direction"  # Dirección del viento
TEMPERATURE = "temperature"  # Temperatura
HUMIDITY = "humidity"  # Humedad relativa
PRESSURE = "pressure"  # Presión atmosférica
PRECIPITATION = "precipitation"  # Precipitación
PRECIPITATION_ACCUMULATED = "precipitation_accumulated" #Precipitación acumulada
SOLAR_GLOBAL_IRRADIANCE = "solar_global_irradiance"  # Irradiación solar global
UV_INDEX = "uv_index"  # UV
MAX_TEMPERATURE = "max_temperature"  # Temperatura máxima
MIN_TEMPERATURE = "min_temperature"  # Temperatura mínima
FEELS_LIKE = "feels_like"  # Sensación térmica
WIND_GUST = "wind_gust"  # Racha de viento
STATION_TIMESTAMP = "station_timestamp"  # Código de tiempo de la estación
CONDITION = "condition"  # Estado del cielo
MAX_TEMPERATURE_FORECAST = "max_temperature_forecast"  # Temperatura máxima prevista
MIN_TEMPERATURE_FORECAST = "min_temperature_forecast"  # Temperatura mínima prevista

# Definición de códigos para variables
WIND_SPEED_CODE = 30
WIND_DIRECTION_CODE = 31
TEMPERATURE_CODE = 32
HUMIDITY_CODE = 33
PRESSURE_CODE = 34
PRECIPITATION_CODE = 35
SOLAR_GLOBAL_IRRADIANCE_CODE = 36
UV_INDEX_CODE = 39
MAX_TEMPERATURE_CODE = 40
MIN_TEMPERATURE_CODE = 42
WIND_GUST_CODE = 50

# Mapeo de códigos 'estatCel' a condiciones de Home Assistant
CONDITION_MAPPING = {
    "sunny": [1],
    # "clear-night": [1],
    "partlycloudy": [2, 3],
    "cloudy": [4, 20, 21, 22],
    "rainy": [5, 6, 23],
    "pouring": [7, 8, 25],
    "lightning-rainy": [8, 24],
    "hail": [9],
    "snowy": [10, 26, 27, 28],
    "fog": [11, 12],
    "snow-rainy": [27, 29, 30],
}
