const DAY = 24 * 60 * 60 * 1000;

const STYLE = `
  ha-card { padding: 16px; }
  h2 { margin: 0 0 12px; font-size: 20px; font-weight: 400; }
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

function collectLoans(hass) {
  const loans = [];
  for (const entity of Object.values(hass.entities || {})) {
    if (entity.platform !== "cardiff_library") continue;
    const state = hass.states[entity.entity_id];
    if (!state) continue;
    for (const loan of state.attributes.loans || []) {
      loans.push({ ...loan, account: state.attributes.account });
    }
  }
  return loans.sort((a, b) => (a.due || "").localeCompare(b.due || "") || (a.account || "").localeCompare(b.account || ""));
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
  }

  set hass(hass) {
    const loans = collectLoans(hass);
    const key = JSON.stringify(loans) + new Date().toDateString();
    if (key === this._key) return;
    this._key = key;
    this._render(loans, new Date());
  }

  _render(loans, today) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const card = element("ha-card");
    card.append(element("h2", "", this._config.title || "Library loans"));
    if (!loans.length) {
      card.append(element("div", "empty", "No books on loan."));
    } else {
      const grid = element("div", "grid");
      for (const loan of loans) grid.append(this._loan(loan, today));
      card.append(grid);
    }
    const style = element("style", "", STYLE);
    this.shadowRoot.replaceChildren(style, card);
  }

  _loan(loan, today) {
    const days = daysUntil(loan.due, today);
    const item = element("div", `loan ${days < 0 ? "late" : days <= 3 ? "soon" : ""}`);
    const cover = element("div", loan.cover ? "cover has-image" : "cover", loan.cover ? undefined : loan.title);
    if (loan.cover) {
      const image = element("img");
      image.src = loan.cover;
      image.alt = "";
      image.loading = "lazy";
      cover.append(image);
    }
    const date = new Date(`${loan.due}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
    item.append(
      cover,
      element("div", "title", loan.title),
      element("div", "meta", `${loan.account} · ${date}`),
      element("div", "due", dueText(days)),
    );
    return item;
  }

  getCardSize() {
    return 6;
  }

  static getStubConfig() {
    return {};
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
