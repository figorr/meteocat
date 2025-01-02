from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo 
import logging
from homeassistant.helpers.entity import (
    DeviceInfo,
    EntityCategory,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
    UnitOfIrradiance,
)

from .const import (
    DOMAIN,
    TOWN_NAME,
    TOWN_ID,
    STATION_NAME,
    STATION_ID,
    WIND_SPEED,
    WIND_DIRECTION,
    TEMPERATURE,
    HUMIDITY,
    PRESSURE,
    PRECIPITATION,
    PRECIPITATION_ACCUMULATED,
    SOLAR_GLOBAL_IRRADIANCE,
    UV_INDEX,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    WIND_GUST,
    STATION_TIMESTAMP,
    CONDITION,
    MAX_TEMPERATURE_FORECAST,
    MIN_TEMPERATURE_FORECAST,
    HOURLY_FORECAST_FILE_STATUS,
    DAILY_FORECAST_FILE_STATUS,
    UVI_FILE_STATUS,
    WIND_SPEED_CODE,
    WIND_DIRECTION_CODE,
    TEMPERATURE_CODE,
    HUMIDITY_CODE,
    PRESSURE_CODE,
    PRECIPITATION_CODE,
    SOLAR_GLOBAL_IRRADIANCE_CODE,
    UV_INDEX_CODE,
    MAX_TEMPERATURE_CODE,
    MIN_TEMPERATURE_CODE,
    FEELS_LIKE,
    WIND_GUST_CODE,
    DEFAULT_VALIDITY_DAYS,
    DEFAULT_VALIDITY_HOURS,
    DEFAULT_VALIDITY_MINUTES,
)

