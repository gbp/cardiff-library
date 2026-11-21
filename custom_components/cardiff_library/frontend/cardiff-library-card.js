const DAY = 24 * 60 * 60 * 1000;
const STORAGE_KEY = "cardiff-library-card";
const SORTS = { due: "Due date", title: "Title" };

const STYLE = `
  ha-card { padding: 16px; }
  h2 { margin: 0 0 12px; font-size: 20px; font-weight: 400; }
  .controls { display: flex; flex-wrap: wrap; gap: 6px 16px; margin-bottom: 12px; }
  .group { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip {
    font: inherit; font-size: 12px; padding: 4px 10px; border-radius: 16px; cursor: pointer;
    border: 1px solid var(--divider-color, #ccc); background: none; color: var(--primary-text-color);
  }
  .chip[aria-pressed="true"] {
    background: var(--primary-color, #03a9f4); border-color: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
  }
  .grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); }
  .loan { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .cover {
    aspect-ratio: 2 / 3; border-radius: 6px; overflow: hidden; display: grid; place-items: center;
    background: var(--secondary-background-color); color: var(--secondary-text-color);
    padding: 6px; text-align: center; font-size: 12px; margin-bottom: 4px;
  }
  .cover.has-image { padding: 0; }
  .cover img { width: 100%; height: 100%; object-fit: cover; }
  .title { font-weight: 500; font-size: 13px; line-height: 1.3; overflow-wrap: anywhere; }
  .meta { color: var(--secondary-text-color); font-size: 12px; }
  .due { font-size: 12px; font-weight: 500; }
  .late .due { color: var(--error-color, #db4437); }
  .soon .due { color: var(--warning-color, #ffa600); }
  .empty { color: var(--secondary-text-color); }
`;

function daysUntil(due, today) {
  const [year, month, day] = due.split("-").map(Number);
  return Math.round((Date.UTC(year, month - 1, day) - Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())) / DAY);
}

function dueText(days) {
  if (days < 0) return `overdue ${-days}d`;
  if (days === 0) return "due today";
  return `due in ${days}d`;
}

function collect(hass) {
  const accounts = [];
  const loans = [];
  for (const entity of Object.values(hass.entities || {})) {
    if (entity.platform !== "cardiff_library") continue;
    const state = hass.states[entity.entity_id];
    if (!state || !state.attributes.account) continue;
    accounts.push(state.attributes.account);
    for (const loan of state.attributes.loans || []) {
      loans.push({ ...loan, account: state.attributes.account });
    }
  }
  return { accounts: accounts.sort(), loans };
}

function sortLoans(loans, sort) {
  const byTitle = (a, b) => (a.title || "").localeCompare(b.title || "", undefined, { sensitivity: "base" });
  // A loan without a due date goes last.
  const byDue = (a, b) => (a.due || "~").localeCompare(b.due || "~");
  const byAccount = (a, b) => (a.account || "").localeCompare(b.account || "");
  return [...loans].sort((a, b) =>
    sort === "title" ? byTitle(a, b) || byDue(a, b) : byDue(a, b) || byAccount(a, b) || byTitle(a, b),
  );
}

// The key holds the card's settings, so a change in the card editor starts
// fresh from the new settings, and cards with other settings keep their own
// choice.
function storageKey(config) {
  return `${STORAGE_KEY}:${JSON.stringify([config.account || "", config.sort || ""])}`;
}

// Storage can be missing or blocked, for example in a private window.
function readChoice(config) {
  try {
    return JSON.parse(localStorage.getItem(storageKey(config))) || {};
  } catch {
    return {};
  }
}

function saveChoice(config, choice) {
  try {
    localStorage.setItem(storageKey(config), JSON.stringify(choice));
  } catch {
    // The choice then lasts only until the page reloads.
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

class CardiffLibraryCard extends HTMLElement {
  _config = {};

  setConfig(config) {
    this._config = config || {};
    const saved = readChoice(this._config);
    this._account = saved.account ?? this._config.account ?? "";
    this._sort = saved.sort ?? this._config.sort ?? "due";
    if (this._data) this._draw();
  }

  set hass(hass) {
    const data = collect(hass);
    const key = JSON.stringify(data) + new Date().toDateString();
    if (key === this._key) return;
    this._key = key;
    this._data = data;
    this._draw();
  }

  _choose(change) {
    Object.assign(this, change);
    saveChoice(this._config, { account: this._account, sort: this._sort });
    this._draw();
  }

  _draw() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const { accounts, loans } = this._data;
    const account = accounts.includes(this._account) ? this._account : "";
    const shown = sortLoans(account ? loans.filter((loan) => loan.account === account) : loans, this._sort);
    const today = new Date();

    const card = element("ha-card");
    card.append(element("h2", "", this._config.title || "Library loans"), this._controls(accounts, account));
    if (!shown.length) {
      card.append(element("div", "empty", "No books on loan."));
    } else {
      const grid = element("div", "grid");
      for (const loan of shown) grid.append(this._loan(loan, today));
      card.append(grid);
    }
    this.shadowRoot.replaceChildren(element("style", "", STYLE), card);
  }

  _controls(accounts, account) {
    const controls = element("div", "controls");
    if (accounts.length > 1) {
      const borrowers = element("div", "group");
      for (const [value, label] of [["", "All"], ...accounts.map((name) => [name, name])]) {
        borrowers.append(this._chip(label, value === account, () => this._choose({ _account: value })));
      }
      controls.append(borrowers);
    }
    const sorts = element("div", "group");
    for (const [value, label] of Object.entries(SORTS)) {
      sorts.append(this._chip(label, value === this._sort, () => this._choose({ _sort: value })));
    }
    controls.append(sorts);
    return controls;
  }

  _chip(label, pressed, onClick) {
    const chip = element("button", "chip", label);
    chip.type = "button";
    chip.setAttribute("aria-pressed", String(pressed));
    chip.addEventListener("click", onClick);
    return chip;
  }

  _loan(loan, today) {
    const days = loan.due ? daysUntil(loan.due, today) : null;
    const state = days === null ? "" : days < 0 ? "late" : days <= 3 ? "soon" : "";
    const item = element("div", `loan ${state}`);
    const cover = element("div", loan.cover ? "cover has-image" : "cover", loan.cover ? undefined : loan.title);
    if (loan.cover) {
      const image = element("img");
      image.src = loan.cover;
      image.alt = "";
      image.loading = "lazy";
      cover.append(image);
    }
    const date = loan.due
      ? new Date(`${loan.due}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })
      : "no due date";
    item.append(
      cover,
      element("div", "title", loan.title),
      element("div", "meta", `${loan.account} · ${date}`),
      element("div", "due", days === null ? "" : dueText(days)),
    );
    return item;
  }

  getCardSize() {
    return 6;
  }

  static getStubConfig() {
    return {};
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "account", selector: { text: {} } },
        {
          name: "sort",
          selector: {
            select: { mode: "dropdown", options: Object.entries(SORTS).map(([value, label]) => ({ value, label })) },
          },
        },
      ],
      computeLabel: (field) =>
        ({ title: "Title", account: "Start with this borrower (empty for all)", sort: "Start sorted by" })[field.name],
    };
  }
}

// The script can load twice, for example as an old cached copy, and a second
// define would throw.
if (!customElements.get("cardiff-library-card")) {
  customElements.define("cardiff-library-card", CardiffLibraryCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "cardiff-library-card",
    name: "Library loans",
    description: "Books on loan from every Cardiff Libraries account, with covers and due dates.",
    preview: true,
  });
}
