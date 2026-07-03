"""Tests for the WSDOT __init__ module (setup/unload)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.wsdot.const import DOMAIN, PLATFORMS


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_entry_creates_coordinator(self):
        """Setup creates coordinator and stores it in hass.data."""
        from custom_components.wsdot import async_setup_entry

        hass = MagicMock()
        hass.data = {}
        hass.config_entries = AsyncMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {"api_key": "test_key"}
        entry.options = {}
        entry.add_update_listener = MagicMock(return_value=MagicMock())
        entry.async_on_unload = MagicMock()

        with patch(
            "custom_components.wsdot.WSDOTDataUpdateCoordinator"
        ) as mock_coordinator_cls:
            mock_coordinator = AsyncMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_cls.return_value = mock_coordinator

            result = await async_setup_entry(hass, entry)

        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        assert hass.data[DOMAIN][entry.entry_id] == mock_coordinator

    @pytest.mark.asyncio
    async def test_setup_entry_forwards_platforms(self):
        """Setup forwards entry to all platforms."""
        from custom_components.wsdot import async_setup_entry

        hass = MagicMock()
        hass.data = {}
        hass.config_entries = AsyncMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {"api_key": "test_key"}
        entry.options = {}
        entry.add_update_listener = MagicMock(return_value=MagicMock())
        entry.async_on_unload = MagicMock()

        with patch(
            "custom_components.wsdot.WSDOTDataUpdateCoordinator"
        ) as mock_coordinator_cls:
            mock_coordinator = AsyncMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_cls.return_value = mock_coordinator

            await async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            entry, PLATFORMS
        )

    @pytest.mark.asyncio
    async def test_setup_entry_registers_update_listener(self):
        """Setup registers an update listener for options."""
        from custom_components.wsdot import async_setup_entry

        hass = MagicMock()
        hass.data = {}
        hass.config_entries = AsyncMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {"api_key": "test_key"}
        entry.options = {}
        entry.add_update_listener = MagicMock(return_value=MagicMock())
        entry.async_on_unload = MagicMock()

        with patch(
            "custom_components.wsdot.WSDOTDataUpdateCoordinator"
        ) as mock_coordinator_cls:
            mock_coordinator = AsyncMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_cls.return_value = mock_coordinator

            await async_setup_entry(hass, entry)

        entry.add_update_listener.assert_called_once()
        entry.async_on_unload.assert_called_once()


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    @pytest.mark.asyncio
    async def test_unload_entry_success(self):
        """Successful unload removes coordinator from hass.data."""
        from custom_components.wsdot import async_unload_entry

        hass = MagicMock()
        hass.data = {DOMAIN: {"entry_1": MagicMock()}}
        hass.config_entries = AsyncMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        entry = MagicMock()
        entry.entry_id = "entry_1"

        result = await async_unload_entry(hass, entry)

        assert result is True
        assert "entry_1" not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_entry_failure(self):
        """Failed unload keeps coordinator in hass.data."""
        from custom_components.wsdot import async_unload_entry

        hass = MagicMock()
        coordinator = MagicMock()
        hass.data = {DOMAIN: {"entry_1": coordinator}}
        hass.config_entries = AsyncMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        entry = MagicMock()
        entry.entry_id = "entry_1"

        result = await async_unload_entry(hass, entry)

        assert result is False
        assert "entry_1" in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["entry_1"] == coordinator


# ---------------------------------------------------------------------------
# async_update_options
# ---------------------------------------------------------------------------


class TestAsyncUpdateOptions:
    """Tests for async_update_options."""

    @pytest.mark.asyncio
    async def test_update_options_reloads_entry(self):
        """Updating options reloads the config entry."""
        from custom_components.wsdot import async_update_options

        hass = MagicMock()
        hass.config_entries = AsyncMock()
        hass.config_entries.async_reload = AsyncMock()

        entry = MagicMock()
        entry.entry_id = "entry_1"

        await async_update_options(hass, entry)

        hass.config_entries.async_reload.assert_called_once_with("entry_1")


# ---------------------------------------------------------------------------
# Constants / domain verification
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_domain_is_wsdot(self):
        assert DOMAIN == "wsdot"

    def test_platforms_has_expected_entries(self):
        assert "sensor" in PLATFORMS
        assert "camera" in PLATFORMS
        assert "binary_sensor" in PLATFORMS
        assert len(PLATFORMS) == 3
