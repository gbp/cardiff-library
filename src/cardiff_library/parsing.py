import re
from dataclasses import dataclass
from datetime import date, datetime
from html import unescape

from bs4 import BeautifulSoup


class LibraryError(Exception):
    pass


class PageError(LibraryError):
    pass


@dataclass(frozen=True)
class Loan:
    title: str
    author: str
    due: date
    status: str


def is_login_page(html: str) -> bool:
    return 'name="BRWLPWD"' in html


def find_loans_link(html: str) -> str:
    for link in BeautifulSoup(html, "html.parser").select('a[href*="LOANRENQ"]'):
        if link.get_text(strip=True) == "Current loans":
            return link["href"]
    raise PageError("The account page has no current loans link")


# The login reply is a short page that sends the browser on with a script,
# not an HTTP redirect, so a plain client must follow it by hand.
def find_next_page(html: str) -> str | None:
    found = re.search(r"/cgi-bin/spydus\.exe/[^\"'\s<>]+", html)
    return unescape(found[0]) if found else None


# Reads only the loans table, so that the account holder's name elsewhere on
# the page never enters the program.
def parse_loans(html: str) -> list[Loan]:
    soup = BeautifulSoup(html, "html.parser")
    try:
        return [_parse_row(row) for row in soup.select("table.table-stacked tbody tr")]
    except (AttributeError, ValueError) as error:
        raise PageError("The loans page has an unexpected format") from error


def _parse_row(row) -> Loan:
    details = row.select_one("div.card-text span.d-block")
    return Loan(
        title=row.select_one("h2.card-title").get_text(" ", strip=True),
        author=details.get_text(strip=True) if details else "",
        due=datetime.strptime(_caption(row, "Due"), "%d %b %Y").date(),
        status=_caption(row, "Status"),
    )


def _caption(row, name: str) -> str:
    cell = row.find("td", attrs={"data-caption": name})
    return cell.get_text(" ", strip=True) if cell else ""
