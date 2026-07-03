"""Shared fixtures and HA mock infrastructure for WSDOT tests."""
from __future__ import annotations

import sys
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out homeassistant packages before importing our code
# ---------------------------------------------------------------------------

# Create a comprehensive HA mock module tree
ha_mock = MagicMock()


# --- homeassistant.core ---
class _FakeHomeAssistant:
    def __init__(self):
        self.data = {}
        self.config_entries = MagicMock()


class _FakeCallback:
    """Decorator that marks a function as a callback."""
    def __call__(self, func):
        return func


ha_mock.core.HomeAssistant = _FakeHomeAssistant
ha_mock.core.callback = _FakeCallback()


# --- homeassistant.config_entries ---
class _FakeConfigEntry:
    def __init__(self, entry_id="test_entry", data=None, options=None):
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}

    def add_update_listener(self, listener):
        return MagicMock()

    def async_on_unload(self, unsub):
        pass


class _FakeConfigFlow:
    """Stub for config_entries.ConfigFlow."""
    domain = None

    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if domain:
            cls.domain = domain

    def __init__(self):
        self.hass = _FakeHomeAssistant()

    async def async_set_unique_id(self, uid):
        pass

    def _abort_if_unique_id_configured(self):
        pass

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}


class _FakeOptionsFlow:
    """Stub for config_entries.OptionsFlow."""
    def __init__(self, config_entry=None):
        self.config_entry = config_entry

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}


ha_mock.config_entries.ConfigEntry = _FakeConfigEntry
ha_mock.config_entries.ConfigFlow = _FakeConfigFlow
ha_mock.config_entries.OptionsFlow = _FakeOptionsFlow

# --- homeassistant.const ---
ha_mock.const.Platform = MagicMock()
ha_mock.const.UnitOfTemperature = MagicMock()
ha_mock.const.UnitOfTemperature.FAHRENHEIT = "°F"
ha_mock.const.UnitOfTime = MagicMock()
ha_mock.const.UnitOfTime.MINUTES = "min"

# --- homeassistant.data_entry_flow ---
ha_mock.data_entry_flow.FlowResult = dict

# --- homeassistant.helpers ---
ha_mock.helpers.config_validation.positive_int = int
ha_mock.helpers.config_validation = MagicMock()
ha_mock.helpers.config_validation.positive_int = int


# --- homeassistant.helpers.entity ---
class _FakeDeviceInfo:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


ha_mock.helpers.entity.DeviceInfo = _FakeDeviceInfo

# --- homeassistant.helpers.entity_platform ---
ha_mock.helpers.entity_platform.AddEntitiesCallback = Any

# --- homeassistant.helpers.aiohttp_client ---
ha_mock.helpers.aiohttp_client.async_get_clientsession = MagicMock()

# --- homeassistant.helpers.update_coordinator ---
class _FakeDataUpdateCoordinator:
    """Minimal stub of DataUpdateCoordinator."""
    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    async def async_config_entry_first_refresh(self):
        self.data = await self._async_update_data()


class _FakeUpdateFailed(Exception):
    pass


ha_mock.helpers.update_coordinator.DataUpdateCoordinator = _FakeDataUpdateCoordinator
ha_mock.helpers.update_coordinator.UpdateFailed = _FakeUpdateFailed


# --- homeassistant.helpers.update_coordinator.CoordinatorEntity ---
class _CoordinatorEntityMeta(type):
    """Metaclass to support CoordinatorEntity[T] subscript syntax."""
    def __getitem__(cls, item):
        return cls


class _FakeCoordinatorEntity(metaclass=_CoordinatorEntityMeta):
    """Minimal stub of CoordinatorEntity."""
    def __init__(self, coordinator):
        self.coordinator = coordinator


ha_mock.helpers.update_coordinator.CoordinatorEntity = _FakeCoordinatorEntity

# --- homeassistant.components.sensor ---
ha_mock.components.sensor.SensorDeviceClass = MagicMock()
ha_mock.components.sensor.SensorDeviceClass.DURATION = "duration"
ha_mock.components.sensor.SensorDeviceClass.TEMPERATURE = "temperature"
ha_mock.components.sensor.SensorEntityDescription = MagicMock
ha_mock.components.sensor.SensorStateClass = MagicMock()
ha_mock.components.sensor.SensorStateClass.MEASUREMENT = "measurement"


class _FakeSensorEntity:
    """Stub for SensorEntity base class."""
    pass


ha_mock.components.sensor.SensorEntity = _FakeSensorEntity

# --- homeassistant.components.binary_sensor ---
ha_mock.components.binary_sensor.BinarySensorDeviceClass = MagicMock()
ha_mock.components.binary_sensor.BinarySensorDeviceClass.PROBLEM = "problem"


class _FakeBinarySensorEntity:
    """Stub for BinarySensorEntity base class."""
    pass


ha_mock.components.binary_sensor.BinarySensorEntity = _FakeBinarySensorEntity

