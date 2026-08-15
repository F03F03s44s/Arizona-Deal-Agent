"use strict";

const $ = (id) => document.getElementById(id);

const form = $("search-form");
const statusEl = $("status");
const summaryEl = $("summary");
const bestEl = $("best");
const tableWrap = $("table-wrap");
const tbody = $("results-body");
const placeholder = $("placeholder");
const drawer = $("drawer");
const drawerBody = $("drawer-body");
const scrim = $("scrim");

let lastDeals = [];

/* ---------- formatting ---------- */

const money = (n, dash = "—") => {
  if (n === null || n === undefined || Number.isNaN(n)) return dash;
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.round(Math.abs(n)).toLocaleString("en-US")}`;
};

const percent = (n, digits = 1) =>
  n === null || n === undefined || Number.isNaN(n) ? "—" : `${(n * 100).toFixed(digits)}%`;

const ratio = (n) => (n === null || n === undefined ? "n/a" : n.toFixed(2));

const signClass = (n) => (n >= 0 ? "pos" : "neg");

const scoreClass = (n) => (n >= 60 ? "s-high" : n >= 40 ? "s-mid" : "");

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])
  );

/* ---------- market vintage ---------- */

async function loadMarket() {
  try {
    const res = await fetch("/api/market");
    const m = await res.json();
    $("vintage").innerHTML =
      `Market data: <b>${m.zip_count}</b> Arizona ZIPs &middot; ` +
      `values &amp; rents as of <b>${m.value_as_of || "—"}</b><br />` +
      `Zillow ZHVI / ZORI &middot; median ${money(m.median_value)} &middot; ${money(m.median_rent)}/mo rent`;
  } catch {
    $("vintage").textContent = "Market data unavailable";
  }
}

/* ---------- weights ---------- */

function syncWeights() {
  const d = Number($("w_discount").value);
  const p = Number($("w_profit").value);
  const a = Number($("w_afford").value);
  const total = d + p + a || 1;
  $("w-discount-out").textContent = `${Math.round((d / total) * 100)}%`;
  $("w-profit-out").textContent = `${Math.round((p / total) * 100)}%`;
  $("w-afford-out").textContent = `${Math.round((a / total) * 100)}%`;
}

["w_discount", "w_profit", "w_afford"].forEach((id) =>
  $(id).addEventListener("input", syncWeights)
);

/* ---------- search ---------- */

function buildBody() {
  const sources = [...document.querySelectorAll('input[name="source"]:checked')].map((el) => el.value);
  const num = (id) => {
    const raw = $(id).value.trim();
    return raw === "" ? null : Number(raw);
  };
  const cities = $("cities").value.split(",").map((s) => s.trim()).filter(Boolean);

  return {
    sources,
    cities,
    top: 60,
    include_over_budget: $("include_over_budget").checked,
    max_price: num("max_price"),
    budget_cash: num("budget_cash"),
    min_cash_flow: num("min_cash_flow"),
    down_payment: Number($("down_payment").value) || 0,
    rate: Number($("rate").value) || 0,
    weight_discount: Number($("w_discount").value) / 100,
    weight_profit: Number($("w_profit").value) / 100,
    weight_afford: Number($("w_afford").value) / 100,
  };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = buildBody();
  if (body.sources.length === 0) {
    statusEl.textContent = "Pick at least one source.";
    statusEl.className = "status error";
    return;
  }

  $("submit").disabled = true;
  statusEl.className = "status";
  statusEl.textContent = "Searching Arizona sources…";

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    render(data);
    statusEl.textContent = `Ranked ${data.deals.length} of ${data.counts.found} candidates.`;
  } catch (error) {
    statusEl.className = "status error";
    statusEl.textContent = String(error.message || error);
  } finally {
    $("submit").disabled = false;
  }
});

/* ---------- rendering ---------- */

function render(data) {
  lastDeals = data.deals;
  placeholder.hidden = true;
  renderSummary(data);
  renderBest(data.best);
  renderTable(data.deals);
}

function renderSummary(data) {
  const chips = [
    `<span class="chip">Found <b>${data.counts.found}</b></span>`,
    `<span class="chip">Ranked <b>${data.counts.ranked}</b></span>`,
  ];
  data.sources.forEach((s) => {
    const cls = s.error ? "chip warn" : "chip";
    const value = s.error ? "failed" : `<b>${s.count}</b>`;
    chips.push(`<span class="${cls}">${escapeHtml(s.name)} ${value}</span>`);
  });
  if (data.counts.over_budget) {
    chips.push(`<span class="chip">Over budget <b>${data.counts.over_budget}</b></span>`);
  }
  data.errors.forEach((e) => chips.push(`<span class="chip warn">${escapeHtml(e)}</span>`));
  summaryEl.innerHTML = chips.join("");
  summaryEl.hidden = false;
}

function renderBest(best) {
  if (!best) {
    bestEl.innerHTML =
      '<div class="panel placeholder"><h2>No deals matched</h2>' +
      "<p>Loosen a filter or turn on another source, then search again.</p></div>";
    return;
  }
  const u = best.underwriting;
  const estimated = best.inputs.price_is_estimated;
  bestEl.innerHTML = `
    <article class="best">
      <div class="best-head">
        <div>
          <div class="best-tag">Best value</div>
          <h2>${escapeHtml(best.address || best.id)}</h2>
          <div class="where">${escapeHtml(best.location)} &middot; ${escapeHtml(best.source)}${
            best.status ? ` &middot; ${escapeHtml(best.status)}` : ""
          }</div>
        </div>
        <div class="big-score">
          <div class="value">${best.scores.composite.toFixed(1)}</div>
          <div class="label">best value / 100</div>
        </div>
      </div>
      <div class="stats">
        <div class="stat"><div class="k">Price</div><div class="v ${estimated ? "est" : ""}">${
          estimated ? "~" : ""
        }${money(best.inputs.price)}</div></div>
        <div class="stat"><div class="k">Rent</div><div class="v">${money(best.inputs.monthly_rent)}</div></div>
        <div class="stat"><div class="k">Cash flow</div><div class="v ${signClass(
          u.monthly_cash_flow
        )}">${money(u.monthly_cash_flow)}/mo</div></div>
        <div class="stat"><div class="k">Cap rate</div><div class="v">${percent(u.cap_rate)}</div></div>
        <div class="stat"><div class="k">Cash to close</div><div class="v">${money(u.cash_to_close)}</div></div>
      </div>
      <ul class="reasons">${best.reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      ${
        best.warnings.length
          ? `<div class="notice">${best.warnings.map(escapeHtml).join(" &middot; ")}</div>`
          : ""
      }
    </article>`;
}

function renderTable(deals) {
  tbody.innerHTML = deals
    .map((deal, index) => {
      const u = deal.underwriting;
      const estimated = deal.inputs.price_is_estimated;
      const live = deal.source.startsWith("hud");
      return `
      <tr data-index="${index}" class="${deal.fits_budget ? "" : "miss"}">
        <td class="num">${index + 1}</td>
        <td class="addr">${escapeHtml(deal.address || deal.id)}<small>${escapeHtml(
        deal.location
      )}</small></td>
        <td><span class="tag ${live ? "live" : ""}">${escapeHtml(deal.source)}</span></td>
        <td class="num ${estimated ? "est" : ""}">${estimated ? "~" : ""}${money(deal.inputs.price)}</td>
        <td class="num">${money(deal.inputs.monthly_rent)}</td>
        <td class="num ${signClass(u.monthly_cash_flow)}">${money(u.monthly_cash_flow)}</td>
        <td class="num">${percent(u.cap_rate)}</td>
        <td class="num"><span class="score-pill ${scoreClass(
          deal.scores.composite
        )}">${deal.scores.composite.toFixed(1)}</span></td>
      </tr>`;
    })
    .join("");
  tableWrap.hidden = deals.length === 0;
}

/* ---------- detail drawer ---------- */

tbody.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-index]");
  if (row) openDrawer(lastDeals[Number(row.dataset.index)]);
});

function dl(pairs) {
  return `<dl class="dl">${pairs
    .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`)
    .join("")}</dl>`;
}

