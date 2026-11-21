from datetime import date

import pytest

from custom_components.cardiff_library.parsing import (
    Loan,
    PageError,
    find_loans_link,
    find_next_page,
    is_login_page,
    parse_loans,
)


def row(title, author, due, status="", year="2022", cover=""):
    return f"""
<tr>
  <td class="counter"><input type="checkbox" name="SVL"></td>
  <td class="col-image">{cover}</td>
  <td><h2 class="card-title mb-0"><span class="d-block"><a href="/x"><span>{title}</span></a></span></h2>
    <div class="card-text"><span class="d-block">{author}</span><span class="d-block">{year}</span></div></td>
  <td class="text-nowrap below-image" data-caption="Due"><span class="d-block">{due}</span></td>
  <td class="text-nowrap" data-caption="Status">{status}</td>
  <td>Renew loan</td>
</tr>"""


def page(*rows):
    return (
        '<header><span class="name">Test Holder</span></header>'
        '<table class="table table-stacked"><thead><tr><th>#</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def test_reads_each_loan():
    loans = parse_loans(
        page(
            row("Atlas", "Ng, A", "05 Dec 2026", "Renewed 2 times"),
            row("Moon", "Ola, B", "12 Dec 2026"),
        )
    )

    assert loans == [
        Loan("Atlas", "Ng, A", date(2026, 12, 5), "Renewed 2 times"),
        Loan("Moon", "Ola, B", date(2026, 12, 12), ""),
    ]


def test_reads_the_first_cover_address_that_has_an_isbn():
    image = (
        '<img src="/loading.png" data-imgurls="https://img.test/s?ISBN=&amp;SIZE=m**'
        'https://img.test/s?ISBN=9780000000002&amp;SIZE=m**">'
    )

    loan = parse_loans(page(row("Atlas", "Ng, A", "05 Dec 2026", cover=image)))[0]

    assert loan.cover == "https://img.test/s?ISBN=9780000000002&SIZE=m"


def test_a_loan_with_no_isbn_has_no_cover():
    image = '<img data-imgurls="https://img.test/s?ISBN=&amp;SIZE=m**">'

    assert parse_loans(page(row("Atlas", "Ng, A", "05 Dec 2026", cover=image)))[0].cover is None


def test_a_loan_without_an_author_still_reads():
    html = page(row("Comet", "", "05 Dec 2026")).replace('<span class="d-block"></span>', "")

    assert parse_loans(html)[0].title == "Comet"


def test_an_account_with_no_loans_reads_as_empty():
    assert parse_loans("<main><p>No loans</p></main>") == []


def test_a_bad_due_date_is_a_page_error():
    with pytest.raises(PageError):
        parse_loans(page(row("Atlas", "Ng, A", "soon")))


def test_finds_the_current_loans_link():
    html = (
        '<a href="/cgi-bin/spydus.exe/ENQ/OPAC/LOANRENQ/1?FMT=CL">Current loans</a>'
        '<a href="/cgi-bin/spydus.exe/ENQ/OPAC/LOANRENQ/2?FMT=X">Loans history</a>'
    )

    assert find_loans_link(html) == "/cgi-bin/spydus.exe/ENQ/OPAC/LOANRENQ/1?FMT=CL"


def test_a_page_without_the_link_is_a_page_error():
    with pytest.raises(PageError):
        find_loans_link("<a href='/home'>Home</a>")


def test_spots_the_login_form():
    assert is_login_page('<input type="password" name="BRWLPWD">')
    assert not is_login_page(page())


def test_finds_the_page_a_script_or_meta_refresh_sends_the_browser_to():
    script = '<script>location.replace("/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/1?A=1&B=2");</script>'
    meta = '<meta http-equiv="refresh" content="0;URL=/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/1?A=1&amp;B=2">'

    assert find_next_page(script) == "/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/1?A=1&B=2"
    assert find_next_page(meta) == "/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/1?A=1&B=2"
    assert find_next_page("<p>Done</p>") is None
