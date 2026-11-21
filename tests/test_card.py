from datetime import date
from pathlib import Path
from unittest.mock import patch

import yaml
from homeassistant.helpers.template import Template
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cardiff_library.const import DOMAIN
from custom_components.cardiff_library.parsing import Loan

CARD = yaml.safe_load(Path(__file__).parent.parent.joinpath("card.yaml").read_text())
FETCH = "custom_components.cardiff_library.coordinator.fetch_loans"


async def add_account(hass, label, loans):
    entry = MockConfigEntry(
        domain=DOMAIN, title=label, unique_id=label, data={"label": label, "card": label, "pin": "0"}
    )
    entry.add_to_hass(hass)
    with patch(FETCH, return_value=loans):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def render(hass):
    return Template(CARD["content"], hass).async_render(parse_result=False)


async def test_card_lists_every_account_by_due_date_with_covers(hass, freezer):
    freezer.move_to("2026-12-01 12:00:00")
    await add_account(
        hass,
        "Ana",
        [Loan("Atlas", "", date(2026, 12, 20), "", "https://img.test/a.jpg"), Loan("Sun", "", date(2026, 12, 1), "")],
    )
    await add_account(
        hass,
        "Ben",
        [Loan("Moon", "", date(2026, 11, 30), ""), Loan("Comet", "", date(2026, 12, 3), "")],
    )

    html = render(hass)

    assert html.index("Moon") < html.index("Comet") < html.index("Atlas")
    assert '<img src="https://img.test/a.jpg"' in html
    assert "Ben · due Mon 30 Nov · <b>overdue 1d</b>" in html
    assert "<b>due in 2d</b>" in html
    assert "Ana · due Tue 01 Dec · <b>due today</b>" in html


async def test_card_says_so_when_nothing_is_on_loan(hass):
    await add_account(hass, "Ana", [])

    assert "No books on loan." in render(hass)