# --- homeassistant.components.camera ---
ha_mock.components.camera.CameraEntityFeature = MagicMock()


class _FakeCamera:
    """Stub for Camera base class."""
    def __init__(self):
        pass


ha_mock.components.camera.Camera = _FakeCamera

# Register all the HA mocks in sys.modules
_ha_modules = {
    "homeassistant": ha_mock,
    "homeassistant.core": ha_mock.core,
    "homeassistant.const": ha_mock.const,
    "homeassistant.config_entries": ha_mock.config_entries,
    "homeassistant.data_entry_flow": ha_mock.data_entry_flow,
    "homeassistant.helpers": ha_mock.helpers,
    "homeassistant.helpers.config_validation": ha_mock.helpers.config_validation,
    "homeassistant.helpers.entity": ha_mock.helpers.entity,
    "homeassistant.helpers.entity_platform": ha_mock.helpers.entity_platform,
    "homeassistant.helpers.aiohttp_client": ha_mock.helpers.aiohttp_client,
    "homeassistant.helpers.update_coordinator": ha_mock.helpers.update_coordinator,
    "homeassistant.components": ha_mock.components,
    "homeassistant.components.sensor": ha_mock.components.sensor,
    "homeassistant.components.binary_sensor": ha_mock.components.binary_sensor,
    "homeassistant.components.camera": ha_mock.components.camera,
}

for mod_name, mod in _ha_modules.items():
    sys.modules.setdefault(mod_name, mod)

# Also stub voluptuous since it's used in config_flow
vol_mock = MagicMock()
vol_mock.Schema = MagicMock(side_effect=lambda x: x)
vol_mock.Required = MagicMock(side_effect=lambda x: x)
vol_mock.Optional = MagicMock(side_effect=lambda x, **kw: x)
vol_mock.All = MagicMock(side_effect=lambda *a: a[0])
vol_mock.Range = MagicMock(return_value=None)
sys.modules.setdefault("voluptuous", vol_mock)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_travel_times():
    """Sample travel time data from WSDOT API."""
    return [
        {
            "TravelTimeID": 101,
            "Name": "I-5 Olympia to Tacoma",
            "Description": "Northbound I-5 from Olympia to Tacoma",
            "Distance": 30.5,
            "CurrentTime": 35,
            "AverageTime": 28,
            "TimeUpdated": "/Date(1688400000000-0700)/",
            "StartPoint": {
                "Latitude": 47.04,
                "Longitude": -122.90,
                "RoadName": "005",
                "Direction": "N",
                "Description": "Olympia",
            },
            "EndPoint": {
                "Latitude": 47.25,
                "Longitude": -122.44,
                "RoadName": "005",
                "Direction": "N",
                "Description": "Tacoma",
            },
        },
        {
            "TravelTimeID": 202,
            "Name": "SR-520 Bellevue to Seattle",
            "Description": "Westbound SR-520",
            "Distance": 8.2,
            "CurrentTime": 15,
            "AverageTime": 12,
            "TimeUpdated": "/Date(1688400000000-0700)/",
            "StartPoint": {
                "Latitude": 47.63,
                "Longitude": -122.18,
                "RoadName": "520",
                "Direction": "W",
                "Description": "Bellevue",
            },
            "EndPoint": {
                "Latitude": 47.64,
                "Longitude": -122.32,
                "RoadName": "520",
                "Direction": "W",
                "Description": "Seattle",
            },
        },
        {
            "TravelTimeID": 303,
            "Name": "US-2 Spokane to Airway Heights",
            "Description": "Westbound US-2 in Spokane",
            "Distance": 5.0,
            "CurrentTime": 8,
            "AverageTime": 7,
            "TimeUpdated": None,
            "StartPoint": {
                "Latitude": 47.66,
                "Longitude": -117.42,
                "RoadName": "002",
                "Direction": "W",
                "Description": "Spokane",
            },
            "EndPoint": {
                "Latitude": 47.65,
                "Longitude": -117.59,
                "RoadName": "002",
                "Direction": "W",
                "Description": "Airway Heights",
            },
        },
    ]


