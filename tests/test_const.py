"""Tests for the WSDOT const module."""
from __future__ import annotations

from custom_components.wsdot.const import (
    ATTRIBUTION,
    CAMERAS_URL,
    CONF_API_KEY,
    DATA_CAMERAS,
    DATA_FLOW,
    DATA_PASS_CONDITIONS,
    DATA_TRAVEL_TIMES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FLOW_DATA_URL,
    LOCAL_BBOX,
    LOCAL_PASS_IDS,
    LOCAL_ROAD_NAMES,
    PASS_CONDITIONS_URL,
    PLATFORMS,
    TRAVEL_TIMES_URL,
    WSDOT_API_BASE,
)


class TestDomainConstants:
    """Tests for domain-level constants."""

    def test_domain(self):
        assert DOMAIN == "wsdot"

    def test_conf_api_key(self):
        assert CONF_API_KEY == "api_key"

    def test_default_scan_interval(self):
        assert DEFAULT_SCAN_INTERVAL == 60
        assert isinstance(DEFAULT_SCAN_INTERVAL, int)


class TestURLConstants:
    """Tests for API URL constants."""

    def test_api_base_url(self):
        assert WSDOT_API_BASE == "https://wsdot.wa.gov/Traffic/api"

    def test_travel_times_url_has_placeholder(self):
        assert "{api_key}" in TRAVEL_TIMES_URL

    def test_pass_conditions_url_has_placeholder(self):
        assert "{api_key}" in PASS_CONDITIONS_URL

    def test_cameras_url_has_placeholder(self):
        assert "{api_key}" in CAMERAS_URL

    def test_flow_data_url_has_placeholder(self):
        assert "{api_key}" in FLOW_DATA_URL

    def test_travel_times_url_format(self):
        url = TRAVEL_TIMES_URL.format(api_key="TESTKEY")
        assert "TESTKEY" in url
        assert "TravelTimes" in url

    def test_pass_conditions_url_format(self):
        url = PASS_CONDITIONS_URL.format(api_key="TESTKEY")
        assert "TESTKEY" in url
        assert "MountainPassConditions" in url

    def test_cameras_url_format(self):
        url = CAMERAS_URL.format(api_key="TESTKEY")
        assert "TESTKEY" in url
        assert "HighwayCameras" in url

    def test_flow_data_url_format(self):
        url = FLOW_DATA_URL.format(api_key="TESTKEY")
        assert "TESTKEY" in url
        assert "FlowData" in url


class TestDataKeys:
    """Tests for data key constants."""

    def test_data_keys_are_strings(self):
        assert isinstance(DATA_TRAVEL_TIMES, str)
        assert isinstance(DATA_PASS_CONDITIONS, str)
        assert isinstance(DATA_CAMERAS, str)
        assert isinstance(DATA_FLOW, str)

    def test_data_keys_unique(self):
        keys = [DATA_TRAVEL_TIMES, DATA_PASS_CONDITIONS, DATA_CAMERAS, DATA_FLOW]
        assert len(keys) == len(set(keys))


class TestLocalBbox:
    """Tests for the local bounding box constants."""

    def test_bbox_has_required_keys(self):
        assert "lat_min" in LOCAL_BBOX
        assert "lat_max" in LOCAL_BBOX
        assert "lon_min" in LOCAL_BBOX
        assert "lon_max" in LOCAL_BBOX

    def test_bbox_lat_range_valid(self):
        assert LOCAL_BBOX["lat_min"] < LOCAL_BBOX["lat_max"]

    def test_bbox_lon_range_valid(self):
        assert LOCAL_BBOX["lon_min"] < LOCAL_BBOX["lon_max"]

    def test_bbox_covers_olympia(self):
        # Olympia, WA is approximately 47.04°N, -122.90°W
        assert LOCAL_BBOX["lat_min"] <= 47.04 <= LOCAL_BBOX["lat_max"]
        assert LOCAL_BBOX["lon_min"] <= -122.90 <= LOCAL_BBOX["lon_max"]

    def test_bbox_values_are_floats(self):
        for v in LOCAL_BBOX.values():
            assert isinstance(v, float)


class TestLocalRoadNames:
    """Tests for local road name filter."""

    def test_includes_i5(self):
        assert "005" in LOCAL_ROAD_NAMES

    def test_includes_i90(self):
        assert "090" in LOCAL_ROAD_NAMES

    def test_includes_sr520(self):
        assert "520" in LOCAL_ROAD_NAMES

    def test_is_a_set(self):
        assert isinstance(LOCAL_ROAD_NAMES, set)

    def test_minimum_roads(self):
        assert len(LOCAL_ROAD_NAMES) >= 5


class TestLocalPassIds:
    """Tests for local pass ID filter."""

    def test_includes_snoqualmie(self):
        assert 11 in LOCAL_PASS_IDS

    def test_includes_stevens(self):
        assert 10 in LOCAL_PASS_IDS

    def test_includes_white_pass(self):
        assert 12 in LOCAL_PASS_IDS

    def test_is_a_set(self):
        assert isinstance(LOCAL_PASS_IDS, set)


class TestPlatforms:
    """Tests for platform list."""

    def test_platforms_is_list(self):
        assert isinstance(PLATFORMS, list)

    def test_platforms_content(self):
        assert set(PLATFORMS) == {"sensor", "camera", "binary_sensor"}


class TestAttribution:
    """Tests for attribution constant."""

    def test_attribution_mentions_wsdot(self):
        assert "WSDOT" in ATTRIBUTION
