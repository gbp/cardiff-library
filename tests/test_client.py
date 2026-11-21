from datetime import date

import pytest

from cardiff_library.client import InvalidLogin, _all_loans, fetch_loans, new_http_client
from cardiff_library.parsing import Loan, PageError


def fetch(card="00000000000000", pin="0000"):
    with new_http_client() as http:
        return fetch_loans(http, card, pin)


@pytest.mark.vcr
def test_logs_in_reads_every_loan_and_logs_out():
    assert fetch() == [
        Loan(
            "Atlas",
            "Ng, A",
            date(2026, 12, 5),
            "Renewed 2 times",
            "https://www.bibdsl.co.uk/xmla/image-service.asp?ISBN=9999999999999&SIZE=m",
        ),
        Loan("Moon", "Ola, B", date(2026, 12, 12), ""),
    ]


@pytest.mark.vcr
def test_a_wrong_card_or_pin_is_reported():
    with pytest.raises(InvalidLogin):
        fetch()


@pytest.mark.vcr
def test_logs_out_even_when_the_loans_page_is_bad():
    with pytest.raises(PageError):
        fetch()


@pytest.mark.vcr
def test_a_failed_logout_keeps_the_loans():
    assert [loan.title for loan in fetch()] == ["Atlas"]


def test_asks_for_every_loan_on_one_page():
    assert _all_loans("/x?NRECS=300&FMT=CL") == "/x?NRECS=200&FMT=CL"
    assert _all_loans("/x?FMT=CL") == "/x?FMT=CL&NRECS=200"
