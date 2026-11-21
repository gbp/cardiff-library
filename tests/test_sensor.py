from datetime import date
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cardiff_library.client import InvalidLogin
from custom_components.cardiff_library.const import DOMAIN
from custom_components.cardiff_library.parsing import Loan, PageError

FETCH = "custom_components.cardiff_library.coordinator.fetch_loans"
LOANS = [
    Loan("Moon", "Ola, B", date(2026, 12, 12), ""),
    Loan("Atlas", "Ng, A", date(2026, 12, 5), "Renewed 2 times", "https://img.test/a.jpg"),
]


async def set_up(hass, **fetch):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ana",
        unique_id="00000000000001",
        data={"label": "Ana", "card": "00000000000001", "pin": "0000"},
    )
    entry.add_to_hass(hass)
    with patch(FETCH, **fetch):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_sensor_counts_loans_and_lists_them_by_due_date(hass):
    await set_up(hass, return_value=LOANS)

    state = hass.states.get("sensor.library_ana_loans")
    assert state.state == "2"
    assert state.attributes["account"] == "Ana"
    assert state.attributes["next_due"] == "2026-12-05"
    assert [loan["title"] for loan in state.attributes["loans"]] == ["Atlas", "Moon"]
    assert state.attributes["loans"][0] == {
        "title": "Atlas",
        "author": "Ng, A",
        "due": "2026-12-05",
        "status": "Renewed 2 times",
        "cover": "https://img.test/a.jpg",
    }


async def test_an_account_with_no_loans_shows_zero(hass):
    await set_up(hass, return_value=[])

    state = hass.states.get("sensor.library_ana_loans")
    assert state.state == "0"
    assert state.attributes["next_due"] is None


async def test_a_failed_first_fetch_retries_the_setup_later(hass):
    entry = await set_up(hass, side_effect=PageError("odd page"))

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_a_rejected_pin_asks_for_a_new_one(hass):
    entry = await set_up(hass, side_effect=InvalidLogin("rejected"))

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]
