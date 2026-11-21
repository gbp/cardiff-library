from unittest.mock import AsyncMock, Mock

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.setup import async_setup_component

from custom_components.cardiff_library import CARD_FILE, CARD_URL
from custom_components.cardiff_library.const import DOMAIN


async def test_the_card_is_served_and_loaded_on_every_dashboard(hass):
    hass.config.components.add("frontend")
    hass.data[DATA_EXTRA_MODULE_URL] = set()
    hass.http = Mock(async_register_static_paths=AsyncMock())

    assert await async_setup_component(hass, DOMAIN, {})

    (path,) = hass.http.async_register_static_paths.call_args.args[0]
    assert (path.url_path, path.path) == (CARD_URL, str(CARD_FILE))
    assert CARD_FILE.is_file()
    assert hass.data[DATA_EXTRA_MODULE_URL] == {f"{CARD_URL}?v=0.1.0"}


async def test_nothing_is_registered_without_the_frontend(hass):
    hass.http = Mock(async_register_static_paths=AsyncMock())

    assert await async_setup_component(hass, DOMAIN, {})

    hass.http.async_register_static_paths.assert_not_called()
