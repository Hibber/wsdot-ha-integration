"""Tests for the WSDOT sensor module."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.wsdot.const import (
    DATA_FLOW,
    DATA_PASS_CONDITIONS,
    DATA_TRAVEL_TIMES,
)
from custom_components.wsdot.sensor import (
    WSDOTFlowSensor,
    WSDOTPassConditionSensor,
    WSDOTPassTemperatureSensor,
    WSDOTTravelTimeSensor,
)


# ---------------------------------------------------------------------------
# Helper to build a mock coordinator
# ---------------------------------------------------------------------------


def _mock_coordinator(data):
    """Build a mock coordinator with data and lookup methods."""
    from custom_components.wsdot.coordinator import WSDOTDataUpdateCoordinator

    coord = MagicMock(spec=WSDOTDataUpdateCoordinator)
    coord.data = data

    def get_pass(pass_id):
        for rec in data.get(DATA_PASS_CONDITIONS, []):
            if rec.get("MountainPassId") == pass_id:
                return rec
        return None

    def get_travel_time(tt_id):
        for rec in data.get(DATA_TRAVEL_TIMES, []):
            if rec.get("TravelTimeID") == tt_id:
                return rec
        return None

    def get_flow_station(station_id):
        for rec in data.get(DATA_FLOW, []):
            if rec.get("FlowStationID") == station_id:
                return rec
        return None

    coord.get_pass = get_pass
    coord.get_travel_time = get_travel_time
    coord.get_flow_station = get_flow_station
    return coord


# ---------------------------------------------------------------------------
# WSDOTTravelTimeSensor
# ---------------------------------------------------------------------------


class TestTravelTimeSensor:
    """Tests for travel time sensors."""

    def test_current_travel_time(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "current")
        assert sensor.native_value == 35

    def test_average_travel_time(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "average")
        assert sensor.native_value == 28

    def test_travel_time_none_when_missing(self):
        """Returns None when the value field is missing."""
        data = {DATA_TRAVEL_TIMES: [{"TravelTimeID": 1, "Name": "Test"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTTravelTimeSensor(coord, 1, "current")
        assert sensor.native_value is None

    def test_travel_time_record_not_found(self):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: []})
        sensor = WSDOTTravelTimeSensor(coord, 999, "current")
        assert sensor.native_value is None

    def test_unique_id_current(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "current")
        assert sensor._attr_unique_id == "wsdot_tt_101_current"

    def test_unique_id_average(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "average")
        assert sensor._attr_unique_id == "wsdot_tt_101_average"

    def test_name_current(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "current")
        assert sensor._attr_name == "Current Travel Time"

    def test_name_average(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "average")
        assert sensor._attr_name == "Average Travel Time"

    def test_extra_state_attributes_current(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "current")
        attrs = sensor.extra_state_attributes
        assert attrs["travel_time_id"] == 101
        assert attrs["distance_miles"] == 30.5
        assert attrs["road_name"] == "005"
        assert attrs["direction"] == "N"
        assert attrs["start_description"] == "Olympia"
        assert attrs["end_description"] == "Tacoma"
        # Congestion attributes present for "current" kind
        assert attrs["congestion_ratio"] == round(35 / 28, 2)
        assert attrs["delay_minutes"] == 7

    def test_extra_state_attributes_average_no_congestion_fields(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "average")
        attrs = sensor.extra_state_attributes
        assert "congestion_ratio" not in attrs
        assert "delay_minutes" not in attrs

    def test_extra_state_attributes_last_updated(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 101, "current")
        attrs = sensor.extra_state_attributes
        assert "last_updated" in attrs

    def test_extra_state_attributes_no_time_updated(self, sample_travel_times):
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: sample_travel_times})
        sensor = WSDOTTravelTimeSensor(coord, 303, "current")
        attrs = sensor.extra_state_attributes
        assert "last_updated" not in attrs

    def test_extra_state_attributes_filters_none(self):
        data = {DATA_TRAVEL_TIMES: [{"TravelTimeID": 1, "Name": "Sparse"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTTravelTimeSensor(coord, 1, "average")
        attrs = sensor.extra_state_attributes
        for v in attrs.values():
            assert v is not None


# ---------------------------------------------------------------------------
# WSDOTPassConditionSensor
# ---------------------------------------------------------------------------


class TestPassConditionSensor:
    """Tests for mountain pass condition sensors."""

    def test_road_condition(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassConditionSensor(coord, 11)
        assert sensor.native_value == "Wet, chains required for all vehicles."

    def test_road_condition_bare(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassConditionSensor(coord, 10)
        assert sensor.native_value == "Bare and dry."

    def test_road_condition_missing_returns_unknown(self):
        data = {DATA_PASS_CONDITIONS: [{"MountainPassId": 1, "MountainPassName": "Test"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTPassConditionSensor(coord, 1)
        assert sensor.native_value == "Unknown"

    def test_road_condition_truncated_at_255(self):
        """Long road condition strings are truncated to 255 chars."""
        long_condition = "A" * 300
        data = {
            DATA_PASS_CONDITIONS: [
                {"MountainPassId": 1, "MountainPassName": "Test", "RoadCondition": long_condition}
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTPassConditionSensor(coord, 1)
        assert len(sensor.native_value) == 255

    def test_record_not_found(self):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: []})
        sensor = WSDOTPassConditionSensor(coord, 999)
        assert sensor.native_value == "Unknown"

    def test_unique_id(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassConditionSensor(coord, 11)
        assert sensor._attr_unique_id == "wsdot_pass_11_condition"

    def test_name(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassConditionSensor(coord, 11)
        assert sensor._attr_name == "Road Condition"

    def test_extra_state_attributes(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassConditionSensor(coord, 11)
        attrs = sensor.extra_state_attributes
        assert attrs["pass_id"] == 11
        assert attrs["pass_name"] == "Snoqualmie Pass"
        assert attrs["weather_condition"] == "Snowing"
        assert attrs["elevation_feet"] == 3022
        assert attrs["restriction_one"] == "Chains required"
        assert attrs["restriction_one_direction"] == "Both"
        assert "last_updated" in attrs

    def test_extra_state_attributes_filters_none(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassConditionSensor(coord, 10)
        attrs = sensor.extra_state_attributes
        for v in attrs.values():
            assert v is not None


# ---------------------------------------------------------------------------
# WSDOTPassTemperatureSensor
# ---------------------------------------------------------------------------


class TestPassTemperatureSensor:
    """Tests for mountain pass temperature sensors."""

    def test_temperature_value(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassTemperatureSensor(coord, 11)
        assert sensor.native_value == 28.0

    def test_temperature_value_different_pass(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassTemperatureSensor(coord, 10)
        assert sensor.native_value == 45.0

    def test_temperature_none_when_missing(self):
        data = {DATA_PASS_CONDITIONS: [{"MountainPassId": 1, "MountainPassName": "Test"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTPassTemperatureSensor(coord, 1)
        assert sensor.native_value is None

    def test_record_not_found(self):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: []})
        sensor = WSDOTPassTemperatureSensor(coord, 999)
        assert sensor.native_value is None

    def test_unique_id(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassTemperatureSensor(coord, 11)
        assert sensor._attr_unique_id == "wsdot_pass_11_temperature"

    def test_name(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassTemperatureSensor(coord, 11)
        assert sensor._attr_name == "Temperature"

    def test_temperature_returns_float(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassTemperatureSensor(coord, 11)
        assert isinstance(sensor.native_value, float)


# ---------------------------------------------------------------------------
# WSDOTFlowSensor
# ---------------------------------------------------------------------------


class TestFlowSensor:
    """Tests for traffic flow sensors."""

    def test_flow_count_from_FlowCount_field(self, sample_flow_data):
        coord = _mock_coordinator({DATA_FLOW: sample_flow_data})
        sensor = WSDOTFlowSensor(coord, 501)
        assert sensor.native_value == 42

    def test_flow_count_fallback_to_Count(self):
        data = {DATA_FLOW: [{"FlowStationID": 1, "StationName": "Test", "Count": 55}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTFlowSensor(coord, 1)
        assert sensor.native_value == 55

    def test_flow_count_fallback_to_Volume(self):
        data = {DATA_FLOW: [{"FlowStationID": 1, "StationName": "Test", "Volume": 77}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTFlowSensor(coord, 1)
        assert sensor.native_value == 77

    def test_flow_count_none_when_no_field(self):
        data = {DATA_FLOW: [{"FlowStationID": 1, "StationName": "Test"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTFlowSensor(coord, 1)
        assert sensor.native_value is None

    def test_flow_count_prefers_FlowCount_over_Count(self):
        data = {
            DATA_FLOW: [
                {"FlowStationID": 1, "StationName": "Test", "FlowCount": 10, "Count": 20}
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTFlowSensor(coord, 1)
        assert sensor.native_value == 10

    def test_record_not_found(self):
        coord = _mock_coordinator({DATA_FLOW: []})
        sensor = WSDOTFlowSensor(coord, 999)
        assert sensor.native_value is None

    def test_unique_id(self, sample_flow_data):
        coord = _mock_coordinator({DATA_FLOW: sample_flow_data})
        sensor = WSDOTFlowSensor(coord, 501)
        assert sensor._attr_unique_id == "wsdot_flow_501"

    def test_name(self, sample_flow_data):
        coord = _mock_coordinator({DATA_FLOW: sample_flow_data})
        sensor = WSDOTFlowSensor(coord, 501)
        assert sensor._attr_name == "Flow Count"

    def test_extra_state_attributes(self, sample_flow_data):
        coord = _mock_coordinator({DATA_FLOW: sample_flow_data})
        sensor = WSDOTFlowSensor(coord, 501)
        attrs = sensor.extra_state_attributes
        assert attrs["station_id"] == 501
        assert attrs["station_name"] == "I-5 at Mounts Rd"
        assert attrs["road_name"] == "005"
        assert attrs["direction"] == "N"
        assert attrs["congestion_category"] == "Free Flow"

    def test_extra_state_attributes_filters_none(self):
        data = {DATA_FLOW: [{"FlowStationID": 1, "StationName": "Test"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTFlowSensor(coord, 1)
        attrs = sensor.extra_state_attributes
        for v in attrs.values():
            assert v is not None
