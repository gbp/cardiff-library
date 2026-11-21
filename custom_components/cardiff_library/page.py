from datetime import date
from html import escape

from .parsing import Loan

STYLE = """
:root {
  --bg: #f7f5f2; --card: #ffffff; --text: #1d1b19; --muted: #6b655e;
  --line: #e4dfd8; --late: #b3261e; --soon: #9a6700; --cover: #e9e4dc;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161514; --card: #211f1d; --text: #f1ede8; --muted: #a49d94;
    --line: #34312d; --late: #ff8a80; --soon: #f2c14e; --cover: #2c2926;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 16px; background: var(--bg); color: var(--text);
  font: 15px/1.4 system-ui, -apple-system, sans-serif;
}
header { max-width: 1100px; margin: 0 auto 20px; }
h1 { margin: 0; font-size: 24px; }
header p { margin: 4px 0 0; color: var(--muted); }
main {
  max-width: 1100px; margin: 0 auto; display: grid; gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
}
article {
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  overflow: hidden; display: flex; flex-direction: column;
}
.cover {
  aspect-ratio: 2 / 3; background: var(--cover); display: grid;
  place-items: center; padding: 12px; text-align: center; color: var(--muted);
}
.cover img { width: 100%; height: 100%; object-fit: cover; }
.cover:has(img) { padding: 0; }
.body { padding: 10px 12px 12px; display: grid; gap: 4px; }
h2 { margin: 0; font-size: 15px; }
.author, .status { color: var(--muted); font-size: 13px; }
.who {
  justify-self: start; font-size: 12px; padding: 1px 8px; border-radius: 999px;
  border: 1px solid var(--line);
}
.due { font-weight: 600; font-size: 13px; }
.late .due { color: var(--late); }
.soon .due { color: var(--soon); }
"""


def when(due: date, today: date) -> str:
    days = (due - today).days
    if days < 0:
        return f"OVERDUE {-days}d"
    if days == 0:
        return "today"
    return f"{days}d"


def render_page(rows: list[tuple[str, Loan]], today: date) -> str:
    cards = "\n".join(
        _card(label, loan, today)
        for label, loan in sorted(rows, key=lambda row: (row[1].due, row[0]))
    )
    count = "1 book" if len(rows) == 1 else f"{len(rows)} books"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Library loans</title>
<style>{STYLE}</style>
</head>
<body>
<header><h1>Library loans</h1><p>{count} on loan, checked {today:%a %d %b %Y}</p></header>
<main>
{cards or "<p>No books on loan.</p>"}
</main>
</body>
</html>
"""


def _card(label: str, loan: Loan, today: date) -> str:
    days = (loan.due - today).days
    state = "late" if days < 0 else "soon" if days <= 3 else ""
    cover = (
        f'<img src="{escape(loan.cover)}" alt="" loading="lazy">'
        if loan.cover
        else escape(loan.title)
    )
    author = f'<div class="author">{escape(loan.author)}</div>' if loan.author else ""
    status = f'<div class="status">{escape(loan.status)}</div>' if loan.status else ""
    return (
        f'<article class="{state}">'
        f'<div class="cover">{cover}</div>'
        f'<div class="body"><h2>{escape(loan.title)}</h2>{author}'
        f'<div class="due">Due {loan.due:%a %d %b} · {when(loan.due, today)}</div>'
        f'{status}<span class="who">{escape(label)}</span></div>'
        "</article>"
    )
