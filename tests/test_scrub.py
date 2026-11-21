from types import SimpleNamespace

from cardiff_library.parsing import find_loans_link, find_next_page, parse_loans
from scrub import scrub_body, scrub_request, scrub_response

LOANS = """
<html><head><title>Loans | Test Holder</title></head><body>
<span class="name">Test Holder</span>
<table class="table table-stacked"><tbody><tr>
  <td><a href="/x/PGM/OPAC/CCOPT/123456780/0/N/3/LOANRENQ?SVL=11112222">Renew</a></td>
  <td><h2 class="card-title"><a href="/x"><span>Atlas</span></a></h2>
    <div class="card-text"><span class="d-block">Ng, A</span><span class="d-block">2022</span></div></td>
  <td data-caption="Due"><span>05 Dec 2026</span></td>
  <td data-caption="Status">Renewed 2 times</td>
</tr></tbody></table></body></html>
"""
DASHBOARD = (
    '<p>Welcome Test Holder</p>'
    '<a href="/cgi-bin/spydus.exe/ENQ/OPAC/LOANRENQ/123456789?QRY=OND01%5C7654321&FMT=CL">Current loans</a>'
)


def test_loans_page_keeps_the_loans_and_drops_the_rest():
    scrubbed = scrub_body(LOANS)

    assert "Test Holder" not in scrubbed
    assert "11112222" not in scrubbed
    loan = parse_loans(scrubbed)[0]
    assert (loan.title, loan.author, loan.status) == ("Atlas", "Ng, A", "Renewed 2 times")


def test_dashboard_keeps_only_the_loans_link_with_numbers_replaced():
    scrubbed = scrub_body(DASHBOARD)

    assert "Test Holder" not in scrubbed
    assert "123456789" not in scrubbed and "7654321" not in scrubbed
    assert "LOANRENQ/999999999" in find_loans_link(scrubbed)


def test_cover_addresses_lose_the_site_key_and_keep_working():
    image = '<img data-imgurls="https://img.test/s?ISBN=9780000000002&amp;DBM=realkey&amp;SIZE=m&amp;X=other**">'
    scrubbed = scrub_body(LOANS.replace('<td><h2', f'<td class="col-image">{image}</td><td><h2'))

    assert "realkey" not in scrubbed and "other" not in scrubbed
    assert parse_loans(scrubbed)[0].cover == "https://img.test/s?ISBN=9999999999999&SIZE=m"
    assert scrub_body(scrubbed) == scrubbed


def test_text_is_escaped_so_the_cassette_stays_valid():
    loan = parse_loans(scrub_body(LOANS.replace("Atlas", "A < B")))[0]

    assert loan.title == "A < B"


def test_short_record_numbers_are_replaced_too():
    assert scrub_body(DASHBOARD.replace("7654321", "4321")).count("4321") == 0


def test_a_forwarding_page_keeps_only_its_target_with_numbers_replaced():
    page = '<p>Test Holder</p><script>location.replace("/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/123456789?Q=1&R=2")</script>'

    scrubbed = scrub_body(page)

    assert "Test Holder" not in scrubbed
    assert find_next_page(scrubbed) == "/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/999999999?Q=1&R=2"
    assert scrub_body(scrubbed) == scrubbed


def test_unknown_pages_are_dropped():
    assert scrub_body("<p>Test Holder, card 21234567890123</p>") == ""


def test_login_request_loses_card_pin_and_cookies():
    request = SimpleNamespace(
        uri="https://x/LB/2", body="BRWLID=21234567890123&BRWLPWD=1234", headers={"Cookie": "a"}
    )

    scrubbed = scrub_request(request)

    assert scrubbed.body is None
    assert scrubbed.headers == {}


def test_response_headers_are_limited_and_locations_scrubbed():
    response = {
        "headers": {
            "Set-Cookie": ["AWSALB=real"],
            "Location": ["/cgi-bin/spydus.exe/ENQ/OPAC/BRWENQ/123456789"],
            "Content-Type": ["text/html"],
        },
        "body": {"string": b""},
    }

    scrubbed = scrub_response(response)

    assert set(scrubbed["headers"]) == {"Location", "Content-Type"}
    assert "123456789" not in scrubbed["headers"]["Location"][0]


def test_scrubbing_twice_changes_nothing():
    for html in (LOANS, DASHBOARD):
        assert scrub_body(scrub_body(html)) == scrub_body(html)
