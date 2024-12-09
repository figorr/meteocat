from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    SOLAR_GLOBAL_IRRADIANCE,
    UV_INDEX,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    WIND_GUST,
    STATION_TIMESTAMP,
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
    WIND_GUST_CODE,
)

from .coordinator import MeteocatSensorCoordinator

_LOGGER = logging.getLogger(__name__)

@dataclass
class MeteocatSensorEntityDescription(SensorEntityDescription):
    """A class that describes Meteocat sensor entities."""

SENSOR_TYPES: tuple[MeteocatSensorEntityDescription, ...] = (
    # Sensores dinámicos
    MeteocatSensorEntityDescription(
        key=WIND_SPEED,
        name="Wind Speed",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    MeteocatSensorEntityDescription(
        key=WIND_DIRECTION,
        name="Wind Direction",
        icon="mdi:compass",
        device_class=None,
    ),
    MeteocatSensorEntityDescription(
        key=TEMPERATURE,
        name="Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=HUMIDITY,
        name="Humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    MeteocatSensorEntityDescription(
        key=PRESSURE,
        name="Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
    ),
    MeteocatSensorEntityDescription(
        key=PRECIPITATION,
        name="Precipitation",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    ),
    MeteocatSensorEntityDescription(
        key=SOLAR_GLOBAL_IRRADIANCE,
        name="Solar Global Irradiance",
        icon="mdi:weather-sunny",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement = UnitOfIrradiance.WATTS_PER_SQUARE_METER,
    ),
    MeteocatSensorEntityDescription(
        key=UV_INDEX,
        name="UV Index",
        icon="mdi:weather-sunny",
    ),
    MeteocatSensorEntityDescription(
        key=MAX_TEMPERATURE,
        name="Max Temperature",
        icon="mdi:thermometer-plus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=MIN_TEMPERATURE,
        name="Min Temperature",
        icon="mdi:thermometer-minus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    MeteocatSensorEntityDescription(
        key=WIND_GUST,
        name="Wind Gust",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    # Sensores estáticos
    MeteocatSensorEntityDescription(
        key=TOWN_NAME,
        name="Town Name",
        icon="mdi:home-city",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=TOWN_ID,
        name="Town ID",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=STATION_NAME,
        name="Station Name",
        icon="mdi:broadcast",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
        key=STATION_ID,
        name="Station ID",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MeteocatSensorEntityDescription(
    key=STATION_TIMESTAMP,
    name="Station Timestamp",
    icon="mdi:calendar-clock",
    device_class=SensorDeviceClass.TIMESTAMP,
    )
)


@callback
async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Meteocat sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["sensor_coordinator"]

    async_add_entities(
        MeteocatSensor(coordinator, description, entry_data)
        for description in SENSOR_TYPES
    )

class MeteocatSensor(CoordinatorEntity[MeteocatSensorCoordinator], SensorEntity):
    """Representation of a Meteocat sensor."""
    STATIC_KEYS = {TOWN_NAME, TOWN_ID, STATION_NAME, STATION_ID}

    CODE_MAPPING = {
        WIND_SPEED: WIND_SPEED_CODE,
        WIND_DIRECTION: WIND_DIRECTION_CODE,
        TEMPERATURE: TEMPERATURE_CODE,
        HUMIDITY: HUMIDITY_CODE,
        PRESSURE: PRESSURE_CODE,
        PRECIPITATION: PRECIPITATION_CODE,
        SOLAR_GLOBAL_IRRADIANCE: SOLAR_GLOBAL_IRRADIANCE_CODE,
        UV_INDEX: UV_INDEX_CODE,
        MAX_TEMPERATURE: MAX_TEMPERATURE_CODE,
        MIN_TEMPERATURE: MIN_TEMPERATURE_CODE,
        WIND_GUST: WIND_GUST_CODE,
    }

    _attr_has_entity_name = True  # Activa el uso de nombres basados en el dispositivo

    def __init__(self, coordinator, description, entry_data):
        """Initialize the sensor."""
        super().__init__(coordinator)
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
        # Información dinámica
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
        if self.entity_description.key == "station_timestamp":
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
                                return datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                            except ValueError:
                                # Manejo de errores si el formato no es válido
                                return None

        return None

    @staticmethod
    def _convert_degrees_to_cardinal(degree: float) -> str:
        """Convert degrees to cardinal direction."""
        if not isinstance(degree, (int, float)):
            return "Unknown"  # Retorna "Unknown" si el valor no es un número válido

        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO", "N",
        ]
        index = round(degree / 22.5) % 16
        return directions[index]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},
            name=self._town_name,
            manufacturer="Meteocat",
            model="Meteocat API",
        )
