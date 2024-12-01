# Constantes generales
DOMAIN = "meteocat"
BASE_URL = "https://api.meteo.cat"
MUNICIPIS_LIST_URL = "/referencia/v1/municipis"
MUNICIPIS_HORA_URL = "/pronostic/v1/municipalHoraria/{codi}"
MUNICIPIS_DIA_URL = "/pronostic/v1/municipal/{codi}"

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
