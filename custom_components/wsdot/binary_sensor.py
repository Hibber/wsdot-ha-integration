"""Binary sensor platform for WSDOT Traffic (travel advisories, congestion alerts)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DATA_PASS_CONDITIONS,
    DATA_TRAVEL_TIMES,
    DOMAIN,
    ICON_ADVISORY,
    ICON_CONGESTION,
)
from .coordinator import WSDOTDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WSDOT binary sensor entities."""
    coordinator: WSDOTDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Mountain pass travel advisories
    for record in coordinator.data.get(DATA_PASS_CONDITIONS, []):
        pass_id = record.get("MountainPassId")
        if pass_id is None:
            continue
        entities.append(WSDOTPassAdvisoryBinarySensor(coordinator, pass_id))

    # Travel time congestion alerts (when current > 150% of average)
    for record in coordinator.data.get(DATA_TRAVEL_TIMES, []):
        tt_id = record.get("TravelTimeID")
        if tt_id is None:
            continue
        entities.append(WSDOTCongestionBinarySensor(coordinator, tt_id))

    async_add_entities(entities)


class WSDOTBinaryEntity(CoordinatorEntity[WSDOTDataUpdateCoordinator]):
    """Base binary sensor entity for WSDOT integration."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        unique_id: str,
        device_name: str,
        device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="WSDOT",
            model="Traffic API",
            configuration_url="https://wsdot.wa.gov/traffic/",
        )


class WSDOTPassAdvisoryBinarySensor(WSDOTBinaryEntity, BinarySensorEntity):
    """Binary sensor: is a travel advisory active for this mountain pass?"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = ICON_ADVISORY

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        pass_id: int,
    ) -> None:
        record = coordinator.get_pass(pass_id) or {}
        pass_name = record.get("MountainPassName", f"Pass {pass_id}")
        device_id = f"pass_{pass_id}"
        super().__init__(
            coordinator,
            unique_id=f"{DOMAIN}_pass_{pass_id}_advisory",
            device_name=pass_name,
            device_id=device_id,
        )
        self._pass_id = pass_id
        self._attr_name = "Travel Advisory Active"

    @property
    def _record(self) -> dict:
        return self.coordinator.get_pass(self._pass_id) or {}

    @property
    def is_on(self) -> bool:
        """Return True if a travel advisory is active."""
        return bool(self._record.get("TravelAdvisoryActive", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        rec = self._record
        return {
            k: v
            for k, v in {
                "pass_name": rec.get("MountainPassName"),
                "restriction_one": rec.get("RestrictionOne", {}).get("RestrictionText"),
                "restriction_two": rec.get("RestrictionTwo", {}).get("RestrictionText"),
                "road_condition": rec.get("RoadCondition"),
            }.items()
            if v is not None
        }


class WSDOTCongestionBinarySensor(WSDOTBinaryEntity, BinarySensorEntity):
    """Binary sensor: is this route experiencing significant congestion?"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = ICON_CONGESTION

    # Congestion threshold: current time > average * threshold
    CONGESTION_THRESHOLD = 1.25

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        travel_time_id: int,
    ) -> None:
        record = coordinator.get_travel_time(travel_time_id) or {}
        route_name = record.get("Name", f"Route {travel_time_id}")
        device_id = f"travel_time_{travel_time_id}"
        super().__init__(
            coordinator,
            unique_id=f"{DOMAIN}_tt_{travel_time_id}_congestion",
            device_name=route_name,
            device_id=device_id,
        )
        self._travel_time_id = travel_time_id
        self._attr_name = "Congestion Alert"

    @property
    def _record(self) -> dict:
        return self.coordinator.get_travel_time(self._travel_time_id) or {}

    @property
    def is_on(self) -> bool:
        """Return True if current time significantly exceeds average."""
        rec = self._record
        avg = rec.get("AverageTime", 0)
        cur = rec.get("CurrentTime", 0)
        if avg and cur and avg > 0:
            return (cur / avg) > self.CONGESTION_THRESHOLD
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        rec = self._record
        avg = rec.get("AverageTime", 0)
        cur = rec.get("CurrentTime", 0)
        return {
            k: v
            for k, v in {
                "current_time_minutes": cur,
                "average_time_minutes": avg,
                "delay_minutes": max(0, cur - avg) if avg and cur else None,
                "congestion_ratio": round(cur / avg, 2) if avg else None,
                "route_name": rec.get("Name"),
                "description": rec.get("Description"),
            }.items()
            if v is not None
        }
