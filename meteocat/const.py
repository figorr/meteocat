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

# Códigos de sensores de la API
WIND_SPEED = "30"  # Velocidad del viento
WIND_DIRECTION = "31"  # Dirección del viento
TEMPERATURE = "32"  # Temperatura
HUMIDITY = "33"  # Humedad relativa
PRESSURE = "34"  # Presión atmosférica
PRECIPITATION = "35"  # Precipitación
UV_INDEX = "39"  # UV
MAX_TEMPERATURE = "40"  # Temperatura máxima
MIN_TEMPERATURE = "42"  # Temperatura mínima
WIND_GUST = "50"  # Racha de viento

# Unidades de medida de los sensores
WIND_SPEED_UNIT = "m/s"
WIND_DIRECTION_UNIT = "°"
TEMPERATURE_UNIT = "°C"
HUMIDITY_UNIT = "%"
PRESSURE_UNIT = "hPa"
PRECIPITATION_UNIT = "mm"
UV_INDEX_UNIT = "UV"

# Mapeo de códigos 'estatCel' a condiciones de Home Assistant
CONDITION_MAPPING = {
    "sunny": [1],
    "clear-night": [1],
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
