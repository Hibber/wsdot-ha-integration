"""Tests for the WSDOT binary_sensor module."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.wsdot.binary_sensor import (
    WSDOTCongestionBinarySensor,
    WSDOTPassAdvisoryBinarySensor,
)
from custom_components.wsdot.const import DATA_PASS_CONDITIONS, DATA_TRAVEL_TIMES


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

    coord.get_pass = get_pass
    coord.get_travel_time = get_travel_time
    return coord


# ---------------------------------------------------------------------------
# WSDOTPassAdvisoryBinarySensor
# ---------------------------------------------------------------------------


class TestPassAdvisoryBinarySensor:
    """Tests for the pass advisory binary sensor."""

    def test_advisory_active(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 11)
        assert sensor.is_on is True

    def test_advisory_inactive(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 10)
        assert sensor.is_on is False

    def test_advisory_missing_field(self):
        """When TravelAdvisoryActive is missing, defaults to False."""
        data = {DATA_PASS_CONDITIONS: [{"MountainPassId": 1, "MountainPassName": "Test"}]}
        coord = _mock_coordinator(data)
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_advisory_record_not_found(self):
        """When pass record is not found, is_on returns False."""
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: []})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 999)
        assert sensor.is_on is False

    def test_unique_id(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 11)
        assert sensor._attr_unique_id == "wsdot_pass_11_advisory"

    def test_name(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 11)
        assert sensor._attr_name == "Travel Advisory Active"

    def test_extra_state_attributes_with_advisory(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 11)
        attrs = sensor.extra_state_attributes
        assert attrs["pass_name"] == "Snoqualmie Pass"
        assert attrs["restriction_one"] == "Chains required"
        assert "road_condition" in attrs

    def test_extra_state_attributes_no_restrictions(self, sample_pass_conditions):
        coord = _mock_coordinator({DATA_PASS_CONDITIONS: sample_pass_conditions})
        sensor = WSDOTPassAdvisoryBinarySensor(coord, 10)
        attrs = sensor.extra_state_attributes
        assert attrs["pass_name"] == "Stevens Pass"
        # None values are filtered out
        assert "restriction_one" not in attrs


# ---------------------------------------------------------------------------
# WSDOTCongestionBinarySensor
# ---------------------------------------------------------------------------


class TestCongestionBinarySensor:
    """Tests for the congestion binary sensor."""

    def test_congested_above_threshold(self):
        """Current > 1.25 * average => congested."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 20,
                    "CurrentTime": 30,  # 30/20 = 1.5 > 1.25
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is True

    def test_not_congested_below_threshold(self):
        """Current <= 1.25 * average => not congested."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 20,
                    "CurrentTime": 22,  # 22/20 = 1.1 < 1.25
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_exactly_at_threshold(self):
        """Current == 1.25 * average => not congested (needs to EXCEED)."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 20,
                    "CurrentTime": 25,  # 25/20 = 1.25, not > 1.25
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_just_above_threshold(self):
        """Current just barely > 1.25 * average."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 100,
                    "CurrentTime": 126,  # 1.26 > 1.25
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is True

    def test_zero_average_time(self):
        """Zero average time should not cause division by zero."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 0,
                    "CurrentTime": 30,
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_zero_current_time(self):
        """Zero current time means no congestion."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 20,
                    "CurrentTime": 0,
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_missing_average_time(self):
        """Missing AverageTime field defaults to no congestion."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "CurrentTime": 30,
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_missing_current_time(self):
        """Missing CurrentTime field defaults to no congestion."""
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 20,
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        assert sensor.is_on is False

    def test_record_not_found(self):
        """Returns False when no record found."""
        coord = _mock_coordinator({DATA_TRAVEL_TIMES: []})
        sensor = WSDOTCongestionBinarySensor(coord, 999)
        assert sensor.is_on is False

    def test_unique_id(self):
        data = {
            DATA_TRAVEL_TIMES: [
                {"TravelTimeID": 42, "Name": "Route 42", "AverageTime": 10, "CurrentTime": 10}
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 42)
        assert sensor._attr_unique_id == "wsdot_tt_42_congestion"

    def test_extra_state_attributes(self):
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "Description": "A test route",
                    "AverageTime": 20,
                    "CurrentTime": 30,
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        attrs = sensor.extra_state_attributes
        assert attrs["current_time_minutes"] == 30
        assert attrs["average_time_minutes"] == 20
        assert attrs["delay_minutes"] == 10
        assert attrs["congestion_ratio"] == 1.5
        assert attrs["route_name"] == "Test Route"

    def test_extra_state_attributes_no_congestion(self):
        data = {
            DATA_TRAVEL_TIMES: [
                {
                    "TravelTimeID": 1,
                    "Name": "Test Route",
                    "AverageTime": 20,
                    "CurrentTime": 20,
                }
            ]
        }
        coord = _mock_coordinator(data)
        sensor = WSDOTCongestionBinarySensor(coord, 1)
        attrs = sensor.extra_state_attributes
        assert attrs["delay_minutes"] == 0
        assert attrs["congestion_ratio"] == 1.0

    def test_threshold_constant(self):
        assert WSDOTCongestionBinarySensor.CONGESTION_THRESHOLD == 1.25
