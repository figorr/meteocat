from __future__ import annotations

from dataclasses import dataclass
from homeassistant.helpers.entity import DeviceInfo
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

@dataclass
class MeteocatSensorEntityDescription(SensorEntityDescription):
    """A class that describes Meteocat sensor entities."""

SENSOR_TYPES: tuple[MeteocatSensorEntityDescription, ...] = (
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

    def __init__(self, coordinator, description, entry_data):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.api_key = entry_data["api_key"]
        self._town_name = entry_data["town_name"]
        self._town_id = entry_data["town_id"]

        # Unique ID for the entity
        self._attr_unique_id = f"{self._town_id}_{self.entity_description.key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
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

        return None

    @staticmethod
    def _convert_degrees_to_cardinal(degree: float) -> str:
        """Convert degrees to cardinal direction."""
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N",
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
