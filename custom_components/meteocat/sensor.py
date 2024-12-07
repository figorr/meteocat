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
)

from .const import (
    DOMAIN,
    WIND_SPEED,
    WIND_DIRECTION,
    TEMPERATURE,
    HUMIDITY,
    PRESSURE,
    PRECIPITATION,
    UV_INDEX,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    WIND_GUST,
    VARIABLE_CODE_MAPPING,
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
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
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
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
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

    def __init__(self, coordinator, description, entry_data):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.api_key = entry_data["api_key"]  # Usamos la API key de la configuración
        self._town_name = entry_data["town_name"]  # Usamos el nombre del municipio
        self._town_id = entry_data["town_id"]  # Usamos el ID del municipio
        self._variable_name = entry_data["variable_name"]  # Usamos el nombre de la variable
        self._variable_id = entry_data["variable_id"]  # Usamos el ID de la variable
        self._station_name = entry_data["station_name"]  # Usamos el nombre de la estación
        self._station_id = entry_data["station_id"]  # Usamos el ID de la estación

        # Unique ID for the entity
        self._attr_unique_id = f"{self._town_id}_{self.entity_description.key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        sensor_code = next(
            (code for code, key in VARIABLE_CODE_MAPPING.items() if key == self.entity_description.key),
            None,
        )
        
        if sensor_code is not None:
            variable_data = next(
                (var for var in self.coordinator.data.get("variables", []) if var["codi"] == sensor_code),
                None,
            )
            if variable_data:
                # Asume que quieres el último valor registrado
                latest_reading = variable_data["lectures"][-1]
                value = latest_reading.get("valor")

                # Convertir grados a direcciones cardinales para WIND_DIRECTION
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
            model="Meteocat API"
        )
