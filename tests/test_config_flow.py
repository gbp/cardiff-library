from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cardiff_library.client import InvalidLogin
from custom_components.cardiff_library.const import DOMAIN
from custom_components.cardiff_library.parsing import PageError

INPUT = {"label": "Ana", "card": " 00000000000001 ", "pin": "0000"}
CHECK = "custom_components.cardiff_library.config_flow.check_login"


async def submit(hass, user_input=INPUT):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_a_good_login_adds_the_account_under_its_label(hass):
    with patch(CHECK) as check:
        result = await submit(hass)

    check.assert_called_once_with("00000000000001", "0000")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ana"
    assert result["data"]["card"] == "00000000000001"


@pytest.mark.parametrize(
    ("error", "reason"),
    [(InvalidLogin("no"), "invalid_auth"), (PageError("odd"), "cannot_connect")],
)
async def test_a_failed_login_shows_the_form_with_an_error(hass, error, reason):
    with patch(CHECK, side_effect=error):
        result = await submit(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": reason}


async def test_an_unexpected_error_shows_the_form_with_an_error(hass):
    with patch(CHECK, side_effect=RuntimeError("boom")):
        result = await submit(hass)

    assert result["errors"] == {"base": "unknown"}


async def test_reauth_saves_the_new_pin(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="00000000000001", data={**INPUT, "card": "00000000000001"})
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)

    with patch(CHECK, side_effect=InvalidLogin("no")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "1111"})
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(CHECK) as check, patch.object(hass.config_entries, "async_reload"):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"pin": "2222"})

    check.assert_called_once_with("00000000000001", "2222")
    assert result["reason"] == "reauth_successful"
    assert entry.data["pin"] == "2222"


async def test_the_same_card_cannot_be_added_twice(hass):
    MockConfigEntry(domain=DOMAIN, unique_id="00000000000001", data=INPUT).add_to_hass(hass)

    with patch(CHECK):
        result = await submit(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
