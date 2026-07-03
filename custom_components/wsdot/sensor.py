"""Sensor platform for WSDOT Traffic."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_FLOW,
    DATA_PASS_CONDITIONS,
    DATA_TRAVEL_TIMES,
    DOMAIN,
    ICON_CONGESTION,
    ICON_PASS,
    ICON_TEMPERATURE,
    ICON_TRAVEL_TIME,
)
from .coordinator import WSDOTDataUpdateCoordinator, parse_wsdot_date
from .entity import WSDOTBaseEntity, filter_none_attrs

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WSDOT sensor entities."""
    coordinator: WSDOTDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # --- Travel Time sensors ---
    for record in coordinator.data.get(DATA_TRAVEL_TIMES, []):
        tt_id = record.get("TravelTimeID")
        if tt_id is None:
            continue
        entities.append(WSDOTTravelTimeSensor(coordinator, tt_id, "current"))
        entities.append(WSDOTTravelTimeSensor(coordinator, tt_id, "average"))

    # --- Mountain Pass sensors ---
    for record in coordinator.data.get(DATA_PASS_CONDITIONS, []):
        pass_id = record.get("MountainPassId")
        if pass_id is None:
            continue
        entities.append(WSDOTPassConditionSensor(coordinator, pass_id))
        if record.get("TemperatureInFahrenheit") is not None:
            entities.append(WSDOTPassTemperatureSensor(coordinator, pass_id))

    # --- Traffic Flow sensors ---
    flow_data = coordinator.data.get(DATA_FLOW, [])
    if isinstance(flow_data, list):
        for record in flow_data:
            station_id = record.get("FlowStationID")
            if station_id is None:
                continue
            entities.append(WSDOTFlowSensor(coordinator, station_id))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Travel Time sensors
# ---------------------------------------------------------------------------

