"""Camera platform for WSDOT Traffic (highway camera snapshots)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_CAMERAS,
    DOMAIN,
    ICON_CAMERA,
)
from .coordinator import WSDOTDataUpdateCoordinator
from .entity import WSDOTBaseEntity, filter_none_attrs

_LOGGER = logging.getLogger(__name__)

# Only show highway cameras (not airport cameras) by default — filter on RoadName
HIGHWAY_ROAD_NAMES = {"Airports"}  # These are excluded by default (airport cams)
ACTIVE_ONLY = True  # Only show IsActive cameras


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WSDOT camera entities."""
    coordinator: WSDOTDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[Camera] = []

    for record in coordinator.data.get(DATA_CAMERAS, []):
        camera_id = record.get("CameraID")
        if camera_id is None:
            continue

        # Skip inactive cameras
        if ACTIVE_ONLY and not record.get("IsActive", True):
            continue

        # Exclude airport cameras to limit entity count (optional, can be removed)
        road_name = (record.get("CameraLocation") or {}).get("RoadName", "")
        if road_name == "Airports":
            continue

        entities.append(WSDOTCamera(coordinator, camera_id))

    _LOGGER.info("Setting up %d WSDOT highway cameras", len(entities))
    async_add_entities(entities)


class WSDOTCamera(WSDOTBaseEntity, Camera):
    """Representation of a WSDOT highway camera."""

    _attr_icon = ICON_CAMERA
    _attr_frame_interval = 60  # seconds between frame refreshes

    def __init__(
        self,
        coordinator: WSDOTDataUpdateCoordinator,
        camera_id: int,
    ) -> None:
        """Initialise camera entity."""
        record = coordinator.get_camera(camera_id) or {}
        title = record.get("Title", f"Camera {camera_id}")

        WSDOTBaseEntity.__init__(
            self,
            coordinator,
            unique_id=f"{DOMAIN}_camera_{camera_id}",
            device_name=title,
            device_id=f"camera_{camera_id}",
            manufacturer=record.get("CameraOwner") or "WSDOT",
            model="Highway Camera",
            configuration_url=record.get("OwnerURL") or "https://wsdot.wa.gov/traffic/",
        )
        Camera.__init__(self)

        self._camera_id = camera_id
        self._attr_name = title
        self._image_url: str | None = record.get("ImageURL")
        self._cached_image: bytes | None = None

    @property
    def _record(self) -> dict:
        return self.coordinator.get_camera(self._camera_id) or {}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional camera attributes for the Lovelace panel."""
        rec = self._record
        loc = rec.get("CameraLocation") or {}
        return filter_none_attrs({
            "camera_id": self._camera_id,
            "title": rec.get("Title"),
            "description": rec.get("Description"),
            "image_url": rec.get("ImageURL"),
            "road_name": loc.get("RoadName"),
            "direction": loc.get("Direction"),
            "milepost": loc.get("MilePost"),
            "latitude": rec.get("DisplayLatitude"),
            "longitude": rec.get("DisplayLongitude"),
            "region": rec.get("Region"),
            "camera_owner": rec.get("CameraOwner"),
            "owner_url": rec.get("OwnerURL"),
            "is_active": rec.get("IsActive"),
        })

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return current camera image."""
        rec = self._record
        image_url = rec.get("ImageURL") or self._image_url
        if not image_url:
            _LOGGER.debug("No image URL for camera %s", self._camera_id)
            return self._cached_image

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                image_url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    self._cached_image = await resp.read()
                    return self._cached_image
                _LOGGER.warning(
                    "Camera %s returned HTTP %s for URL %s",
                    self._camera_id,
                    resp.status,
                    image_url,
                )
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout fetching camera %s", self._camera_id)
        except aiohttp.ClientError as err:
            _LOGGER.warning("Error fetching camera %s: %s", self._camera_id, err)

        if self._cached_image is not None:
            _LOGGER.debug(
                "Returning stale cached image for camera %s", self._camera_id
            )
        else:
            _LOGGER.warning(
                "No cached image available for camera %s after fetch failure",
                self._camera_id,
            )
        return self._cached_image

    @property
    def is_streaming(self) -> bool:
        """No live stream — just snapshots."""
        return False