function bar(label, value, isTotal = false) {
  return `<div class="bar-row ${isTotal ? "total" : ""}">
    <span>${label}</span>
    <span class="bar"><i style="width:${Math.max(0, Math.min(100, value))}%"></i></span>
    <span class="n">${value.toFixed(0)}</span>
  </div>`;
}

function openDrawer(deal) {
  if (!deal) return;
  const u = deal.underwriting;
  const i = deal.inputs;
  const labels = i.provenance_labels || {};

  const facts = [
    deal.beds ? `${deal.beds} bd` : null,
    deal.baths ? `${deal.baths} ba` : null,
    deal.sqft ? `${deal.sqft.toLocaleString("en-US")} sqft` : null,
    deal.year_built ? `built ${deal.year_built}` : null,
  ].filter(Boolean);

  drawerBody.innerHTML = `
    <h2>${escapeHtml(deal.address || deal.id)}</h2>
    <div class="where">${escapeHtml(deal.location)} &middot; ${escapeHtml(deal.source)}${
    facts.length ? ` &middot; ${facts.join(" · ")}` : ""
  }</div>

    <div class="dsection">
      <h3>Best value score</h3>
      <div class="bars">
        ${bar("Discount", deal.scores.discount)}
        ${bar("Profitability", deal.scores.profitability)}
        ${bar("Affordability", deal.scores.affordability)}
        ${bar("Composite", deal.scores.composite, true)}
      </div>
    </div>

    <div class="dsection">
      <h3>Market (${escapeHtml(i.provenance.market_scope || "—")})</h3>
      ${dl([
        ["Typical value", `${money(i.market_value)}<small>${escapeHtml(labels.market_value || "")}</small>`],
        ["Typical rent", `${money(i.monthly_rent)}/mo<small>${escapeHtml(labels.rent || "")}</small>`],
      ])}
    </div>

    <div class="dsection">
      <h3>Purchase</h3>
      ${dl([
        ["Price", `${money(i.price)}<small>${escapeHtml(labels.price || "")}</small>`],
        ["Rehab budget", money(i.rehab_cost)],
        ["Total cost basis", money(u.total_cost_basis)],
        ["Down payment", money(u.down_payment)],
        ["Closing costs", money(u.closing_costs)],
        ["Cash to close", `<b>${money(u.cash_to_close)}</b>`],
      ])}
    </div>

    <div class="dsection">
      <h3>Monthly</h3>
      ${dl([
        ["Market rent", money(i.monthly_rent)],
        ["Mortgage payment", money(u.monthly_payment)],
        ["Taxes, insurance, HOA", money(u.monthly_carrying_cost - u.monthly_payment)],
        ["Carrying cost", money(u.monthly_carrying_cost)],
        [
          "Cash flow",
          `<b class="${signClass(u.monthly_cash_flow)}">${money(u.monthly_cash_flow)}</b>`,
        ],
      ])}
    </div>

    <div class="dsection">
      <h3>Returns</h3>
      ${dl([
        ["Cap rate", percent(u.cap_rate, 2)],
        ["Cash-on-cash", percent(u.cash_on_cash, 2)],
        ["DSCR", ratio(u.dscr)],
        ["Gross yield", percent(u.gross_yield, 2)],
        ["Net operating income", `${money(u.net_operating_income)}/yr`],
        ["70%-rule max offer", money(u.max_allowable_offer)],
        ["Breakeven price", money(u.breakeven_price)],
        ["Equity capture", money(u.equity_capture)],
      ])}
    </div>

    <div class="dsection">
      <h3>Why it scored this way</h3>
      <ul class="reasons">${deal.reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
    </div>

    ${
      deal.warnings.length
        ? `<div class="dsection"><h3>Estimates used</h3><ul class="reasons">${deal.warnings
            .map((w) => `<li>${escapeHtml(w)}</li>`)
            .join("")}</ul></div>`
        : ""
    }
    ${
      deal.budget_misses.length
        ? `<div class="dsection"><h3>Budget misses</h3><ul class="reasons">${deal.budget_misses
            .map((w) => `<li>${escapeHtml(w)}</li>`)
            .join("")}</ul></div>`
        : ""
    }
    ${
      deal.url
        ? `<div class="dsection"><a class="chip" href="${escapeHtml(
            deal.url
          )}" target="_blank" rel="noopener">Open the source listing &rarr;</a></div>`
        : ""
    }`;

  drawer.hidden = false;
  scrim.hidden = false;
}

function closeDrawer() {
  drawer.hidden = true;
  scrim.hidden = true;
}

$("drawer-close").addEventListener("click", closeDrawer);
scrim.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeDrawer();
});

syncWeights();
loadMarket();