@pytest.fixture
def sample_pass_conditions():
    """Sample mountain pass data from WSDOT API."""
    return [
        {
            "MountainPassId": 11,
            "MountainPassName": "Snoqualmie Pass",
            "RoadCondition": "Wet, chains required for all vehicles.",
            "WeatherCondition": "Snowing",
            "TemperatureInFahrenheit": 28,
            "ElevationInFeet": 3022,
            "Latitude": 47.3929,
            "Longitude": -121.4117,
            "TravelAdvisoryActive": True,
            "DateUpdated": "/Date(1688400000000-0700)/",
            "RestrictionOne": {
                "RestrictionText": "Chains required",
                "TravelDirection": "Both",
            },
            "RestrictionTwo": {
                "RestrictionText": "No oversized vehicles",
                "TravelDirection": "Eastbound",
            },
        },
        {
            "MountainPassId": 10,
            "MountainPassName": "Stevens Pass",
            "RoadCondition": "Bare and dry.",
            "WeatherCondition": "Clear",
            "TemperatureInFahrenheit": 45,
            "ElevationInFeet": 4061,
            "Latitude": 47.7467,
            "Longitude": -121.0892,
            "TravelAdvisoryActive": False,
            "DateUpdated": "/Date(1688400000000-0700)/",
            "RestrictionOne": {"RestrictionText": None, "TravelDirection": None},
            "RestrictionTwo": {"RestrictionText": None, "TravelDirection": None},
        },
        {
            "MountainPassId": 99,
            "MountainPassName": "Remote Pass",
            "RoadCondition": "Closed",
            "WeatherCondition": "Blizzard",
            "TemperatureInFahrenheit": 5,
            "ElevationInFeet": 5500,
            "Latitude": 48.9,
            "Longitude": -120.5,
            "TravelAdvisoryActive": True,
            "DateUpdated": None,
            "RestrictionOne": {"RestrictionText": "Closed", "TravelDirection": "Both"},
            "RestrictionTwo": {"RestrictionText": None, "TravelDirection": None},
        },
    ]


@pytest.fixture
def sample_cameras():
    """Sample camera data from WSDOT API."""
    return [
        {
            "CameraID": 1001,
            "Title": "I-5 at Tumwater",
            "Description": "Looking north on I-5",
            "ImageURL": "https://images.wsdot.wa.gov/nw/005vc06200.jpg",
            "DisplayLatitude": 47.01,
            "DisplayLongitude": -122.90,
            "IsActive": True,
            "Region": "SWR",
            "CameraOwner": "WSDOT",
            "OwnerURL": "https://wsdot.wa.gov",
            "CameraLocation": {
                "RoadName": "I-5",
                "Direction": "N",
                "MilePost": 102.5,
            },
        },
        {
            "CameraID": 1002,
            "Title": "I-5 at Spokane",
            "Description": "Looking north in Spokane area",
            "ImageURL": "https://images.wsdot.wa.gov/nw/005vc99999.jpg",
            "DisplayLatitude": 47.66,
            "DisplayLongitude": -117.42,
            "IsActive": True,
            "Region": "ER",
            "CameraOwner": "WSDOT",
            "OwnerURL": None,
            "CameraLocation": {
                "RoadName": "I-5",
                "Direction": "N",
                "MilePost": 280.0,
            },
        },
        {
            "CameraID": 1003,
            "Title": "Airport Camera A",
            "Description": "Airport terminal view",
            "ImageURL": "https://images.wsdot.wa.gov/nw/airport.jpg",
            "DisplayLatitude": 47.45,
            "DisplayLongitude": -122.31,
            "IsActive": True,
            "Region": "NWR",
            "CameraOwner": "Port of Seattle",
            "OwnerURL": None,
            "CameraLocation": {
                "RoadName": "Airports",
                "Direction": "",
                "MilePost": 0,
            },
        },
        {
            "CameraID": 1004,
            "Title": "Inactive Camera",
            "Description": "Decommissioned camera",
            "ImageURL": None,
            "DisplayLatitude": 47.10,
            "DisplayLongitude": -122.80,
            "IsActive": False,
            "Region": "SWR",
            "CameraOwner": "WSDOT",
            "OwnerURL": None,
            "CameraLocation": {
                "RoadName": "I-5",
                "Direction": "S",
                "MilePost": 110.0,
            },
        },
    ]


@pytest.fixture
def sample_flow_data():
    """Sample flow station data."""
    return [
        {
            "FlowStationID": 501,
            "StationName": "I-5 at Mounts Rd",
            "RoadName": "005",
            "Direction": "N",
            "Latitude": 47.05,
            "Longitude": -122.75,
            "FlowCount": 42,
            "FlowReadingValue": 1200,
            "CongestionCategory": "Free Flow",
        },
        {
            "FlowStationID": 502,
            "StationName": "SR-167 at Puyallup",
            "RoadName": "167",
            "Direction": "S",
            "Latitude": 47.18,
            "Longitude": -122.40,
            "FlowCount": 85,
            "FlowReadingValue": 900,
            "CongestionCategory": "Moderate",
        },
        {
            "FlowStationID": 503,
            "StationName": "US-2 at Spokane",
            "RoadName": "002",
            "Direction": "W",
            "Latitude": 47.66,
            "Longitude": -117.42,
            "FlowCount": 20,
            "FlowReadingValue": 1500,
            "CongestionCategory": "Free Flow",
        },
    ]


@pytest.fixture
def full_coordinator_data(
    sample_travel_times, sample_pass_conditions, sample_cameras, sample_flow_data
):
    """Complete dataset as returned by the coordinator (before filtering)."""
    return {
        "travel_times": sample_travel_times,
        "pass_conditions": sample_pass_conditions,
        "cameras": sample_cameras,
        "flow": sample_flow_data,
    }
