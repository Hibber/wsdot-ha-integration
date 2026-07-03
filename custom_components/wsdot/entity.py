"""Shared base entity and utilities for WSDOT Traffic integration."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import WSDOTDataUpdateCoordinator


def filter_none_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *attrs* with all None-valued keys removed."""
    return {k: v for k, v in attrs.items() if v is not None}


class WSDOTBaseEntity(CoordinatorEntity[WSDOTDataUpdateCoordinator]):
    """Base entity shared by all WSDOT platforms (sensor, binary_sensor, camera)."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        unique_id: str,
        device_name: str,
        device_id: str,
        *,
        manufacturer: str = "WSDOT",
        model: str = "Traffic API",
        configuration_url: str = "https://wsdot.wa.gov/traffic/",
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=manufacturer,
            model=model,
            configuration_url=configuration_url,
        )
