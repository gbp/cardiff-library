from datetime import timedelta
import logging

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import InvalidLogin, fetch_loans, new_http_client
from .const import CONF_CARD, CONF_PIN, DOMAIN
from .parsing import LibraryError, Loan

UPDATE_INTERVAL = timedelta(hours=6)


class LoansCoordinator(DataUpdateCoordinator[list[Loan]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logging.getLogger(__name__),
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> list[Loan]:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except InvalidLogin as error:
            raise ConfigEntryAuthFailed(str(error)) from error
        except (LibraryError, httpx.HTTPError) as error:
            detail = str(error) if isinstance(error, LibraryError) else type(error).__name__
            raise UpdateFailed(detail) from error

    def _fetch(self) -> list[Loan]:
        data = self.config_entry.data
        with new_http_client() as http:
            return fetch_loans(http, data[CONF_CARD], data[CONF_PIN])
