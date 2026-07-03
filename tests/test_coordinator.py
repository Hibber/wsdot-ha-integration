"""Tests for the WSDOT coordinator module."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.wsdot.const import (
    DATA_CAMERAS,
    DATA_FLOW,
    DATA_PASS_CONDITIONS,
    DATA_TRAVEL_TIMES,
    LOCAL_BBOX,
    LOCAL_PASS_IDS,
)
from custom_components.wsdot.coordinator import (
    WSDOTDataUpdateCoordinator,
    parse_wsdot_date,
)


# ---------------------------------------------------------------------------
# parse_wsdot_date
# ---------------------------------------------------------------------------


class TestParseWsdotDate:
    """Tests for the parse_wsdot_date utility."""

    def test_valid_date_with_offset(self):
        result = parse_wsdot_date("/Date(1688400000000-0700)/")
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        # 1688400000000 ms = 1688400000 s epoch
        expected = datetime.fromtimestamp(1688400000, tz=timezone.utc)
        assert result == expected

    def test_valid_date_without_offset(self):
        result = parse_wsdot_date("/Date(1688400000000)/")
        assert result is not None
        expected = datetime.fromtimestamp(1688400000, tz=timezone.utc)
        assert result == expected

    def test_valid_date_positive_offset(self):
        result = parse_wsdot_date("/Date(1688400000000+0530)/")
        assert result is not None
        expected = datetime.fromtimestamp(1688400000, tz=timezone.utc)
        assert result == expected

    def test_zero_epoch(self):
        result = parse_wsdot_date("/Date(0)/")
        assert result is not None
        expected = datetime.fromtimestamp(0, tz=timezone.utc)
        assert result == expected

    def test_negative_epoch(self):
        result = parse_wsdot_date("/Date(-1000)/")
        assert result is not None
        expected = datetime.fromtimestamp(-1, tz=timezone.utc)
        assert result == expected

    def test_none_input(self):
        assert parse_wsdot_date(None) is None

    def test_empty_string(self):
        assert parse_wsdot_date("") is None

    def test_invalid_format(self):
        assert parse_wsdot_date("2023-07-03T12:00:00Z") is None

    def test_malformed_date_string(self):
        assert parse_wsdot_date("/Date(abc)/") is None

    def test_partial_match(self):
        assert parse_wsdot_date("prefix/Date(1000)/suffix") is None


# ---------------------------------------------------------------------------
# _in_bbox
# ---------------------------------------------------------------------------


class TestInBbox:
    """Tests for the _in_bbox static method."""

    def test_point_inside_bbox(self):
        # Olympia: ~47.04°N, -122.9°W — inside the local bbox
        assert WSDOTDataUpdateCoordinator._in_bbox(47.04, -122.90) is True

    def test_point_outside_bbox_south(self):
        # South of bbox
        assert WSDOTDataUpdateCoordinator._in_bbox(46.5, -122.90) is False

    def test_point_outside_bbox_north(self):
        # North of bbox
        assert WSDOTDataUpdateCoordinator._in_bbox(48.0, -122.90) is False

    def test_point_outside_bbox_east(self):
        # East of bbox (Spokane area)
        assert WSDOTDataUpdateCoordinator._in_bbox(47.04, -117.42) is False

    def test_point_outside_bbox_west(self):
        # West of bbox
        assert WSDOTDataUpdateCoordinator._in_bbox(47.04, -124.0) is False

    def test_point_on_boundary_lat_min(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(
            LOCAL_BBOX["lat_min"], -122.5
        ) is True

    def test_point_on_boundary_lat_max(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(
            LOCAL_BBOX["lat_max"], -122.5
        ) is True

    def test_point_on_boundary_lon_min(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(
            47.0, LOCAL_BBOX["lon_min"]
        ) is True

    def test_point_on_boundary_lon_max(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(
            47.0, LOCAL_BBOX["lon_max"]
        ) is True

    def test_none_lat(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(None, -122.90) is False

    def test_none_lon(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(47.04, None) is False

    def test_both_none(self):
        assert WSDOTDataUpdateCoordinator._in_bbox(None, None) is False


# ---------------------------------------------------------------------------
# _filter_local_data
# ---------------------------------------------------------------------------


class TestFilterLocalData:
    """Tests for the _filter_local_data static method."""

    def test_filters_travel_times_by_bbox(self, full_coordinator_data):
        result = WSDOTDataUpdateCoordinator._filter_local_data(full_coordinator_data)
        tt_ids = [r["TravelTimeID"] for r in result[DATA_TRAVEL_TIMES]]
        # Route 101 (Olympia) is in bbox, Route 202 (SR-520) has road in LOCAL_ROAD_NAMES
        assert 101 in tt_ids
        assert 202 in tt_ids
        # Route 303 (Spokane, road "002") is NOT in bbox and road not in LOCAL_ROAD_NAMES
        assert 303 not in tt_ids

    def test_filters_travel_times_by_road_name(self, sample_travel_times):
        """A route outside bbox but on a LOCAL_ROAD_NAME is kept."""
        data = {
            DATA_TRAVEL_TIMES: sample_travel_times,
            DATA_PASS_CONDITIONS: [],
            DATA_CAMERAS: [],
            DATA_FLOW: [],
        }
        result = WSDOTDataUpdateCoordinator._filter_local_data(data)
        tt_ids = [r["TravelTimeID"] for r in result[DATA_TRAVEL_TIMES]]
        # 202 has road "520" which is in LOCAL_ROAD_NAMES
        assert 202 in tt_ids

    def test_filters_pass_conditions_by_id(self, full_coordinator_data):
        result = WSDOTDataUpdateCoordinator._filter_local_data(full_coordinator_data)
        pass_ids = [r["MountainPassId"] for r in result[DATA_PASS_CONDITIONS]]
        # Snoqualmie(11) and Stevens(10) are in LOCAL_PASS_IDS
        assert 11 in pass_ids
        assert 10 in pass_ids
        # Remote Pass (99) is NOT in LOCAL_PASS_IDS
        assert 99 not in pass_ids

    def test_filters_cameras_by_bbox(self, full_coordinator_data):
        result = WSDOTDataUpdateCoordinator._filter_local_data(full_coordinator_data)
        cam_ids = [r["CameraID"] for r in result[DATA_CAMERAS]]
        # Camera 1001 (Tumwater) is in bbox
        assert 1001 in cam_ids
        # Camera 1002 (Spokane) is outside bbox
        assert 1002 not in cam_ids

    def test_filters_flow_by_bbox(self, full_coordinator_data):
        result = WSDOTDataUpdateCoordinator._filter_local_data(full_coordinator_data)
        flow_ids = [r["FlowStationID"] for r in result[DATA_FLOW]]
        # Station 501 (Mounts Rd near Olympia) and 502 (Puyallup) are in bbox
        assert 501 in flow_ids
        assert 502 in flow_ids
        # Station 503 (Spokane) is outside bbox
        assert 503 not in flow_ids

    def test_empty_data(self):
        data = {
            DATA_TRAVEL_TIMES: [],
            DATA_PASS_CONDITIONS: [],
            DATA_CAMERAS: [],
            DATA_FLOW: [],
        }
        result = WSDOTDataUpdateCoordinator._filter_local_data(data)
        assert result[DATA_TRAVEL_TIMES] == []
        assert result[DATA_PASS_CONDITIONS] == []
        assert result[DATA_CAMERAS] == []
        assert result[DATA_FLOW] == []

    def test_missing_coordinates_excluded(self):
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 999,
                    "StartPoint": {"Latitude": None, "Longitude": None, "RoadName": "999"},
                    "EndPoint": {"Latitude": None, "Longitude": None, "RoadName": "999"},
                }
            ],
            DATA_PASS_CONDITIONS: [],
            DATA_CAMERAS: [
                {"CameraID": 9999, "DisplayLatitude": None, "DisplayLongitude": None}
            ],
            DATA_FLOW: [
                {"FlowStationID": 9999, "Latitude": None, "Longitude": None}
            ],
        }
        result = WSDOTDataUpdateCoordinator._filter_local_data(data)
        assert result[DATA_TRAVEL_TIMES] == []
        assert result[DATA_CAMERAS] == []
        assert result[DATA_FLOW] == []


# ---------------------------------------------------------------------------
# Convenience lookups
# ---------------------------------------------------------------------------


class TestConvenienceLookups:
    """Tests for get_travel_time, get_pass, get_camera, get_flow_station."""

    def _make_coordinator(self, data):
        """Create a coordinator instance with pre-set data."""
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"api_key": "test_key"}
        entry.options = {}
        coord = WSDOTDataUpdateCoordinator(hass, entry)
        coord.data = data
        return coord

    def test_get_travel_time_found(self, sample_travel_times):
        coord = self._make_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        result = coord.get_travel_time(101)
        assert result is not None
        assert result["Name"] == "I-5 Olympia to Tacoma"

    def test_get_travel_time_not_found(self, sample_travel_times):
        coord = self._make_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        assert coord.get_travel_time(9999) is None

    def test_get_travel_time_no_data(self):
        coord = self._make_coordinator(None)
        assert coord.get_travel_time(101) is None

    def test_get_pass_found(self, sample_pass_conditions):
        coord = self._make_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        result = coord.get_pass(11)
        assert result is not None
        assert result["MountainPassName"] == "Snoqualmie Pass"

    def test_get_pass_not_found(self, sample_pass_conditions):
        coord = self._make_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        assert coord.get_pass(9999) is None

    def test_get_pass_no_data(self):
        coord = self._make_coordinator(None)
        assert coord.get_pass(11) is None

    def test_get_camera_found(self, sample_cameras):
        coord = self._make_coordinator({DATA_CAMERAS: sample_cameras})
        result = coord.get_camera(1001)
        assert result is not None
        assert result["Title"] == "I-5 at Tumwater"

    def test_get_camera_not_found(self, sample_cameras):
        coord = self._make_coordinator({DATA_CAMERAS: sample_cameras})
        assert coord.get_camera(9999) is None

    def test_get_camera_no_data(self):
        coord = self._make_coordinator(None)
        assert coord.get_camera(1001) is None

    def test_get_flow_station_found(self, sample_flow_data):
        coord = self._make_coordinator({DATA_FLOW: sample_flow_data})
        result = coord.get_flow_station(501)
        assert result is not None
        assert result["StationName"] == "I-5 at Mounts Rd"

    def test_get_flow_station_not_found(self, sample_flow_data):
        coord = self._make_coordinator({DATA_FLOW: sample_flow_data})
        assert coord.get_flow_station(9999) is None

    def test_get_flow_station_no_data(self):
        coord = self._make_coordinator(None)
        assert coord.get_flow_station(501) is None

    def test_get_travel_time_empty_list(self):
        coord = self._make_coordinator({DATA_TRAVEL_TIMES: []})
        assert coord.get_travel_time(101) is None


# ---------------------------------------------------------------------------
# _async_update_data
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Fake aiohttp response as async context manager."""

    def __init__(self, json_data=None, status=200, raise_on_status=False):
        self._json_data = json_data
        self.status = status
        self._raise_on_status = raise_on_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        if self._raise_on_status:
            raise Exception(f"HTTP {self.status}")

    async def json(self, content_type=None):
        return self._json_data


