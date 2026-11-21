# Cardiff Libraries

See the books on loan from your Cardiff Libraries accounts, with covers and
due dates. Use it as a Home Assistant integration or from the terminal.

The tool reads the library's Spydus site. It only reads. It does not renew
loans.

## Install in Home Assistant

1. In HACS, open the menu and select **Custom repositories**.
2. Add this repository with the type **Integration**.
3. Install **Cardiff Libraries**, then restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Select **Cardiff Libraries**.
6. Enter a label, the card number and the PIN.
7. Repeat steps 4 to 6 for each account.

Each account gets a sensor, such as `sensor.library_ana_loans`. The state is
the number of books on loan. The attributes hold `account`, `next_due` and
`loans`, a list of title, author, due date, status and cover address, sorted by
due date. The sensor updates every 6 hours. To update it now, run the
`homeassistant.update_entity` action on it.

## Add the dashboard card

1. Open a dashboard and select **Edit dashboard → Add card**.
2. Search for **Library loans** and select it.
3. Select **Save**.

The card needs no settings. It lists the loans of every account by due date,
with a cover, the account label and the due date. It marks overdue loans and
loans due within 3 days. If the card is not in the list after an update,
reload the browser page.

## Use the command line tool

Put your accounts in `~/.config/cardiff-library/accounts.toml`. Make the file
readable only by you.

```toml
[[account]]
label = "Ana"
card = "21234567890123"
pin = "1234"
```

Then run the tool:

```sh
cardiff-library
cardiff-library --html ~/library-loans.html
```

The first command prints the loans. The second also writes a page of cover
cards and opens it.

## Keep account details private

The tool and the integration show your labels, not the names from the library
site. Home Assistant stores the card number and PIN in its own config storage.

## Develop

```sh
nix develop
pip install -e ".[dev]"
python -m pytest
```

Tests replay cassettes with the network blocked, so they never reach the
live site. `tests/scrub.py` keeps an allowed list of fields and drops names,
card numbers, PINs and session numbers. Read any new cassette before you
commit it.
