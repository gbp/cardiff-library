from datetime import date

from cardiff_library.page import render_page
from cardiff_library.parsing import Loan

TODAY = date(2026, 12, 1)


def test_cards_follow_due_date_and_mark_late_and_soon_loans():
    page = render_page(
        [
            ("Ana", Loan("Later", "", date(2026, 12, 20), "")),
            ("Ben", Loan("Late", "", date(2026, 11, 30), "")),
            ("Ana", Loan("Soon", "", date(2026, 12, 3), "")),
        ],
        TODAY,
    )

    assert page.index("Late") < page.index("Soon") < page.index("Later")
    assert '<article class="late">' in page
    assert '<article class="soon">' in page
    assert "OVERDUE 1d" in page


def test_cover_shows_as_an_image_or_falls_back_to_the_title():
    page = render_page(
        [
            ("Ana", Loan("Atlas", "Ng, A", date(2026, 12, 5), "", "https://img.test/s?ISBN=1&SIZE=m")),
            ("Ben", Loan("Moon", "", date(2026, 12, 6), "")),
        ],
        TODAY,
    )

    assert '<img src="https://img.test/s?ISBN=1&amp;SIZE=m"' in page
    assert '<div class="cover">Moon</div>' in page


def test_text_from_the_site_is_escaped():
    page = render_page([("<b>", Loan("<script>", "", date(2026, 12, 5), ""))], TODAY)

    assert "<script>" not in page.split("<style>")[0] + page.split("</style>")[1]
    assert "&lt;script&gt;" in page
    assert "&lt;b&gt;" in page


def test_no_loans_says_so():
    assert "No books on loan." in render_page([], TODAY)
