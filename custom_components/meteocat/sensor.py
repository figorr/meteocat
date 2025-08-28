from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo
import os
import json
import aiofiles
import asyncio 
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfPrecipitationDepth,
    UnitOfVolumetricFlux,
    UnitOfIrradiance,
)

from .const import (
    DOMAIN,
    TOWN_NAME,
    TOWN_ID,
    STATION_NAME,
    STATION_ID,
    REGION_NAME,
    REGION_ID,
    WIND_SPEED,
    WIND_DIRECTION,
    WIND_DIRECTION_CARDINAL,
    TEMPERATURE,
    HUMIDITY,
    PRESSURE,
    PRECIPITATION,
    PRECIPITATION_ACCUMULATED,
    PRECIPITATION_PROBABILITY,
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
    QUOTA_FILE_STATUS,
    QUOTA_XDDE,
    QUOTA_PREDICCIO,
    QUOTA_BASIC,
    QUOTA_XEMA,
    QUOTA_QUERIES,
    ALERTS,
    ALERT_FILE_STATUS,
    ALERT_WIND,
	ALERT_RAIN_INTENSITY,
	ALERT_RAIN,
	ALERT_SEA,
	ALERT_COLD,
	ALERT_WARM,
	ALERT_WARM_NIGHT,
	ALERT_SNOW,
    LIGHTNING_FILE_STATUS,
    LIGHTNING_REGION,
    LIGHTNING_TOWN,
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
    DEFAULT_ALERT_VALIDITY_TIME,
    DEFAULT_QUOTES_VALIDITY_TIME,
    ALERT_VALIDITY_MULTIPLIER_100,
    ALERT_VALIDITY_MULTIPLIER_200,
    ALERT_VALIDITY_MULTIPLIER_500,
    ALERT_VALIDITY_MULTIPLIER_DEFAULT,
    DEFAULT_LIGHTNING_VALIDITY_TIME,
    DEFAULT_LIGHTNING_VALIDITY_HOURS,
    DEFAULT_LIGHTNING_VALIDITY_MINUTES,
)

from .coordinator import (
    MeteocatSensorCoordinator,
    MeteocatStaticSensorCoordinator,
    MeteocatUviFileCoordinator,
    MeteocatConditionCoordinator,
    MeteocatTempForecastCoordinator,
    MeteocatEntityCoordinator,
    DailyForecastCoordinator,
    MeteocatUviCoordinator,
    MeteocatAlertsCoordinator,
    MeteocatAlertsRegionCoordinator,
    MeteocatQuotesCoordinator,
    MeteocatQuotesFileCoordinator,
    MeteocatLightningCoordinator,
    MeteocatLightningFileCoordinator,
)