class _FakeSession:
    """Fake aiohttp ClientSession with controllable get() responses."""

    def __init__(self, responses=None, error=None):
        self._responses = responses or []
        self._error = error
        self._call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def get(self, url, **kwargs):
        if self._error:
            return _FakeErrorContextManager(self._error)
        idx = self._call_count
        self._call_count += 1
        if idx < len(self._responses):
            return _FakeResponse(json_data=self._responses[idx])
        return _FakeResponse(json_data=[])


class _FakeErrorContextManager:
    """Context manager that raises on entry."""

    def __init__(self, error):
        self._error = error

    async def __aenter__(self):
        raise self._error

    async def __aexit__(self, *args):
        pass


class TestAsyncUpdateData:
    """Tests for the _async_update_data method."""

    def _make_coordinator(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"api_key": "test_key_123"}
        entry.options = {"scan_interval": 120}
        return WSDOTDataUpdateCoordinator(hass, entry)

    @pytest.mark.asyncio
    async def test_successful_fetch(self, full_coordinator_data):
        coord = self._make_coordinator()
        travel_times = full_coordinator_data[DATA_TRAVEL_TIMES]
        passes = full_coordinator_data[DATA_PASS_CONDITIONS]
        cameras = full_coordinator_data[DATA_CAMERAS]
        flow = full_coordinator_data[DATA_FLOW]

        fake_session = _FakeSession(responses=[travel_times, passes, cameras, flow])

        with patch("aiohttp.ClientSession", return_value=fake_session):
            result = await coord._async_update_data()

        # Should have filtered data
        assert DATA_TRAVEL_TIMES in result
        assert DATA_PASS_CONDITIONS in result
        assert DATA_CAMERAS in result
        assert DATA_FLOW in result
        # Verify filtering worked: pass 99 should be excluded
        pass_ids = [r["MountainPassId"] for r in result[DATA_PASS_CONDITIONS]]
        assert 99 not in pass_ids

    @pytest.mark.asyncio
    async def test_update_failed_when_no_data(self):
        """Raises UpdateFailed when both travel times and passes are empty."""
        from custom_components.wsdot.coordinator import UpdateFailed

        coord = self._make_coordinator()

        fake_session = _FakeSession(responses=[[], [], [], []])

        with patch("aiohttp.ClientSession", return_value=fake_session):
            with pytest.raises(UpdateFailed):
                await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_fetch_error_returns_empty_lists(self):
        """When _fetch_json catches errors (returns None), data becomes []."""
        from custom_components.wsdot.coordinator import UpdateFailed

        coord = self._make_coordinator()
        fake_session = _FakeSession(error=Exception("Network error"))

        with patch("aiohttp.ClientSession", return_value=fake_session):
            # All fetches fail → both travel_times and passes are empty → UpdateFailed
            with pytest.raises(UpdateFailed):
                await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_partial_fetch_success(self, sample_pass_conditions):
        """When some fetches succeed, the result includes that data."""
        coord = self._make_coordinator()
        # Only passes succeed; travel_times/cameras/flow return empty
        fake_session = _FakeSession(responses=[[], sample_pass_conditions, [], []])

        with patch("aiohttp.ClientSession", return_value=fake_session):
            result = await coord._async_update_data()

        # Pass data should be present (filtered to LOCAL_PASS_IDS)
        assert len(result[DATA_PASS_CONDITIONS]) > 0
        pass_ids = [r["MountainPassId"] for r in result[DATA_PASS_CONDITIONS]]
        assert 11 in pass_ids

    @pytest.mark.asyncio
    async def test_gather_exception_uses_cached_data(self, sample_travel_times):
        """When gather returns an Exception result, cached data is used."""
        coord = self._make_coordinator()
        coord.data = {
            DATA_TRAVEL_TIMES: sample_travel_times,
            DATA_PASS_CONDITIONS: [
                {"MountainPassId": 11, "MountainPassName": "Snoqualmie Pass"}
            ],
            DATA_CAMERAS: [],
            DATA_FLOW: [],
        }

        # Patch _fetch_json to raise (simulating gather with return_exceptions)
        async def _fetch_raising(session, url):
            raise RuntimeError("Simulated failure")

        coord._fetch_json = _fetch_raising

        fake_session = _FakeSession()
        with patch("aiohttp.ClientSession", return_value=fake_session):
            result = await coord._async_update_data()

        # Should have fallen back to cached data
        assert len(result[DATA_TRAVEL_TIMES]) > 0
        assert len(result[DATA_PASS_CONDITIONS]) == 1


# ---------------------------------------------------------------------------
# Coordinator initialization
# ---------------------------------------------------------------------------


class TestCoordinatorInit:
    """Tests for coordinator initialization."""

    def test_default_scan_interval(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"api_key": "key123"}
        entry.options = {}
        coord = WSDOTDataUpdateCoordinator(hass, entry)
        from datetime import timedelta

        assert coord.update_interval == timedelta(seconds=60)

    def test_custom_scan_interval(self):
        hass = MagicMock()
        entry = MagicMock()
        entry.data = {"api_key": "key123"}
        entry.options = {"scan_interval": 300}
        coord = WSDOTDataUpdateCoordinator(hass, entry)
        from datetime import timedelta

        assert coord.update_interval == timedelta(seconds=300)
