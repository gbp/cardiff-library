"""Reduce recorded traffic to an allowed list of fields.

The repo holds the cassettes, and live pages hold the account holder's name,
card number and session numbers. The scrubber drops anything not on the
allowed list. Each function must give the same result when it runs on its own
output, because vcrpy also runs the filters on playback.
"""

import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from custom_components.cardiff_library.parsing import find_next_page

KEPT_RESPONSE_HEADERS = {"content-type", "location"}
LOGIN_FORM = '<form><input type="password" name="BRWLPWD"></form>'


def scrub_url(url: str) -> str:
    return re.sub(r"\d{4,}", lambda match: "9" * len(match[0]), url)


def scrub_request(request):
    request.uri = scrub_url(request.uri)
    request.headers = {}
    request.body = None
    return request


def scrub_response(response):
    response["headers"] = {
        name: [scrub_url(value) if name.lower() == "location" else value for value in values]
        for name, values in response["headers"].items()
        if name.lower() in KEPT_RESPONSE_HEADERS
    }
    body = response["body"]["string"]
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    response["body"]["string"] = scrub_body(text).encode()
    return response


def scrub_body(text: str) -> str:
    if "table-stacked" in text:
        return _loans_table(text)
    if "LOANRENQ" in text:
        return _loans_link(text)
    if 'name="BRWLPWD"' in text:
        return LOGIN_FORM
    next_page = find_next_page(text)
    if next_page:
        return f'<meta http-equiv="refresh" content="0;URL={html.escape(scrub_url(next_page))}">'
    return ""


def _loans_table(page: str) -> str:
    rows = []
    for row in BeautifulSoup(page, "html.parser").select("table.table-stacked tbody tr"):
        title = row.select_one("h2.card-title")
        author = row.select_one("div.card-text span.d-block")
        image = row.select_one("img[data-imgurls]")
        covers = _scrub_covers(image["data-imgurls"]) if image else ""
        rows.append(
            "<tr>"
            f'<td class="col-image"><img data-imgurls="{html.escape(covers)}"></td>'
            f'<td><h2 class="card-title">{_text(title)}</h2>'
            f'<div class="card-text"><span class="d-block">{_text(author)}</span></div></td>'
            f'<td data-caption="Due">{_caption(row, "Due")}</td>'
            f'<td data-caption="Status">{_caption(row, "Status")}</td>'
            "</tr>"
        )
    return f'<table class="table-stacked"><tbody>{"".join(rows)}</tbody></table>'


def _scrub_covers(urls: str) -> str:
    return "**".join(_scrub_cover(url) for url in urls.split("**"))


def _scrub_cover(url: str) -> str:
    if not url:
        return url
    parts = urlsplit(url)
    query = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if name in ("ISBN", "SIZE")
    ]
    return scrub_url(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), "")))


def _loans_link(page: str) -> str:
    for link in BeautifulSoup(page, "html.parser").select('a[href*="LOANRENQ"]'):
        if link.get_text(strip=True) == "Current loans":
            href = scrub_url(link["href"]).replace("&", "&amp;")
            return f'<a href="{href}">Current loans</a>'
    return ""


def _text(element) -> str:
    return html.escape(element.get_text(" ", strip=True)) if element else ""


def _caption(row, name: str) -> str:
    return _text(row.find("td", attrs={"data-caption": name}))
