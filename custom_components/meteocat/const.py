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
STATION_TYPE = "station_type"
LATITUDE = "latitude"
LONGITUDE = "longitude"
ALTITUDE = "altitude"
REGION_ID = "region_id"
REGION_NAME = "region_name"
PROVINCE_ID = "province_id"
PROVINCE_NAME = "province_name"
STATION_STATUS = "station_status"
HOURLY_FORECAST_FILE_STATUS = "hourly_forecast_file_status"
DAILY_FORECAST_FILE_STATUS = "daily_forecast_file_status"
UVI_FILE_STATUS = "uvi_file_status"

from homeassistant.const import Platform

ATTRIBUTION = "Powered by Meteocatpy"
PLATFORMS = [Platform.SENSOR, Platform.WEATHER]
DEFAULT_NAME = "METEOCAT"

# Tiempos para validación de API
DEFAULT_VALIDITY_DAYS = 1  # Número de días a partir de los cuales se considera que el archivo de información está obsoleto
DEFAULT_VALIDITY_HOURS = 5  # Hora a partir de la cuall la API tiene la información actualizada de predicciones disponible para descarga
DEFAULT_VALIDITY_MINUTES = 0 # Minutos a partir de los cuales la API tiene la información actualizada de predicciones disponible para descarga

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
