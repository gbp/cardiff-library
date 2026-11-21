import re

import httpx

from cardiff_library.parsing import (
    LibraryError,
    Loan,
    PageError,
    find_loans_link,
    find_next_page,
    is_login_page,
    parse_loans,
)

BASE_URL = "https://cardiff.spydus.co.uk"
LOGIN_PATH = "/cgi-bin/spydus.exe/PGM/OPAC/CCOPT/LB/2"
LOGOUT_PATH = "/cgi-bin/spydus.exe/PGM/OPAC/CCOPT/LB/3"
AFTER_LOGIN = "/cgi-bin/spydus.exe/PGM/OPAC/CCOPT/LB/1?ISGLB=0"


class InvalidLogin(LibraryError):
    pass


def new_http_client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, follow_redirects=True, timeout=30)


def _get(http: httpx.Client, url: str, **kwargs) -> str:
    response = http.request("GET", url, **kwargs)
    if not response.is_success:
        raise LibraryError(f"The library site replied with HTTP {response.status_code}")
    return response.text


def fetch_loans(http: httpx.Client, card: str, pin: str) -> list[Loan]:
    response = http.post(
        LOGIN_PATH, data={"BRWLID": card, "BRWLPWD": pin, "RDT": AFTER_LOGIN}
    )
    if not response.is_success:
        raise LibraryError(f"The library site replied with HTTP {response.status_code}")
    if is_login_page(response.text):
        raise InvalidLogin("The library rejected the card number or PIN")
    try:
        return parse_loans(_get(http, _all_loans(_loans_link(http, response.text))))
    finally:
        # A failed logout must not hide the loans or the first error.
        try:
            _get(http, LOGOUT_PATH)
        except (LibraryError, httpx.HTTPError):
            pass


def _loans_link(http: httpx.Client, html: str) -> str:
    try:
        return find_loans_link(html)
    except PageError:
        next_page = find_next_page(html)
        if not next_page:
            raise
        return find_loans_link(_get(http, next_page))


# The site shows 30 loans per page by default.
def _all_loans(link: str) -> str:
    if re.search(r"NRECS=\d+", link):
        return re.sub(r"NRECS=\d+", "NRECS=200", link)
    return f"{link}{'&' if '?' in link else '?'}NRECS=200"
