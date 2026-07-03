"""Tests for the WSDOT camera module."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.wsdot.camera import WSDOTCamera
from custom_components.wsdot.const import DATA_CAMERAS


# ---------------------------------------------------------------------------
# Helper to build a mock coordinator
# ---------------------------------------------------------------------------


def _mock_coordinator(data):
    """Build a mock coordinator with data and lookup methods."""
    from custom_components.wsdot.coordinator import WSDOTDataUpdateCoordinator

    coord = MagicMock(spec=WSDOTDataUpdateCoordinator)
    coord.data = data

    def get_camera(camera_id):
        for rec in data.get(DATA_CAMERAS, []):
            if rec.get("CameraID") == camera_id:
                return rec
        return None

    coord.get_camera = get_camera
    return coord


# ---------------------------------------------------------------------------
# WSDOTCamera entity properties
# ---------------------------------------------------------------------------


class TestWSDOTCameraProperties:
    """Tests for camera entity properties."""

    def test_unique_id(self, sample_cameras):
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        assert camera._attr_unique_id == "wsdot_camera_1001"

    def test_name(self, sample_cameras):
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        assert camera._attr_name == "I-5 at Tumwater"

    def test_name_fallback(self):
        data = {DATA_CAMERAS: [{"CameraID": 99}]}
        coord = _mock_coordinator(data)
        camera = WSDOTCamera(coord, 99)
        assert camera._attr_name == "Camera 99"

    def test_is_streaming(self, sample_cameras):
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        assert camera.is_streaming is False

    def test_extra_state_attributes(self, sample_cameras):
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        attrs = camera.extra_state_attributes
        assert attrs["camera_id"] == 1001
        assert attrs["title"] == "I-5 at Tumwater"
        assert attrs["image_url"] == "https://images.wsdot.wa.gov/nw/005vc06200.jpg"
        assert attrs["road_name"] == "I-5"
        assert attrs["direction"] == "N"
        assert attrs["latitude"] == 47.01
        assert attrs["longitude"] == -122.90
        assert attrs["is_active"] is True

    def test_extra_state_attributes_filters_none(self):
        data = {DATA_CAMERAS: [{"CameraID": 1, "Title": "Test"}]}
        coord = _mock_coordinator(data)
        camera = WSDOTCamera(coord, 1)
        attrs = camera.extra_state_attributes
        for v in attrs.values():
            assert v is not None

    def test_device_info_manufacturer(self, sample_cameras):
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        # Device info should have WSDOT as manufacturer
        assert camera._attr_device_info.manufacturer == "WSDOT"

    def test_device_info_manufacturer_fallback(self):
        data = {DATA_CAMERAS: [{"CameraID": 1, "Title": "Test", "CameraOwner": None}]}
        coord = _mock_coordinator(data)
        camera = WSDOTCamera(coord, 1)
        assert camera._attr_device_info.manufacturer == "WSDOT"


# ---------------------------------------------------------------------------
# async_camera_image
# ---------------------------------------------------------------------------


class TestAsyncCameraImage:
    """Tests for the image fetch logic."""

    @pytest.mark.asyncio
    async def test_successful_image_fetch(self, sample_cameras):
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        camera.hass = MagicMock()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n image data")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.camera.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await camera.async_camera_image()

        assert result == b"\x89PNG\r\n\x1a\n image data"
        assert camera._cached_image == result

    @pytest.mark.asyncio
    async def test_non_200_returns_cached(self, sample_cameras):
        """On non-200 response, returns cached image."""
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        camera.hass = MagicMock()
        camera._cached_image = b"cached_image_data"

        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.camera.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await camera.async_camera_image()

        assert result == b"cached_image_data"

    @pytest.mark.asyncio
    async def test_timeout_returns_cached(self, sample_cameras):
        """On timeout, returns cached image."""
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        camera.hass = MagicMock()
        camera._cached_image = b"old_cache"

        mock_session = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=mock_ctx)

        with patch(
            "custom_components.wsdot.camera.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await camera.async_camera_image()

        assert result == b"old_cache"

    @pytest.mark.asyncio
    async def test_client_error_returns_cached(self, sample_cameras):
        """On aiohttp.ClientError, returns cached image."""
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        camera.hass = MagicMock()
        camera._cached_image = b"cached"

        mock_session = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientError("Connection reset")
        )
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=mock_ctx)

        with patch(
            "custom_components.wsdot.camera.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await camera.async_camera_image()

        assert result == b"cached"

    @pytest.mark.asyncio
    async def test_no_image_url_returns_none(self):
        """Returns None when no ImageURL is available."""
        data = {DATA_CAMERAS: [{"CameraID": 1, "Title": "No URL Cam"}]}
        coord = _mock_coordinator(data)
        camera = WSDOTCamera(coord, 1)
        camera.hass = MagicMock()
        camera._image_url = None

        result = await camera.async_camera_image()
        assert result is None

    @pytest.mark.asyncio
    async def test_no_cache_on_error_returns_none(self, sample_cameras):
        """Returns None when error and no cached image exists."""
        coord = _mock_coordinator({DATA_CAMERAS: sample_cameras})
        camera = WSDOTCamera(coord, 1001)
        camera.hass = MagicMock()
        camera._cached_image = None

        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.camera.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await camera.async_camera_image()

        assert result is None

    @pytest.mark.asyncio
    async def test_image_url_updates_from_record(self, sample_cameras):
        """Uses ImageURL from current record, not just the initial one."""
        data = {
            DATA_CAMERAS: [
                {
                    "CameraID": 1001,
                    "Title": "Test",
                    "ImageURL": "https://new-url.com/img.jpg",
                    "DisplayLatitude": 47.01,
                    "DisplayLongitude": -122.90,
                    "IsActive": True,
                }
            ]
        }
        coord = _mock_coordinator(data)
        camera = WSDOTCamera(coord, 1001)
        camera.hass = MagicMock()
        # Original URL was different
        camera._image_url = "https://old-url.com/img.jpg"

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b"new_img")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.camera.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await camera.async_camera_image()

        assert result == b"new_img"
        # Should have called with the new URL from the record
        mock_session.get.assert_called_once()
        called_url = mock_session.get.call_args[0][0]
        assert called_url == "https://new-url.com/img.jpg"