from .coordinator import (
    MeteocatSensorCoordinator,
    MeteocatStaticSensorCoordinator,
    MeteocatUviFileCoordinator,
    MeteocatConditionCoordinator,
    MeteocatTempForecastCoordinator,
    MeteocatEntityCoordinator,
    MeteocatUviCoordinator,
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class MeteocatSensorEntityDescription(SensorEntityDescription):
    """A class that describes Meteocat sensor entities."""

SENSOR_TYPES: tuple[MeteocatSensorEntityDescription, ...] = (
    # Sensores dinámicos
    MeteocatSensorEntityDescription(
        key=WIND_SPEED,
        translation_key="wind_speed",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    MeteocatSensorEntityDescription(
        key=WIND_DIRECTION,
        translation_key="wind_direction",
        icon="mdi:compass",
        device_class=None,
    ),
    MeteocatSensorEntityDescription(
        key=TEMPERATURE,
        translation_key="temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=HUMIDITY,
        translation_key="humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    MeteocatSensorEntityDescription(
        key=PRESSURE,
        translation_key="pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
    ),
    MeteocatSensorEntityDescription(
        key=PRECIPITATION,
        translation_key="precipitation",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    ),
    MeteocatSensorEntityDescription(
        key=PRECIPITATION_ACCUMULATED,
        translation_key="precipitation_accumulated",
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mm",
    ),
    MeteocatSensorEntityDescription(
        key=SOLAR_GLOBAL_IRRADIANCE,
        translation_key="solar_global_irradiance",
        icon="mdi:weather-sunny",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement = UnitOfIrradiance.WATTS_PER_SQUARE_METER,
    ),
    MeteocatSensorEntityDescription(
        key=UV_INDEX,
        translation_key="uv_index",
        icon="mdi:weather-sunny-alert",
    ),
    MeteocatSensorEntityDescription(
        key=MAX_TEMPERATURE,
        translation_key="max_temperature",
        icon="mdi:thermometer-plus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=MIN_TEMPERATURE,
        translation_key="min_temperature",
        icon="mdi:thermometer-minus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=FEELS_LIKE,
        translation_key="feels_like",
        icon="mdi:sun-thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=WIND_GUST,
        translation_key="wind_gust",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    # Sensores estáticos
    MeteocatSensorEntityDescription(
        key=TOWN_NAME,
        translation_key="town_name",
        icon="mdi:home-city",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=TOWN_ID,
        translation_key="town_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=STATION_NAME,
        translation_key="station_name",
        icon="mdi:broadcast",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=STATION_ID,
        translation_key="station_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=STATION_TIMESTAMP,
        translation_key="station_timestamp",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    MeteocatSensorEntityDescription(
        key=CONDITION,
        translation_key="condition",
        icon="mdi:weather-partly-cloudy",
    ),
     MeteocatSensorEntityDescription(
        key=MAX_TEMPERATURE_FORECAST,
        translation_key="max_temperature_forecast",
        icon="mdi:thermometer-plus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=MIN_TEMPERATURE_FORECAST,
        translation_key="min_temperature_forecast",
        icon="mdi:thermometer-minus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=HOURLY_FORECAST_FILE_STATUS,
        translation_key="hourly_forecast_file_status",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=DAILY_FORECAST_FILE_STATUS,
        translation_key="daily_forecast_file_status",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=UVI_FILE_STATUS,
        translation_key="uvi_file_status",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
)

@callback
async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Meteocat sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]

    # Coordinadores para sensores
    sensor_coordinator = entry_data.get("sensor_coordinator")
    uvi_file_coordinator = entry_data.get("uvi_file_coordinator")
    static_sensor_coordinator = entry_data.get("static_sensor_coordinator")
    condition_coordinator = entry_data.get("condition_coordinator")
    temp_forecast_coordinator = entry_data.get("temp_forecast_coordinator")
    entity_coordinator = entry_data.get("entity_coordinator")
    uvi_coordinator = entry_data.get("uvi_coordinator")

    # Sensores generales
    async_add_entities(
        MeteocatSensor(sensor_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {WIND_SPEED, WIND_DIRECTION, TEMPERATURE, HUMIDITY, PRESSURE, PRECIPITATION, PRECIPITATION_ACCUMULATED, SOLAR_GLOBAL_IRRADIANCE, MAX_TEMPERATURE, MIN_TEMPERATURE, FEELS_LIKE, WIND_GUST, STATION_TIMESTAMP}  # Incluir sensores generales en el coordinador SENSOR COORDINATOR
    )

    # Sensores estáticos
    async_add_entities(
        MeteocatStaticSensor(static_sensor_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {TOWN_NAME, TOWN_ID, STATION_NAME, STATION_ID}
    )

    # Sensor UVI
    async_add_entities(
        MeteocatUviSensor(uvi_file_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == UV_INDEX  # Incluir UVI en el coordinador UVI FILE COORDINATOR
    )

    # Sensor CONDITION para estado del cielo
    async_add_entities(
        MeteocatConditionSensor(condition_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == CONDITION  # Incluir CONDITION en el coordinador CONDITION COORDINATOR
    )

    # Sensores temperatura previsión
    async_add_entities(
        MeteocatTempForecast(temp_forecast_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {MAX_TEMPERATURE_FORECAST, MIN_TEMPERATURE_FORECAST}
    )

    # Sensores de estado de los archivos de previsión horaria
    async_add_entities(
        MeteocatHourlyForecastStatusSensor(entity_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == HOURLY_FORECAST_FILE_STATUS
    )

    # Sensores de estado de los archivos de previsión diaria
    async_add_entities(
        MeteocatDailyForecastStatusSensor(entity_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == DAILY_FORECAST_FILE_STATUS
    )

    # Sensores de estado de los archivos de uvi
    async_add_entities(
        MeteocatUviStatusSensor(uvi_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == UVI_FILE_STATUS
    )

# Cambiar UTC a la zona horaria local
def convert_to_local_time(utc_time: str, local_tz: str = "Europe/Madrid") -> datetime:
    try:
        # Convertir la cadena UTC a un objeto datetime
        utc_dt = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
        
        # Convertir a la zona horaria local usando ZoneInfo
        local_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(local_tz))
        
        return local_dt
    except ValueError:
        return None

class MeteocatStaticSensor(CoordinatorEntity[MeteocatStaticSensorCoordinator], SensorEntity):
    """Representation of a static Meteocat sensor."""
    STATIC_KEYS = {TOWN_NAME, TOWN_ID, STATION_NAME, STATION_ID}
    
    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, static_sensor_coordinator, description, entry_data):
        """Initialize the static sensor."""
        super().__init__(static_sensor_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_name = entry_data["station_name"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._station_id}_{self.entity_description.key}"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)
        
        # Log para depuración
        _LOGGER.debug(
            "Inicializando sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Información estática
        if self.entity_description.key in self.STATIC_KEYS:
            # Información estática del `entry_data`
            if self.entity_description.key == TOWN_NAME:
                return self._town_name
            if self.entity_description.key == TOWN_ID:
                return self._town_id
            if self.entity_description.key == STATION_NAME:
                return self._station_name
            if self.entity_description.key == STATION_ID:
                return self._station_id
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatUviSensor(CoordinatorEntity[MeteocatUviFileCoordinator], SensorEntity):
    """Representation of a Meteocat UV Index sensor."""

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, uvi_file_coordinator, description, entry_data):
        """Initialize the UV Index sensor."""
        super().__init__(uvi_file_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_{self.entity_description.key}"

        # Asigna entity_category desde description (si está definido)
        self._attr_entity_category = getattr(description, "entity_category", None)
        
        # Log para depuración
        _LOGGER.debug(
            "Inicializando sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )

    @property
    def native_value(self):
        """Return the current UV index value."""
        if self.entity_description.key == UV_INDEX:
            uvi_data = self.coordinator.data or {}
            return uvi_data.get("uvi", None)
    
    @property
    def extra_state_attributes(self):
        """Return additional attributes for the sensor."""
        attributes = super().extra_state_attributes or {}
        if self.entity_description.key == UV_INDEX:
            uvi_data = self.coordinator.data or {}
            # Add the "hour" attribute if it exists
            attributes["hour"] = uvi_data.get("hour")
        return attributes
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatConditionSensor(CoordinatorEntity[MeteocatConditionCoordinator], SensorEntity):
    """Representation of a Meteocat UV Index sensor."""

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, condition_coordinator, description, entry_data):
        """Initialize the UV Index sensor."""
        super().__init__(condition_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_{self.entity_description.key}"

        # Asigna entity_category desde description (si está definido)
        self._attr_entity_category = getattr(description, "entity_category", None)
        
        # Log para depuración
        _LOGGER.debug(
            "Inicializando sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )

    @property
    def native_value(self):
        """Return the current UV index value."""
        if self.entity_description.key == CONDITION:
            condition_data = self.coordinator.data or {}
            return condition_data.get("condition", None)
    
    @property
    def extra_state_attributes(self):
        """Return additional attributes for the sensor."""
        attributes = super().extra_state_attributes or {}
        if self.entity_description.key == CONDITION:
            condition_data = self.coordinator.data or {}
            # Add the "hour" attribute if it exists
            attributes["hour"] = condition_data.get("hour", None)
        return attributes
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatSensor(CoordinatorEntity[MeteocatSensorCoordinator], SensorEntity):
    """Representation of a Meteocat sensor."""

    CODE_MAPPING = {
        WIND_SPEED: WIND_SPEED_CODE,
        WIND_DIRECTION: WIND_DIRECTION_CODE,
        TEMPERATURE: TEMPERATURE_CODE,
        HUMIDITY: HUMIDITY_CODE,
        PRESSURE: PRESSURE_CODE,
        PRECIPITATION: PRECIPITATION_CODE,
        SOLAR_GLOBAL_IRRADIANCE: SOLAR_GLOBAL_IRRADIANCE_CODE,
        # UV_INDEX: UV_INDEX_CODE,
        MAX_TEMPERATURE: MAX_TEMPERATURE_CODE,
        MIN_TEMPERATURE: MIN_TEMPERATURE_CODE,
        WIND_GUST: WIND_GUST_CODE,
    }

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, sensor_coordinator, description, entry_data):
        """Initialize the sensor."""
        super().__init__(sensor_coordinator)
        self.entity_description = description
        self.api_key = entry_data["api_key"]
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_name = entry_data["station_name"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._station_id}_{self.entity_description.key}"

        # Asigna entity_category desde description (si está definido)
        self._attr_entity_category = getattr(description, "entity_category", None)

        # Log para depuración
        _LOGGER.debug(
            "Inicializando sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Información dinámica
        if self.entity_description.key == FEELS_LIKE:
            stations = self.coordinator.data or []

            # Variables necesarias
            temperature = None
            humidity = None
            wind_speed = None

            # Obtener valores de las variables
            for station in stations:
                variables = station.get("variables", [])
                for var in variables:
                    code = var.get("codi")
                    lectures = var.get("lectures", [])
                    if not lectures:
                        continue
                    latest_reading = lectures[-1].get("valor")
                    
                    if code == TEMPERATURE_CODE:
                        temperature = float(latest_reading)
                    elif code == HUMIDITY_CODE:
                        humidity = float(latest_reading)
                    elif code == WIND_SPEED_CODE:
                        wind_speed = float(latest_reading)
            
            # Verificar que todas las variables necesarias están presentes
            if temperature is not None and humidity is not None and wind_speed is not None:
                # Cálculo del windchill
                windchill = (
                    13.1267 +
                    0.6215 * temperature -
                    11.37 * (wind_speed ** 0.16) +
                    0.3965 * temperature * (wind_speed ** 0.16)
                )
                
                # Cálculo del heat_index
                heat_index = (
                    -8.78469476 +
                    1.61139411 * temperature +
                    2.338548839 * humidity -
                    0.14611605 * temperature * humidity -
                    0.012308094 * (temperature ** 2) -
                    0.016424828 * (humidity ** 2) +
                    0.002211732 * (temperature ** 2) * humidity +
                    0.00072546 * temperature * (humidity ** 2) -
                    0.000003582 * (temperature ** 2) * (humidity ** 2)
                )
                
                # Lógica de selección
                if -50 <= temperature <= 10 and wind_speed > 4.8:
                    _LOGGER.debug(f"Sensación térmica por frío, calculada según la fórmula de Wind Chill: {windchill} ºC")
                    return round(windchill, 1)
                elif temperature > 26 and humidity > 40:
                    _LOGGER.debug(f"Sensación térmica por calor, calculada según la fórmula de Heat Index: {heat_index} ºC")
                    return round(heat_index, 1)
                else:
                    _LOGGER.debug(f"Sensación térmica idéntica a la temperatura actual: {temperature} ºC")
                    return round(temperature, 1)

        sensor_code = self.CODE_MAPPING.get(self.entity_description.key)

        if sensor_code is not None:
            # Accedemos a las estaciones en el JSON recibido
            stations = self.coordinator.data or []
            for station in stations:
                variables = station.get("variables", [])

                # Filtramos por código
                variable_data = next(
                    (var for var in variables if var.get("codi") == sensor_code),
                    None,
                )

                if variable_data:
                    # Obtenemos la última lectura
                    lectures = variable_data.get("lectures", [])
                    if lectures:
                        latest_reading = lectures[-1]
                        value = latest_reading.get("valor")

                        # Convertimos grados a dirección cardinal para WIND_DIRECTION
                        if self.entity_description.key == WIND_DIRECTION and isinstance(value, (int, float)):
                            return self._convert_degrees_to_cardinal(value)

                        return value
                    
        # Lógica específica para el sensor de timestamp
        if self.entity_description.key == STATION_TIMESTAMP:
            stations = self.coordinator.data or []
            for station in stations:
                variables = station.get("variables", [])
                for variable in variables:
                    lectures = variable.get("lectures", [])
                    if lectures:
                        # Obtenemos el campo `data` de la última lectura
                        latest_reading = lectures[-1]
                        raw_timestamp = latest_reading.get("data")

                        if raw_timestamp:
                            # Convertir el timestamp a un objeto datetime
                            try:
                                # Convertimos raw_timestamp a hora local
                                local_time = convert_to_local_time(raw_timestamp)
                                _LOGGER.debug("Hora UTC: %s convertida a hora local: %s", raw_timestamp, local_time)
                                return local_time
                            except ValueError:
                                # Manejo de errores si el formato no es válido
                                _LOGGER.error(f"Error al convertir el timestamp '{raw_timestamp}' a hora local.")
                                return None

        # Nuevo sensor para la precipitación acumulada
        if self.entity_description.key == PRECIPITATION_ACCUMULATED:
            stations = self.coordinator.data or []
            total_precipitation = 0.0  # Usa float para permitir acumulación de decimales

            for station in stations:
                variables = station.get("variables", [])

                # Filtramos por código de precipitación
                variable_data = next(
                    (var for var in variables if var.get("codi") == PRECIPITATION_CODE),
                    None,
                )

                if variable_data:
                    # Sumamos las lecturas de precipitación
                    lectures = variable_data.get("lectures", [])
                    for lecture in lectures:
                        total_precipitation += float(lecture.get("valor", 0.0))  # Convertimos a float

            _LOGGER.debug(f"Total precipitación acumulada: {total_precipitation} mm")
            return total_precipitation
        
        return None
        
    @staticmethod
    def _convert_degrees_to_cardinal(degree: float) -> str:
        """Convert degrees to cardinal direction."""
        if not isinstance(degree, (int, float)):
            return "Unknown"  # Retorna "Unknown" si el valor no es un número válido

        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N",
        ]
        index = round(degree / 22.5) % 16
        return directions[index]
    
    @property
    def extra_state_attributes(self):
        """Return additional attributes of the sensor."""
        attributes = super().extra_state_attributes or {}

        # Agregar grados como atributo solo para WIND_DIRECTION
        if self.entity_description.key == WIND_DIRECTION:
            # Obtener el código del sensor desde CODE_MAPPING
            sensor_code = self.CODE_MAPPING.get(self.entity_description.key)

            if sensor_code is not None:
                # Acceder a los datos de la estación desde el coordinator
                stations = self.coordinator.data or []
                degrees_value = None

                for station in stations:
                    variables = station.get("variables", [])
                    # Buscar la variable correspondiente al código
                    variable_data = next(
                        (var for var in variables if var.get("codi") == sensor_code),
                        None,
                    )
                    if variable_data:
                        # Obtener la última lectura de grados
                        lectures = variable_data.get("lectures", [])
                        if lectures:
                            degrees_value = lectures[-1].get("valor")
                            break

                # Asignar el valor al atributo
                if degrees_value is not None:
                    attributes["degrees"] = degrees_value

        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatTempForecast(CoordinatorEntity[MeteocatTempForecastCoordinator], SensorEntity):
    """Representation of a Meteocat UV Index sensor."""

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, temp_forecast_coordinator, description, entry_data):
        """Initialize the UV Index sensor."""
        super().__init__(temp_forecast_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_{self.entity_description.key}"

        # Asigna entity_category desde description (si está definido)
        self._attr_entity_category = getattr(description, "entity_category", None)
        
        # Log para depuración
        _LOGGER.debug(
            "Inicializando sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )

    @property
    def native_value(self):
        """Return the Max and Min Temp Forecast value."""
        temp_forecast_data = self.coordinator.data or {}
        
        if self.entity_description.key == MAX_TEMPERATURE_FORECAST:
            return temp_forecast_data.get("max_temp_forecast", None)
        if self.entity_description.key == MIN_TEMPERATURE_FORECAST:
            return temp_forecast_data.get("min_temp_forecast", None)
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatHourlyForecastStatusSensor(CoordinatorEntity[MeteocatEntityCoordinator], SensorEntity):

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, entity_coordinator, description, entry_data):
        super().__init__(entity_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._station_id}_hourly_status"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _get_first_date(self):
        hourly_data = self.coordinator.data.get("hourly")
        if hourly_data and "dies" in hourly_data:
            return datetime.fromisoformat(hourly_data["dies"][0]["data"].rstrip("Z")).date()
        return None

    @property
    def native_value(self):
        first_date = self._get_first_date()
        if first_date:
            today = datetime.now(timezone.utc).date()
            current_time = datetime.now(timezone.utc).time()
            days_difference = (today - first_date).days
            _LOGGER.debug(
                f"Diferencia de días para predicciones horarias: {days_difference}."
                f"Hora actual de validación: {current_time}."
                f"Para la validación: "
                f"número de días= {DEFAULT_VALIDITY_DAYS}, "
                f"hora de contacto a la API >= {DEFAULT_VALIDITY_HOURS}, "
                f"minutos de contacto a la API >= {DEFAULT_VALIDITY_MINUTES}."
            )
            
            # Validar fecha y hora según la lógica del coordinador
            if days_difference > DEFAULT_VALIDITY_DAYS and current_time >= time(DEFAULT_VALIDITY_HOURS, DEFAULT_VALIDITY_MINUTES):
                return "obsolete"
            return "updated"
        return "unknown"

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes or {}
        first_date = self._get_first_date()
        if first_date:
            attributes["update_date"] = first_date.isoformat()
        return attributes
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatDailyForecastStatusSensor(CoordinatorEntity[MeteocatEntityCoordinator], SensorEntity):

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, entity_coordinator, description, entry_data):
        super().__init__(entity_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._station_id}_daily_status"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _get_first_date(self):
        daily_data = self.coordinator.data.get("daily")
        if daily_data and "dies" in daily_data:
            return datetime.fromisoformat(daily_data["dies"][0]["data"].rstrip("Z")).date()
        return None

    @property
    def native_value(self):
        first_date = self._get_first_date()
        if first_date:
            today = datetime.now(timezone.utc).date()
            current_time = datetime.now(timezone.utc).time()
            days_difference = (today - first_date).days
            _LOGGER.debug(
                f"Diferencia de días para predicciones diarias: {days_difference}."
                f"Hora actual de validación: {current_time}."
                f"Para la validación: "
                f"número de días= {DEFAULT_VALIDITY_DAYS}, "
                f"hora de contacto a la API >= {DEFAULT_VALIDITY_HOURS}, "
                f"minutos de contacto a la API >= {DEFAULT_VALIDITY_MINUTES}."
            )

            # Validar fecha y hora según la lógica del coordinador
            if days_difference > DEFAULT_VALIDITY_DAYS and current_time >= time(DEFAULT_VALIDITY_HOURS, DEFAULT_VALIDITY_MINUTES):
                return "obsolete"
            return "updated"
        return "unknown"

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes or {}
        first_date = self._get_first_date()
        if first_date:
            attributes["update_date"] = first_date.isoformat()
        return attributes
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatUviStatusSensor(CoordinatorEntity[MeteocatUviCoordinator], SensorEntity):

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, uvi_coordinator, description, entry_data):
        super().__init__(uvi_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._station_id}_uvi_status"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _get_first_date(self):
        if self.coordinator.data:
            return datetime.strptime(self.coordinator.data[0].get("date"), "%Y-%m-%d").date()
        return None

    @property
    def native_value(self):
        first_date = self._get_first_date()
        if first_date:
            today = datetime.now(timezone.utc).date()
            current_time = datetime.now(timezone.utc).time()
            days_difference = (today - first_date).days
            _LOGGER.debug(
                f"Diferencia de días para datos UVI: {days_difference}."
                f"Hora actual de validación: {current_time}."
                f"Para la validación: "
                f"número de días= {DEFAULT_VALIDITY_DAYS}, "
                f"hora de contacto a la API >= {DEFAULT_VALIDITY_HOURS}, "
                f"minutos de contacto a la API >= {DEFAULT_VALIDITY_MINUTES}."
            )

            # Validar fecha y hora según la lógica del coordinador
            if days_difference > DEFAULT_VALIDITY_DAYS and current_time >= time(DEFAULT_VALIDITY_HOURS, DEFAULT_VALIDITY_MINUTES):
                return "obsolete"
            return "updated"
        return "unknown"

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes or {}
        first_date = self._get_first_date()
        if first_date:
            attributes["update_date"] = first_date.isoformat()
        return attributes
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )