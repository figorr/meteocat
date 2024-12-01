from dataclasses import dataclass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature

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
    WIND_SPEED_UNIT,
    PRESSURE_UNIT,
    PRECIPITATION_UNIT,
    UV_INDEX_UNIT,
    WIND_DIRECTION_UNIT
)

from .coordinator import MeteocatDataCoordinator

@dataclass
class MeteocatSensorEntityDescription(SensorEntityDescription):
    """A class that describes sensor entities"""

SENSOR_TYPES: tuple[MeteocatSensorEntityDescription, ...] = (
    MeteocatSensorEntityDescription(
        key=WIND_SPEED,
        name="Wind Speed",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=WIND_SPEED_UNIT
    ),
    MeteocatSensorEntityDescription(
        key=WIND_DIRECTION,
        name="Wind Direction",
        icon="mdi:compass",
        device_class=SensorDeviceClass.DIRECTION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=WIND_DIRECTION_UNIT
    ),
    MeteocatSensorEntityDescription(
        key=TEMPERATURE,
        name="Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature
    ),
    MeteocatSensorEntityDescription(
        key=HUMIDITY,
        name="Humidity",
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE
    ),
    MeteocatSensorEntityDescription(
        key=PRESSURE,
        name="Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PRESSURE_UNIT
    ),
    MeteocatSensorEntityDescription(
        key=PRECIPITATION,
        name="Precipitation",
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PRECIPITATION_UNIT
    ),
    MeteocatSensorEntityDescription(
        key=UV_INDEX,
        name="UV Index",
        icon="mdi:sun",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UV_INDEX_UNIT
    ),
    MeteocatSensorEntityDescription(
        key=MAX_TEMPERATURE,
        name="Max Temperature",
        icon="mdi:thermometer-plus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature
    ),
    MeteocatSensorEntityDescription(
        key=MIN_TEMPERATURE,
        name="Min Temperature",
        icon="mdi:thermometer-minus",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature
    ),
    MeteocatSensorEntityDescription(
        key=WIND_GUST,
        name="Wind Gust",
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=WIND_SPEED
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Meteocat sensor."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    if config_entry.options:
        config.update(config_entry.options)

    coordinator = MeteocatDataCoordinator(hass, config['api_key'], config['municipality'])

    await coordinator.async_config_entry_first_refresh()

    # Obtener el town_name desde los datos guardados en config_entry
    town_name = config_entry.data.get("town_name")  # 'town_name' es el nombre del municipio guardado en config_flow.py

    # Obtener el town_id desde los datos guardados en config_entry
    town_id = config_entry.data.get("town_id")  # 'town_id' es el código del municipio guardado en config_flow.py

    # Obtener el station_name desde los datos guardados en config_entry
    station_name = config_entry.data.get("station_name")  # 'station_name_id' es el nombre de la estación guardada en config_flow.py

    # Obtener el station_id desde los datos guardados en config_entry
    station_id = config_entry.data.get("station_id")  # 'station_id' es el código de la estación guardada en config_flow.py

    async_add_entities(
        MeteocatSensor(coordinator, description, town_name, town_id, station_name, station_id)
        for description in SENSOR_TYPES
    )

class MeteocatSensor(
    CoordinatorEntity[MeteocatDataCoordinator],
    SensorEntity,
):
    """Implementation of a Meteocat sensor."""

    _attr_has_entity_name = True
    entity_description: MeteocatSensorEntityDescription

    def __init__(
        self,
        coordinator: MeteocatDataCoordinator,
        description: MeteocatSensorEntityDescription,
        town_name: str,
        town_id: str,
        station_name: str,
        station_id: str,
    ) -> None:
        """Initialize the Meteocat sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._town_name = town_name
        self._town_id = town_id
        self._station_name = station_name
        self._station_id = station_id
        # Crear unique_id utilizando town_id y key del sensor
        self._attr_unique_id = f"{self._town_name}_{self.entity_description.key}"
        self._attr_native_value = getattr(self.coordinator.data, self.entity_description.key)

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        # Si es el sensor de dirección del viento, convertir grados a dirección cardinal
        if self.entity_description.key == WIND_DIRECTION:
            return self._convert_degrees_to_cardinal(self._attr_native_value)

        # Para los demás sensores, devolver el valor normal
        return self._attr_native_value

    @staticmethod
    def _convert_degrees_to_cardinal(degree: float | None) -> str | None:
        """Convert degrees to cardinal direction."""
        if degree is None:
            return None

        # Lista de direcciones cardinales
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"
        ]

        # Cálculo del índice de la dirección
        index = int(((degree + 11.25) / 22.5)) % 16
        return directions[index]

    @property
    def native_unit_of_measurement(self) -> StateType:
        return self.entity_description.native_unit_of_measurement

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = getattr(self.coordinator.data, self.entity_description.key)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._town_id)},  # Usar town_id como identificador único
            name=f"{self._town_name}",  # Mostrar el nombre del municipio
            manufacturer="Meteocat",
            model="Meteocat API",
            additional_properties={  # Detalles adicionales visibles en configuración avanzada
                "ID Municipio": self._town_id,
                "Estación": self._station_name,
                "ID Estación": self._station_id,
            },
        )

