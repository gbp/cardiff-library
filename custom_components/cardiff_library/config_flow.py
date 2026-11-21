import logging
from collections.abc import Mapping
from typing import Any

import httpx
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .client import InvalidLogin, fetch_loans, new_http_client
from .const import CONF_CARD, CONF_LABEL, CONF_PIN, DOMAIN
from .parsing import LibraryError

_LOGGER = logging.getLogger(__name__)
SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LABEL): str,
        vol.Required(CONF_CARD): str,
        vol.Required(CONF_PIN): str,
    }
)
PIN_SCHEMA = vol.Schema({vol.Required(CONF_PIN): str})


def check_login(card: str, pin: str) -> None:
    with new_http_client() as http:
        fetch_loans(http, card, pin)


class LibraryConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            card = user_input[CONF_CARD].strip()
            await self.async_set_unique_id(card)
            self._abort_if_unique_id_configured()
            error = await self._check(card, user_input[CONF_PIN])
            if error is None:
                return self.async_create_entry(
                    title=user_input[CONF_LABEL], data={**user_input, CONF_CARD: card}
                )
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._check(entry.data[CONF_CARD], user_input[CONF_PIN])
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PIN: user_input[CONF_PIN]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=PIN_SCHEMA,
            errors=errors,
            description_placeholders={"label": entry.title},
        )

    async def _check(self, card: str, pin: str) -> str | None:
        try:
            await self.hass.async_add_executor_job(check_login, card, pin)
        except InvalidLogin:
            return "invalid_auth"
        except (LibraryError, httpx.HTTPError):
            return "cannot_connect"
        except Exception:  # noqa: BLE001 - the form must show an error, not fail
            _LOGGER.exception("Unexpected error while checking the library login")
            return "unknown"
        return None
