"""DataUpdateCoordinator for WSDOT Traffic."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CAMERAS_URL,
    CONF_API_KEY,
    DATA_CAMERAS,
    DATA_FLOW,
    DATA_PASS_CONDITIONS,
    DATA_TRAVEL_TIMES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FLOW_DATA_URL,
    PASS_CONDITIONS_URL,
    TRAVEL_TIMES_URL,
)

_LOGGER = logging.getLogger(__name__)

# Regex to parse WSDOT's /Date(...)/ format
_DATE_RE = re.compile(r"/Date\((-?\d+)([+-]\d{4})?\)/")


def parse_wsdot_date(date_str: str | None) -> datetime | None:
    """Parse WSDOT's /Date(epoch-offset)/ format into a datetime."""
    if not date_str:
        return None
    m = _DATE_RE.match(date_str)
    if not m:
        return None
    epoch_ms = int(m.group(1))
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


class WSDOTDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches all WSDOT data on a schedule."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        self._api_key = entry.data[CONF_API_KEY]
        scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_json(self, session: aiohttp.ClientSession, url: str) -> Any:
        """Fetch JSON from *url*, returning parsed data or None on error."""
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Failed to fetch %s: %s", url, err)
            return None

    # ------------------------------------------------------------------
    # DataUpdateCoordinator interface
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all WSDOT data concurrently."""
        key = self._api_key
        urls = {
            DATA_TRAVEL_TIMES: TRAVEL_TIMES_URL.format(api_key=key),
            DATA_PASS_CONDITIONS: PASS_CONDITIONS_URL.format(api_key=key),
            DATA_CAMERAS: CAMERAS_URL.format(api_key=key),
            DATA_FLOW: FLOW_DATA_URL.format(api_key=key),
        }

        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(
                *[self._fetch_json(session, url) for url in urls.values()],
                return_exceptions=True,
            )

        data: dict[str, Any] = {}
        for key_name, result in zip(urls.keys(), results):
            if isinstance(result, Exception):
                _LOGGER.error("Error fetching %s: %s", key_name, result)
                # Keep previous data if available
                if self.data and key_name in self.data:
                    data[key_name] = self.data[key_name]
                else:
                    data[key_name] = []
            else:
                data[key_name] = result or []

        if not data[DATA_TRAVEL_TIMES] and not data[DATA_PASS_CONDITIONS]:
            raise UpdateFailed("No data received from WSDOT API")

        return data

    # ------------------------------------------------------------------
    # Convenience lookups
    # ------------------------------------------------------------------

    def get_travel_time(self, travel_time_id: int) -> dict | None:
        """Return a specific travel time record by ID."""
        if not self.data:
            return None
        for record in self.data.get(DATA_TRAVEL_TIMES, []):
            if record.get("TravelTimeID") == travel_time_id:
                return record
        return None

    def get_pass(self, pass_id: int) -> dict | None:
        """Return a specific mountain pass record by ID."""
        if not self.data:
            return None
        for record in self.data.get(DATA_PASS_CONDITIONS, []):
            if record.get("MountainPassId") == pass_id:
                return record
        return None

    def get_camera(self, camera_id: int) -> dict | None:
        """Return a specific camera record by ID."""
        if not self.data:
            return None
        for record in self.data.get(DATA_CAMERAS, []):
            if record.get("CameraID") == camera_id:
                return record
        return None

    def get_flow_station(self, flow_station_id: int) -> dict | None:
        """Return a specific flow station by ID."""
        if not self.data:
            return None
        for record in self.data.get(DATA_FLOW, []):
            if record.get("FlowStationID") == flow_station_id:
                return record
        return None
