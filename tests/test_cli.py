from datetime import date

import pytest

from cardiff_library.cli import main

TODAY = date(2026, 12, 1)
ACCOUNTS = """
[[account]]
label = "Ana"
card = "00000000000001"
pin = "0000"

[[account]]
label = "Ben"
card = "00000000000002"
pin = "0000"
"""


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "accounts.toml"
    path.write_text(ACCOUNTS)
    return path


@pytest.mark.vcr
def test_lists_every_account_by_due_date(config, capsys):
    assert main(["--config", str(config)], today=TODAY) == 0

    assert capsys.readouterr().out.splitlines() == [
        "Mon 30 Nov   OVERDUE 1d  Ben  Moon (Ola, B)",
        "Sat 05 Dec           4d  Ana  Atlas (Ng, A)  [Renewed 2 times]",
    ]


@pytest.mark.vcr
def test_one_failed_account_still_shows_the_others(config, capsys):
    assert main(["--config", str(config)], today=TODAY) == 1

    output = capsys.readouterr()
    assert "Error for Ana: The library rejected the card number or PIN" in output.err
    assert "Moon" in output.out


@pytest.mark.vcr
def test_html_option_writes_the_page_and_opens_it(config, tmp_path, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr("webbrowser.open", opened.append)
    page = tmp_path / "loans.html"

    assert main(["--config", str(config), "--html", str(page)], today=TODAY) == 0

    assert "Atlas" in page.read_text() and "Moon" in page.read_text()
    assert opened == [page.resolve().as_uri()]


@pytest.mark.vcr
def test_a_page_that_cannot_be_written_is_an_error(config, tmp_path, capsys):
    page = tmp_path / "missing" / "loans.html"

    assert main(["--config", str(config), "--html", str(page)], today=TODAY) == 1

    assert "Error writing" in capsys.readouterr().err


def test_a_missing_accounts_file_says_where_it_looked(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "none.toml")]) == 1

    assert "No accounts file at" in capsys.readouterr().err


def test_an_unreadable_accounts_file_is_an_error_not_a_crash(tmp_path, capsys):
    assert main(["--config", str(tmp_path)]) == 1

    assert "Cannot read" in capsys.readouterr().err


def test_a_bad_accounts_file_says_what_it_needs(tmp_path, capsys):
    path = tmp_path / "accounts.toml"
    path.write_text('[[account]]\nlabel = "Ana"\n')

    assert main(["--config", str(path)]) == 1

    assert "label, card and pin" in capsys.readouterr().err