class WSDOTTravelTimeSensor(WSDOTBaseEntity, SensorEntity):
    """Sensor for a WSDOT travel time route (current or average)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = ICON_TRAVEL_TIME

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        travel_time_id: int,
        kind: str,  # "current" or "average"
    ) -> None:
        """Initialise travel time sensor."""
        record = coordinator.get_travel_time(travel_time_id) or {}
        route_name = record.get("Name", f"Route {travel_time_id}")
        device_id = f"travel_time_{travel_time_id}"

        super().__init__(
            coordinator,
            unique_id=f"{DOMAIN}_tt_{travel_time_id}_{kind}",
            device_name=route_name,
            device_id=device_id,
        )
        self._travel_time_id = travel_time_id
        self._kind = kind
        self._attr_name = "Current Travel Time" if kind == "current" else "Average Travel Time"

    @property
    def _record(self) -> dict:
        return self.coordinator.get_travel_time(self._travel_time_id) or {}

    @property
    def native_value(self) -> int | None:
        """Return the travel time in minutes."""
        key = "CurrentTime" if self._kind == "current" else "AverageTime"
        val = self._record.get(key)
        return int(val) if val is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        rec = self._record
        attrs: dict[str, Any] = {
            "travel_time_id": self._travel_time_id,
            "description": rec.get("Description"),
            "distance_miles": rec.get("Distance"),
            "road_name": rec.get("StartPoint", {}).get("RoadName"),
            "direction": rec.get("StartPoint", {}).get("Direction"),
            "start_description": rec.get("StartPoint", {}).get("Description"),
            "end_description": rec.get("EndPoint", {}).get("Description"),
            "start_latitude": rec.get("StartPoint", {}).get("Latitude"),
            "start_longitude": rec.get("StartPoint", {}).get("Longitude"),
            "end_latitude": rec.get("EndPoint", {}).get("Latitude"),
            "end_longitude": rec.get("EndPoint", {}).get("Longitude"),
        }
        time_updated = parse_wsdot_date(rec.get("TimeUpdated"))
        if time_updated:
            attrs["last_updated"] = time_updated.isoformat()
        if self._kind == "current":
            avg = rec.get("AverageTime")
            cur = rec.get("CurrentTime")
            if avg and cur:
                attrs["congestion_ratio"] = round(cur / avg, 2)
                attrs["delay_minutes"] = max(0, cur - avg)
        return filter_none_attrs(attrs)


# ---------------------------------------------------------------------------
# Mountain Pass sensors
# ---------------------------------------------------------------------------

class WSDOTPassConditionSensor(WSDOTBaseEntity, SensorEntity):
    """Sensor for mountain pass road condition."""

    _attr_icon = ICON_PASS

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        pass_id: int,
    ) -> None:
        """Initialise pass condition sensor."""
        record = coordinator.get_pass(pass_id) or {}
        pass_name = record.get("MountainPassName", f"Pass {pass_id}")
        device_id = f"pass_{pass_id}"

        super().__init__(
            coordinator,
            unique_id=f"{DOMAIN}_pass_{pass_id}_condition",
            device_name=pass_name,
            device_id=device_id,
        )
        self._pass_id = pass_id
        self._attr_name = "Road Condition"

    @property
    def _record(self) -> dict:
        return self.coordinator.get_pass(self._pass_id) or {}

    @property
    def native_value(self) -> str | None:
        """Return the road condition."""
        condition = self._record.get("RoadCondition")
        if not condition:
            return "Unknown"
        # Truncate long conditions to 255 chars for HA state
        return condition[:255] if condition else "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        rec = self._record
        attrs: dict[str, Any] = {
            "pass_id": self._pass_id,
            "pass_name": rec.get("MountainPassName"),
            "weather_condition": rec.get("WeatherCondition"),
            "elevation_feet": rec.get("ElevationInFeet"),
            "latitude": rec.get("Latitude"),
            "longitude": rec.get("Longitude"),
            "travel_advisory_active": rec.get("TravelAdvisoryActive"),
            "restriction_one": rec.get("RestrictionOne", {}).get("RestrictionText"),
            "restriction_one_direction": rec.get("RestrictionOne", {}).get("TravelDirection"),
            "restriction_two": rec.get("RestrictionTwo", {}).get("RestrictionText"),
            "restriction_two_direction": rec.get("RestrictionTwo", {}).get("TravelDirection"),
            "full_road_condition": rec.get("RoadCondition"),
        }
        date_updated = parse_wsdot_date(rec.get("DateUpdated"))
        if date_updated:
            attrs["last_updated"] = date_updated.isoformat()
        return filter_none_attrs(attrs)


class WSDOTPassTemperatureSensor(WSDOTBaseEntity, SensorEntity):
    """Sensor for mountain pass temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = ICON_TEMPERATURE

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        pass_id: int,
    ) -> None:
        """Initialise pass temperature sensor."""
        record = coordinator.get_pass(pass_id) or {}
        pass_name = record.get("MountainPassName", f"Pass {pass_id}")
        device_id = f"pass_{pass_id}"

        super().__init__(
            coordinator,
            unique_id=f"{DOMAIN}_pass_{pass_id}_temperature",
            device_name=pass_name,
            device_id=device_id,
        )
        self._pass_id = pass_id
        self._attr_name = "Temperature"

    @property
    def _record(self) -> dict:
        return self.coordinator.get_pass(self._pass_id) or {}

    @property
    def native_value(self) -> float | None:
        """Return the temperature in Fahrenheit."""
        temp = self._record.get("TemperatureInFahrenheit")
        return float(temp) if temp is not None else None


# ---------------------------------------------------------------------------
# Traffic Flow sensor
# ---------------------------------------------------------------------------

class WSDOTFlowSensor(WSDOTBaseEntity, SensorEntity):
    """Sensor for a WSDOT traffic flow station."""

    _attr_icon = ICON_CONGESTION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "vehicles/5min"

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        station_id: int,
    ) -> None:
        """Initialise flow sensor."""
        record = coordinator.get_flow_station(station_id) or {}
        station_name = record.get(
            "StationName", f"Flow Station {station_id}"
        )
        device_id = f"flow_{station_id}"

        super().__init__(
            coordinator,
            unique_id=f"{DOMAIN}_flow_{station_id}",
            device_name=station_name,
            device_id=device_id,
        )
        self._station_id = station_id
        self._attr_name = "Flow Count"

    @property
    def _record(self) -> dict:
        return self.coordinator.get_flow_station(self._station_id) or {}

    @property
    def native_value(self) -> int | None:
        """Return the flow count."""
        # Try common WSDOT flow count fields
        for field in ("FlowCount", "Count", "Volume"):
            val = self._record.get(field)
            if val is not None:
                return int(val)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        rec = self._record
        return filter_none_attrs({
            "station_id": self._station_id,
            "station_name": rec.get("StationName"),
            "road_name": rec.get("RoadName"),
            "direction": rec.get("Direction"),
            "latitude": rec.get("Latitude"),
            "longitude": rec.get("Longitude"),
            "flow_reading_value": rec.get("FlowReadingValue"),
            "congestion_category": rec.get("CongestionCategory"),
        })
