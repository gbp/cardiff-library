import argparse
import os
import sys
import tomllib
import webbrowser
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

from cardiff_library.client import fetch_loans, new_http_client
from cardiff_library.page import render_page, when
from cardiff_library.parsing import LibraryError, Loan

DEFAULT_CONFIG = Path.home() / ".config" / "cardiff-library" / "accounts.toml"


@dataclass(frozen=True)
class Account:
    label: str
    card: str
    pin: str


def load_accounts(path: Path) -> list[Account]:
    try:
        data = tomllib.loads(path.read_text())
        return [Account(str(a["label"]), str(a["card"]), str(a["pin"])) for a in data["account"]]
    except FileNotFoundError as error:
        raise LibraryError(f"No accounts file at {path}") from error
    except (OSError, UnicodeDecodeError) as error:
        raise LibraryError(f"Cannot read {path}") from error
    except (tomllib.TOMLDecodeError, KeyError, TypeError) as error:
        raise LibraryError(f"{path} needs [[account]] entries with label, card and pin") from error


def print_loans(rows: list[tuple[str, Loan]], today: date) -> None:
    width = max((len(label) for label, _ in rows), default=0)
    for label, loan in sorted(rows, key=lambda row: (row[1].due, row[0])):
        author = f" ({loan.author})" if loan.author else ""
        status = f"  [{loan.status}]" if loan.status else ""
        print(
            f"{loan.due:%a %d %b}  {when(loan.due, today):>11}  "
            f"{label:<{width}}  {loan.title}{author}{status}"
        )


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cardiff-library", description="List current loans for each library account."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(os.environ.get("CARDIFF_LIBRARY_CONFIG", DEFAULT_CONFIG)),
        help=f"accounts file (default {DEFAULT_CONFIG})",
    )
    parser.add_argument("--html", type=Path, help="also write a page of covers here and open it")
    args = parser.parse_args(argv)

    try:
        accounts = load_accounts(args.config)
    except LibraryError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    rows: list[tuple[str, Loan]] = []
    failed = False
    for account in accounts:
        try:
            with new_http_client() as http:
                rows += [(account.label, loan) for loan in fetch_loans(http, account.card, account.pin)]
        except (LibraryError, httpx.HTTPError) as error:
            detail = str(error) if isinstance(error, LibraryError) else type(error).__name__
            print(f"Error for {account.label}: {detail}", file=sys.stderr)
            failed = True

    today = today or date.today()
    print_loans(rows, today)
    if args.html:
        try:
            args.html.write_text(render_page(rows, today), encoding="utf-8")
        except OSError:
            print(f"Error writing {args.html}", file=sys.stderr)
            return 1
        webbrowser.open(args.html.resolve().as_uri())
    if not rows and not failed:
        print("No books on loan.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