# Definir la zona horaria local
TIMEZONE = ZoneInfo("Europe/Madrid")

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
        key=WIND_DIRECTION_CARDINAL,
        translation_key="wind_direction_cardinal",
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
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mm",
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
        key=PRECIPITATION_PROBABILITY,
        translation_key="precipitation_probability",
        icon="mdi:weather-rainy",
        device_class=None,
        native_unit_of_measurement=PERCENTAGE,
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
    MeteocatSensorEntityDescription(
        key=LIGHTNING_REGION,
        translation_key="lightning_region",
        icon="mdi:weather-lightning",
    ),
    MeteocatSensorEntityDescription(
        key=LIGHTNING_TOWN,
        translation_key="lightning_town",
        icon="mdi:weather-lightning",
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
        key=REGION_NAME,
        translation_key="region_name",
        icon="mdi:broadcast",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=REGION_ID,
        translation_key="region_id",
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
    ),
    MeteocatSensorEntityDescription(
        key=QUOTA_FILE_STATUS,
        translation_key="quota_file_status",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=LIGHTNING_FILE_STATUS,
        translation_key="lightning_file_status",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=ALERTS,
        translation_key="alerts",
        icon="mdi:alert-outline",
    ),
    MeteocatSensorEntityDescription(
        key=ALERT_FILE_STATUS,
        translation_key="alert_file_status",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=ALERT_WIND,
        translation_key="alert_wind",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_RAIN_INTENSITY,
        translation_key="alert_rain_intensity",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_RAIN,
        translation_key="alert_rain",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_SEA,
        translation_key="alert_sea",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_COLD,
        translation_key="alert_cold",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_WARM,
        translation_key="alert_warm",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_WARM_NIGHT,
        translation_key="alert_warm_night",
        icon="mdi:alert-outline",
    ),
	MeteocatSensorEntityDescription(
        key=ALERT_SNOW,
        translation_key="alert_snow",
        icon="mdi:alert-outline",
    ),
    MeteocatSensorEntityDescription(
        key=QUOTA_XDDE,
        translation_key="quota_xdde",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=QUOTA_PREDICCIO,
        translation_key="quota_prediccio",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=QUOTA_BASIC,
        translation_key="quota_basic",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=QUOTA_XEMA,
        translation_key="quota_xema",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=QUOTA_QUERIES,
        translation_key="quota_queries",
        icon="mdi:counter",
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
    daily_forecast_coordinator = entry_data.get("daily_forecast_coordinator")
    temp_forecast_coordinator = entry_data.get("temp_forecast_coordinator")
    entity_coordinator = entry_data.get("entity_coordinator")
    uvi_coordinator = entry_data.get("uvi_coordinator")
    alerts_coordinator = entry_data.get("alerts_coordinator")
    alerts_region_coordinator = entry_data.get("alerts_region_coordinator")
    quotes_coordinator = entry_data.get("quotes_coordinator")
    quotes_file_coordinator = entry_data.get("quotes_file_coordinator")
    lightning_coordinator = entry_data.get("lightning_coordinator")
    lightning_file_coordinator = entry_data.get("lightning_file_coordinator")

    # Sensores generales
    async_add_entities(
        MeteocatSensor(sensor_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {WIND_SPEED, WIND_DIRECTION, WIND_DIRECTION_CARDINAL, TEMPERATURE, HUMIDITY, PRESSURE, PRECIPITATION, PRECIPITATION_ACCUMULATED, SOLAR_GLOBAL_IRRADIANCE, MAX_TEMPERATURE, MIN_TEMPERATURE, FEELS_LIKE, WIND_GUST, STATION_TIMESTAMP}  # Incluir sensores generales en el coordinador SENSOR COORDINATOR
    )

    # Sensores estáticos
    async_add_entities(
        MeteocatStaticSensor(static_sensor_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {TOWN_NAME, TOWN_ID, STATION_NAME, STATION_ID, REGION_NAME, REGION_ID}
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

    # Sensor precipitación probabilidad
    async_add_entities(
        MeteocatPrecipitationProbabilitySensor(daily_forecast_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == PRECIPITATION_PROBABILITY
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

    # Sensores de alertas
    async_add_entities(
        MeteocatAlertStatusSensor(alerts_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == ALERT_FILE_STATUS
    )

    # Sensores de alertas para la comarca
    async_add_entities(
        MeteocatAlertRegionSensor(alerts_region_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == ALERTS
    )

    # Sensores de alertas para cada meteor
    async_add_entities(
        MeteocatAlertMeteorSensor(alerts_region_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {ALERT_WIND, ALERT_RAIN_INTENSITY, ALERT_RAIN, ALERT_SEA, ALERT_COLD, ALERT_WARM, ALERT_WARM_NIGHT, ALERT_SNOW}
    )

    # Sensores de estado de cuotas
    async_add_entities(
        MeteocatQuotaStatusSensor(quotes_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == QUOTA_FILE_STATUS
    )

    # Sensores cuotas
    async_add_entities(
        MeteocatQuotaSensor(quotes_file_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {QUOTA_XDDE, QUOTA_PREDICCIO, QUOTA_BASIC, QUOTA_XEMA, QUOTA_QUERIES}
    )

    # Sensores de estado de rayos
    async_add_entities(
        MeteocatLightningStatusSensor(lightning_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key == LIGHTNING_FILE_STATUS
    )

    # Sensores de rayos en comarca y municipio
    async_add_entities(
        MeteocatLightningSensor(lightning_file_coordinator, description, entry_data)
        for description in SENSOR_TYPES
        if description.key in {LIGHTNING_REGION, LIGHTNING_TOWN}
    )

# Cambiar UTC a la zona horaria local
def convert_to_local_time(utc_time: str, local_tz: str = "Europe/Madrid") -> datetime | None:
    """
    Convierte una fecha/hora UTC en formato ISO 8601 a la zona horaria local especificada.

    Args:
        utc_time (str): Fecha/hora en formato ISO 8601 (ejemplo: '2025-01-02T12:00:00Z').
        local_tz (str): Zona horaria local en formato IANA (por defecto, 'Europe/Madrid').

    Returns:
        datetime | None: Objeto datetime convertido a la zona horaria local, o None si hay un error.
    """
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
    STATIC_KEYS = {TOWN_NAME, TOWN_ID, STATION_NAME, STATION_ID, REGION_NAME, REGION_ID}
    
    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, static_sensor_coordinator, description, entry_data):
        """Initialize the static sensor."""
        super().__init__(static_sensor_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_name = entry_data["station_name"]
        self._station_id = entry_data["station_id"]
        self._region_name = entry_data["region_name"]
        self._region_id = entry_data["region_id"]

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
            if self.entity_description.key == REGION_NAME:
                return self._region_name
            if self.entity_description.key == REGION_ID:
                return self._region_id
    
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

                        return value
                    
        # Para el sensor WIND_DIRECTION_CARDINAL, convertir grados a dirección cardinal
        if self.entity_description.key == WIND_DIRECTION_CARDINAL:
            stations = self.coordinator.data or []
            for station in stations:
                variables = station.get("variables", [])

                # Filtramos por código
                variable_data = next(
                    (var for var in variables if var.get("codi") == WIND_DIRECTION_CODE),
                    None,
                )

                if variable_data:
                    # Obtenemos la última lectura
                    lectures = variable_data.get("lectures", [])
                    if lectures:
                        latest_reading = lectures[-1]
                        value = latest_reading.get("valor")

                        return self._convert_degrees_to_cardinal(value)
                    
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
        "north", "north_northeast", "northeast", "east_northeast", "east", "east_southeast", "southeast", "south_southeast",
        "south", "south_southwest", "southwest", "west_southwest", "west", "west_northwest", "northwest", "north_northwest"
        ]
        index = round(degree / 22.5) % 16
        return directions[index]

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
    """Representation of a Meteocat Min and Max Temperature sensors."""

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, temp_forecast_coordinator, description, entry_data):
        """Initialize the Mina and Max Temperature sensors."""
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

class MeteocatPrecipitationProbabilitySensor(CoordinatorEntity[DailyForecastCoordinator], SensorEntity):
    """Representation of a Meteocat precipitation probability sensor."""

    _attr_has_entity_name = True  # Enable device-based naming

    def __init__(self, daily_forecast_coordinator, description, entry_data):
        super().__init__(daily_forecast_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_{self.entity_description.key}"
        self._attr_entity_category = getattr(description, "entity_category", None)
        
        _LOGGER.debug(
            "Initializing sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )

    @property
    def native_value(self):
        """Retorna la probabilidad de precipitación del día actual."""
        forecast = self.coordinator.get_forecast_for_today()
        if forecast:
            precipitation = forecast.get("variables", {}).get("precipitacio", {}).get("valor", None)
            if precipitation is not None and float(precipitation) >= 0:
                return float(precipitation)
        return None

    @property
    def device_info(self) -> DeviceInfo:
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

class MeteocatAlertStatusSensor(CoordinatorEntity[MeteocatAlertsCoordinator], SensorEntity):
    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, alerts_coordinator, description, entry_data):
        super().__init__(alerts_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]
        self._region_id = entry_data["region_id"]
        self._limit_prediccio = entry_data["limit_prediccio"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._region_id}_alert_status"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _get_data_update(self):
        """Obtiene la fecha de actualización directamente desde el coordinador."""
        data_update = self.coordinator.data.get("actualizado")
        if data_update:
            try:
                return datetime.fromisoformat(data_update.rstrip("Z"))
            except ValueError:
                _LOGGER.error("Formato de fecha de actualización inválido: %s", data_update)
        return None
    
    def _get_validity_duration(self):
        """Calcula la duración de validez basada en el límite de predicción."""
        if self._limit_prediccio <= 100:
            multiplier = ALERT_VALIDITY_MULTIPLIER_100
        elif 100 < self._limit_prediccio <= 200:
            multiplier = ALERT_VALIDITY_MULTIPLIER_200
        elif 200 < self._limit_prediccio <= 500:
            multiplier = ALERT_VALIDITY_MULTIPLIER_500
        else:
            multiplier = ALERT_VALIDITY_MULTIPLIER_DEFAULT

        return timedelta(minutes=DEFAULT_ALERT_VALIDITY_TIME * multiplier)

    @property
    def native_value(self):
        """Devuelve el estado actual de las alertas basado en la fecha de actualización."""
        data_update = self._get_data_update()
        if not data_update:
            return "unknown"

        current_time = datetime.now(ZoneInfo("UTC"))
        validity_duration = self._get_validity_duration()

        # Comprobar si el archivo de alertas está obsoleto
        if current_time - data_update >= validity_duration:
            return "obsolete"
        return "updated"

    @property
    def extra_state_attributes(self):
        """Devuelve los atributos adicionales del estado."""
        attributes = super().extra_state_attributes or {}
        data_update = self._get_data_update()
        if data_update:
            attributes["update_date"] = data_update.isoformat()
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Devuelve la información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=f"Meteocat {self._station_id} {self._town_name}",
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatAlertRegionSensor(CoordinatorEntity[MeteocatAlertsRegionCoordinator], SensorEntity):
    """Sensor dinámico que muestra el estado de las alertas por región."""

    METEOR_MAPPING = {
        "Temps violent": "violent_weather",
        "Intensitat de pluja": "rain_intensity",
        "Acumulació de pluja": "rain_amount",
        "Neu acumulada en 24 hores": "snow_amount_24",
        "Vent": "wind",
        "Estat de la mar": "sea_state",
        "Fred": "cold",
        "Calor": "heat",
        "Calor nocturna": "night_heat",
    }

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, alerts_region_coordinator, description, entry_data):
        super().__init__(alerts_region_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]
        self._region_id = entry_data["region_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._region_id}_alerts"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _map_meteor_case_insensitive(self, meteor: str) -> str:
        """Busca el meteor en el mapping sin importar mayúsculas/minúsculas."""
        for key, value in self.METEOR_MAPPING.items():
            if key.lower() == meteor.lower():
                return value
        return "unknown"

    @property
    def native_value(self):
        """Devuelve el número de alertas activas."""
        return self.coordinator.data.get("activas", 0)

    @property
    def extra_state_attributes(self):
        """Devuelve los atributos extra del sensor con los nombres traducidos."""
        meteor_details = self.coordinator.data.get("detalles", {}).get("meteor", {})
        
        # Convertimos las claves al formato deseado usando el mapping
        attributes = {}
        for i, meteor in enumerate(meteor_details.keys()):
            mapped_name = self._map_meteor_case_insensitive(meteor)
            if not mapped_name:
                _LOGGER.warning("Meteor desconocido sin mapeo: %s", meteor)
                mapped_name = "unknown"
            attributes[f"alert_{i+1}"] = mapped_name

        _LOGGER.info("Atributos traducidos del sensor: %s", attributes)
        return attributes
    
    @property
    def device_info(self) -> DeviceInfo:
        """Devuelve la información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatAlertMeteorSensor(CoordinatorEntity[MeteocatAlertsRegionCoordinator], SensorEntity):
    """Sensor dinámico que muestra el estado de las alertas por cada meteor para una región."""
    METEOR_MAPPING = {
        ALERT_WIND: "Vent",
        ALERT_RAIN_INTENSITY: "Intensitat de pluja",
        ALERT_RAIN: "Acumulació de pluja",
        ALERT_SEA: "Estat de la mar",
        ALERT_COLD: "Fred",
        ALERT_WARM: "Calor",
        ALERT_WARM_NIGHT: "Calor nocturna",
        ALERT_SNOW: "Neu acumulada en 24 hores",
    }

    STATE_MAPPING = {
        "Obert": "opened",
        "Tancat": "closed",
    }

    UMBRAL_MAPPING = {
        "Ratxes de vent > 25 m/s": "wind_gusts_25",
        "Esclafits": "microburst",
        "Tornados o mànegues": "tornadoes",
        "Ratxa màxima > 40m/s": "wind_40",
        "Ratxa màxima > 35m/s": "wind_35",
        "Ratxa màxima > 30m/s": "wind_30",
        "Ratxa màxima > 25m/s": "wind_25",
        "Ratxa màxima > 20m/s": "wind_20",
        "Pedra de diàmetre > 2 cm": "hail_2_cm",
        "Intensitat > 40 mm / 30 minuts": "intensity_40_30",
        "Intensitat > 20 mm / 30 minuts": "intensity_20_30",
        "Acumulada > 200 mm /24 hores": "rain_200_24",
        "Acumulada > 100 mm /24 hores": "rain_100_24",
        "Onades > 4.00 metres (mar brava)": "waves_4",
        "Onades > 2.50 metres (maregassa)": "waves_2_50",
        "Fred molt intens": "cold_very_intense",
        "Fred intens": "cold_intense",
        "Calor molt intensa": "heat_very_intense",
        "Calor intensa": "heat_intense",
        "Calor nocturna molt intensa": "heat_night_very_intense",
        "Calor nocturna intensa": "heat_night_intense",
        "gruix > 50 cm a cotes superiors a 1000 metres fins a 1500 metres": "thickness_50_at_1000",
        "gruix > 30 cm a cotes superiors a 800 metres fins a 1000 metres": "thickness_30_at_800",
        "gruix > 20 cm a cotes superiors a 600 metres fins a 800 metres": "thickness_20_at_600",
        "gruix > 20 cm a cotes superiors a 1000 metres fins a 1500 metres": "thickness_20_at_1000",
        "gruix > 15 cm a cotes superiors a 300 metres fins a 600 metres": "thickness_15_at_300",
        "gruix > 10 cm a cotes superiors a 800 metres fins a 1000 metres": "thickness_10_at_800",
        "gruix > 5 cm a cotes inferiors a 300 metres": "thickness_5_at_300",
        "gruix > 5 cm a cotes superiors a 600 metres fins a 800 metres": "thickness_5_at_600",
        "gruix > 2 cm a cotes superiors a 300 metres fins a 600 metres": "thickness_2_at_300",
        "gruix ≥ 0 cm a cotes inferiors a 300 metres": "thickness_0_at_300",
    }
    
    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, alerts_region_coordinator, description, entry_data):
        super().__init__(alerts_region_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]
        self._region_id = entry_data["region_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._region_id}_{self.entity_description.key}"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)
        
        # Log para depuración
        _LOGGER.debug(
            "Inicializando sensor: %s, Unique ID: %s",
            self.entity_description.name,
            self._attr_unique_id,
        )
    
    def _get_meteor_data_case_insensitive(self, meteor_type: str) -> dict:
        """Busca en los datos de meteor de forma case-insensitive."""
        meteor_data_dict = self.coordinator.data.get("detalles", {}).get("meteor", {})
        for key, value in meteor_data_dict.items():
            if key.lower() == meteor_type.lower():
                return value
        return {}

    @property
    def native_value(self):
        """Devuelve el estado de la alerta específica."""
        meteor_type = self.METEOR_MAPPING.get(self.entity_description.key)
        if not meteor_type:
            return "Desconocido"

        meteor_data = self._get_meteor_data_case_insensitive(meteor_type)

        # Convertir estado para translation_key
        estado_original = meteor_data.get("estado", "Tancat")
        return self.STATE_MAPPING.get(estado_original, "unknown")

    @property
    def extra_state_attributes(self):
        """Devuelve los atributos específicos de la alerta."""
        meteor_type = self.METEOR_MAPPING.get(self.entity_description.key)
        if not meteor_type:
            _LOGGER.warning(
                "Tipo de meteor desconocido para sensor %s: %s",
                self.entity_description.key,
                self.coordinator.data.get("detalles", {}).get("meteor", {}).keys(),
            )
            return "unknown"

        meteor_data = self._get_meteor_data_case_insensitive(meteor_type)
        if not meteor_data:
            return {}
        
        # Convertir umbral para translation_key
        umbral_original = meteor_data.get("umbral")
        umbral_convertido = self.UMBRAL_MAPPING.get(umbral_original, "unknown")

        return {
            "inicio": meteor_data.get("inicio"),
            "fin": meteor_data.get("fin"),
            "fecha": meteor_data.get("fecha"),
            "periodo": meteor_data.get("periodo"),
            "umbral": umbral_convertido,
            "nivel": meteor_data.get("nivel"),
            "peligro": meteor_data.get("peligro"),
            "comentario": meteor_data.get("comentario"),
        }
    
    @property
    def device_info(self) -> DeviceInfo:
        """Devuelve la información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name="Meteocat " + self._station_id + " " + self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatQuotaStatusSensor(CoordinatorEntity[MeteocatQuotesCoordinator], SensorEntity):
    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, quotes_coordinator, description, entry_data):
        super().__init__(quotes_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_quota_status"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _get_data_update(self):
        """Obtiene la fecha de actualización directamente desde el coordinador."""
        data_update = self.coordinator.data.get("actualizado")
        if data_update:
            try:
                return datetime.fromisoformat(data_update.rstrip("Z"))
            except ValueError:
                _LOGGER.error("Formato de fecha de actualización inválido: %s", data_update)
        return None

    @property
    def native_value(self):
        """Devuelve el estado actual de las alertas basado en la fecha de actualización."""
        data_update = self._get_data_update()
        if not data_update:
            return "unknown"

        current_time = datetime.now(ZoneInfo("UTC"))

        # Comprobar si el archivo de alertas está obsoleto
        if current_time - data_update >= timedelta(minutes=DEFAULT_QUOTES_VALIDITY_TIME):
            return "obsolete"

        return "updated"

    @property
    def extra_state_attributes(self):
        """Devuelve los atributos adicionales del estado."""
        attributes = super().extra_state_attributes or {}
        data_update = self._get_data_update()
        if data_update:
            attributes["update_date"] = data_update.isoformat()
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Devuelve la información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=f"Meteocat {self._station_id} {self._town_name}",
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatQuotaSensor(CoordinatorEntity[MeteocatQuotesFileCoordinator], SensorEntity):
    """Representation of Meteocat Quota sensors."""

    # Mapeo de claves en sensor.py a nombres en quotes.json
    QUOTA_MAPPING = {
        "quota_xdde": "XDDE",
        "quota_prediccio": "Prediccio",
        "quota_basic": "Basic",
        "quota_xema": "XEMA",
        "quota_queries": "Quota",
    }

    # Mapeo de periodos para facilitar la traducción del estado
    PERIOD_STATE_MAPPING = {
        "Setmanal": "weekly",
        "Mensual": "monthly",
        "Anual": "annual",
    }

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, quotes_file_coordinator, description, entry_data):
        super().__init__(quotes_file_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_{self.entity_description.key}"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)
    
    def _get_plan_data(self):
        """Encuentra los datos del plan correspondiente al sensor actual."""
        if not self.coordinator.data:
            return None

        plan_name = self.QUOTA_MAPPING.get(self.entity_description.key)

        if not plan_name:
            _LOGGER.error(f"No se encontró un mapeo para la clave: {self.entity_description.key}")
            return None

        for plan in self.coordinator.data.get("plans", []):
            if plan.get("nom") == plan_name:
                return plan  # Retorna el plan encontrado

        _LOGGER.warning(f"No se encontró el plan '{plan_name}' en los datos del coordinador.")
        return None

    @property
    def native_value(self):
        """Devuelve el estado de la cuota: 'ok' si no se ha excedido, 'exceeded' si se ha superado."""
        plan = self._get_plan_data()

        if not plan:
            return None

        max_consultes = plan.get("maxConsultes")
        consultes_realitzades = plan.get("consultesRealitzades")

        if max_consultes is None or consultes_realitzades is None or \
            not isinstance(max_consultes, (int, float)) or not isinstance(consultes_realitzades, (int, float)):
                _LOGGER.warning(f"Datos inválidos para el plan '{plan.get('nom', 'unknown')}': {plan}")
                return None

        return "ok" if consultes_realitzades <= max_consultes else "exceeded"

    @property
    def extra_state_attributes(self):
        """Devuelve atributos adicionales del estado del sensor."""
        attributes = super().extra_state_attributes or {}
        plan = self._get_plan_data()

        if not plan:
            return {}
        
        # Aplicar el mapeo de periodos
        period = plan.get("periode", "desconocido")
        translated_period = self.PERIOD_STATE_MAPPING.get(period, period)  # Si no está en el mapping, dejar el original

        attributes.update({
            "period": translated_period,
            "max_queries": plan.get("maxConsultes"),
            "made_queries": plan.get("consultesRealitzades"),
            "remain_queries": plan.get("consultesRestants"),
        })

        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Devuelve la información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=f"Meteocat {self._station_id} {self._town_name}",
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatLightningStatusSensor(CoordinatorEntity[MeteocatLightningCoordinator], SensorEntity):
    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, lightning_coordinator, description, entry_data):
        super().__init__(lightning_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_lightning_status"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    def _get_data_update(self):
        """Obtiene la fecha de actualización directamente desde el coordinador y la convierte a UTC."""
        data_update = self.coordinator.data.get("actualizado")
        if data_update:
            try:
                local_time = datetime.fromisoformat(data_update)  # Ya tiene offset (+01:00 o +02:00)
                return local_time.astimezone(ZoneInfo("UTC"))  # Convertir a UTC
            except ValueError:
                _LOGGER.error("Formato de fecha de actualización inválido: %s", data_update)
        return None
    
    def _determine_status(self, now, data_update, current_time, validity_start_time, validity_duration):
        """Determina el estado basado en la fecha de actualización."""
        if now - data_update > timedelta(days=1):
            return "obsolete"
        elif now - data_update < validity_duration or current_time < validity_start_time:
            return "updated"
        return "obsolete"

    @property
    def native_value(self):
        """Devuelve el estado del archivo de rayos basado en la fecha de actualización."""
        data_update = self._get_data_update()
        if not data_update:
            return "unknown"

        now = datetime.now(timezone.utc).astimezone(TIMEZONE)
        current_time = now.time()  # Extraer solo la parte de la hora
        offset = now.utcoffset().total_seconds() / 3600  # Obtener el offset en horas

        # Determinar la hora de validez considerando el offset horario, el horario de verano (+02:00) o invierno (+01:00)
        validity_start_time = time(int(DEFAULT_LIGHTNING_VALIDITY_HOURS + offset), DEFAULT_LIGHTNING_VALIDITY_MINUTES)
        validity_duration = timedelta(minutes=DEFAULT_LIGHTNING_VALIDITY_TIME)

        return self._determine_status(now, data_update, current_time, validity_start_time, validity_duration)

    @property
    def extra_state_attributes(self):
        """Devuelve los atributos adicionales del estado."""
        attributes = super().extra_state_attributes or {}
        data_update = self._get_data_update()
        if data_update:
            attributes["update_date"] = data_update.isoformat()
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Devuelve la información del dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=f"Meteocat {self._station_id} {self._town_name}",
            manufacturer="Meteocat",
            model="Meteocat API",
        )

class MeteocatLightningSensor(CoordinatorEntity[MeteocatLightningFileCoordinator], SensorEntity):
    """Representation of Meteocat Lightning sensors."""

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, lightning_file_coordinator, description, entry_data):
        super().__init__(lightning_file_coordinator)
        self.entity_description = description
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]
        self._station_id = entry_data["station_id"]
        self._region_id = entry_data["region_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"sensor.{DOMAIN}_{self._town_id}_{self.entity_description.key}"

        # Assign entity_category if defined in the description
        self._attr_entity_category = getattr(description, "entity_category", None)

    @property
    def native_value(self):
        """Return the total number of lightning strikes."""
        if self.entity_description.key == LIGHTNING_REGION:
            return self.coordinator.data.get("region", {}).get("total", 0)
        elif self.entity_description.key == LIGHTNING_TOWN:
            return self.coordinator.data.get("town", {}).get("total", 0)
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes for the sensor."""
        attributes = super().extra_state_attributes or {}
        if self.entity_description.key == LIGHTNING_REGION:
            data = self.coordinator.data.get("region", {})
        elif self.entity_description.key == LIGHTNING_TOWN:
            data = self.coordinator.data.get("town", {})
        else:
            return attributes

        # Agregar atributos específicos
        attributes.update({
            "cloud_cloud": data.get("cc", 0),
            "cloud_ground_neg": data.get("cg-", 0),
            "cloud_ground_pos": data.get("cg+", 0),
        })
        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=f"Meteocat {self._station_id} {self._town_name}",
            manufacturer="Meteocat",
            model="Meteocat API",
        )