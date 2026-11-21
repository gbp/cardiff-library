"""Cardiff Libraries loans for Home Assistant.

Home Assistant imports stay inside the functions, so the command line tool
can import the shared parser and client without Home Assistant installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant



def _config_schema():
    try:
        from homeassistant.helpers import config_validation as cv
    except ImportError:
        return None
    return cv.config_entry_only_config_schema(DOMAIN)


# Hassfest finds the schema only as an assignment at the top of the module.
CONFIG_SCHEMA = _config_schema()

PLATFORMS = ["sensor"]
CARD_URL = "/cardiff_library/cardiff-library-card.js"
CARD_FILE = Path(__file__).parent / "frontend" / "cardiff-library-card.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # A Home Assistant without the frontend has no dashboards to show a card.
    if "frontend" not in hass.config.components:
        return True

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.loader import async_get_integration

    integration = await async_get_integration(hass, "cardiff_library")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=False)]
    )
    # The version in the URL makes browsers load a new card after an update.
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import LoansCoordinator

    coordinator = LoansCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
