"""Tests for the WSDOT config_flow module."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.wsdot.config_flow import (
    CannotConnect,
    ConfigFlow,
    InvalidAuth,
    OptionsFlowHandler,
    validate_input,
)
from custom_components.wsdot.const import CONF_API_KEY


# ---------------------------------------------------------------------------
# validate_input
# ---------------------------------------------------------------------------


class TestValidateInput:
    """Tests for validate_input."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Successful validation returns title."""
        hass = MagicMock()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=[{"MountainPassId": 1}])
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.config_flow.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await validate_input(hass, {CONF_API_KEY: "valid_key"})

        assert result == {"title": "WSDOT Traffic"}

    @pytest.mark.asyncio
    async def test_invalid_auth_401(self):
        """Returns InvalidAuth on 401 response."""
        hass = MagicMock()

        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.config_flow.async_get_clientsession",
            return_value=mock_session,
        ):
            with pytest.raises(InvalidAuth):
                await validate_input(hass, {CONF_API_KEY: "bad_key"})

    @pytest.mark.asyncio
    async def test_invalid_auth_403(self):
        """Returns InvalidAuth on 403 response."""
        hass = MagicMock()

        mock_resp = AsyncMock()
        mock_resp.status = 403
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.config_flow.async_get_clientsession",
            return_value=mock_session,
        ):
            with pytest.raises(InvalidAuth):
                await validate_input(hass, {CONF_API_KEY: "bad_key"})

    @pytest.mark.asyncio
    async def test_cannot_connect_on_500(self):
        """Returns CannotConnect on server error."""
        hass = MagicMock()

        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.config_flow.async_get_clientsession",
            return_value=mock_session,
        ):
            with pytest.raises(CannotConnect):
                await validate_input(hass, {CONF_API_KEY: "key"})

    @pytest.mark.asyncio
    async def test_cannot_connect_on_client_error(self):
        """Returns CannotConnect on network error."""
        import aiohttp

        hass = MagicMock()

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            side_effect=aiohttp.ClientError("Connection refused")
        )

        with patch(
            "custom_components.wsdot.config_flow.async_get_clientsession",
            return_value=mock_session,
        ):
            with pytest.raises(CannotConnect):
                await validate_input(hass, {CONF_API_KEY: "key"})

    @pytest.mark.asyncio
    async def test_cannot_connect_non_list_response(self):
        """Returns CannotConnect when response is not a list."""
        hass = MagicMock()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"error": "bad key"})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch(
            "custom_components.wsdot.config_flow.async_get_clientsession",
            return_value=mock_session,
        ):
            with pytest.raises(CannotConnect):
                await validate_input(hass, {CONF_API_KEY: "key"})


# ---------------------------------------------------------------------------
# ConfigFlow
# ---------------------------------------------------------------------------


class TestConfigFlow:
    """Tests for the ConfigFlow class."""

    @pytest.mark.asyncio
    async def test_step_user_no_input_shows_form(self):
        """Shows form when no user_input."""
        flow = ConfigFlow()
        result = await flow.async_step_user(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_step_user_valid_input_creates_entry(self):
        """Creates entry on valid input."""
        flow = ConfigFlow()

        with patch(
            "custom_components.wsdot.config_flow.validate_input",
            return_value={"title": "WSDOT Traffic"},
        ):
            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "valid_key_12345"}
            )

        assert result["type"] == "create_entry"
        assert result["title"] == "WSDOT Traffic"
        assert result["data"] == {CONF_API_KEY: "valid_key_12345"}

    @pytest.mark.asyncio
    async def test_step_user_cannot_connect_error(self):
        """Shows cannot_connect error."""
        flow = ConfigFlow()

        with patch(
            "custom_components.wsdot.config_flow.validate_input",
            side_effect=CannotConnect,
        ):
            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "key"}
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}

    @pytest.mark.asyncio
    async def test_step_user_invalid_auth_error(self):
        """Shows invalid_auth error."""
        flow = ConfigFlow()

        with patch(
            "custom_components.wsdot.config_flow.validate_input",
            side_effect=InvalidAuth,
        ):
            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "bad_key"}
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}

    @pytest.mark.asyncio
    async def test_step_user_unknown_error(self):
        """Shows unknown error on unexpected exception."""
        flow = ConfigFlow()

        with patch(
            "custom_components.wsdot.config_flow.validate_input",
            side_effect=RuntimeError("something broke"),
        ):
            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "key"}
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "unknown"}


# ---------------------------------------------------------------------------
# OptionsFlowHandler
# ---------------------------------------------------------------------------


class TestOptionsFlowHandler:
    """Tests for the OptionsFlowHandler class."""

    @pytest.mark.asyncio
    async def test_init_no_input_shows_form(self):
        """Shows form with current scan_interval when no input."""
        entry = MagicMock()
        entry.options = {"scan_interval": 120}
        handler = OptionsFlowHandler(entry)

        result = await handler.async_step_init(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_with_input_creates_entry(self):
        """Creates entry when user submits options."""
        entry = MagicMock()
        entry.options = {}
        handler = OptionsFlowHandler(entry)

        result = await handler.async_step_init(user_input={"scan_interval": 300})
        assert result["type"] == "create_entry"
        assert result["data"] == {"scan_interval": 300}

    @pytest.mark.asyncio
    async def test_init_default_scan_interval(self):
        """Uses DEFAULT_SCAN_INTERVAL when no option is set."""
        entry = MagicMock()
        entry.options = {}
        handler = OptionsFlowHandler(entry)

        result = await handler.async_step_init(user_input=None)
        assert result["type"] == "form"


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class TestExceptions:
    """Tests for custom exception classes."""

    def test_cannot_connect_is_exception(self):
        assert issubclass(CannotConnect, Exception)

    def test_invalid_auth_is_exception(self):
        assert issubclass(InvalidAuth, Exception)

    def test_cannot_connect_can_be_raised(self):
        with pytest.raises(CannotConnect):
            raise CannotConnect()

    def test_invalid_auth_can_be_raised(self):
        with pytest.raises(InvalidAuth):
            raise InvalidAuth()
