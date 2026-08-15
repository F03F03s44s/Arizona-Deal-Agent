const $ = (sel) => document.querySelector(sel);

const money = (x) =>
  x >= 1_000_000 ? `$${(x / 1_000_000).toFixed(2)}M` : `$${Math.round(x).toLocaleString()}`;
const pct = (x, digits = 0) => `${(x * 100).toFixed(digits)}%`;

const TYPE_LABELS = {
  single_family: "Single family",
  townhouse: "Townhouse",
  condo: "Condo",
  multi_family: "Multi-family",
  manufactured: "Manufactured",
  land: "Land",
  other: "Other",
};

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function loadCities() {
  const cities = await fetchJSON("/api/cities");
  const select = $("#city");
  for (const { city, count } of cities) {
    const opt = document.createElement("option");
    opt.value = city;
    opt.textContent = `${city} (${count})`;
    select.appendChild(opt);
  }
}

function currentQuery() {
  const params = new URLSearchParams();
  if ($("#city").value) params.set("city", $("#city").value);
  if ($("#max-price").value) params.set("max_price", $("#max-price").value);
  if ($("#min-beds").value) params.set("min_beds", $("#min-beds").value);
  if ($("#property-type").value) params.set("property_type", $("#property-type").value);
  params.set("limit", "100");
  return params;
}

function scoreClass(score) {
  if (score >= 65) return "good";
  if (score >= 45) return "mid";
  return "poor";
}

function renderStats(deals, total) {
  const el = $("#stats");
  if (!deals.length) { el.innerHTML = ""; return; }
  const median = (arr) => {
    const s = [...arr].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const yields = deals.filter((d) => d.gross_yield != null).map((d) => d.gross_yield);
  const stats = [
    ["Deals ranked", total.toLocaleString()],
    ["Top score", deals[0].deal_score.toFixed(1)],
    ["Median price", money(median(deals.map((d) => d.listing.price)))],
    ["Median est. yield", yields.length ? pct(median(yields), 1) : "—"],
  ];
  el.innerHTML = stats
    .map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`)
    .join("");
}

function dealCard(deal, rank) {
  const listing = deal.listing;
  const cls = scoreClass(deal.deal_score);
  const discount = deal.discount_vs_market;
  const discountHtml =
    discount == null
      ? ""
      : discount >= 0
        ? `<span class="delta-good">${pct(discount)} below market</span>`
        : `<span class="delta-bad">${pct(-discount)} above market</span>`;
  const chips = deal.reasons
    .map((r) => `<span class="chip${r.startsWith("Watch") || r.startsWith("No sqft") ? " warn" : ""}">${r}</span>`)
    .join("");
  const bars = [
    ["Price vs. market (40%)", deal.breakdown.value],
    ["Rental yield (30%)", deal.breakdown.yield],
    ["Seller motivation (20%)", deal.breakdown.motivation],
    ["Property risk (10%)", deal.breakdown.risk],
  ]
    .map(
      ([label, v]) => `
      <div class="bar-row">
        <span>${label}</span>
        <div class="bar"><span style="width:${v}%"></span></div>
        <b>${Math.round(v)}</b>
      </div>`
    )
    .join("");
  const facts = [
    ["List price", money(listing.price)],
    ["$ / sqft", deal.price_per_sqft ? `$${Math.round(deal.price_per_sqft)} (mkt median $${Math.round(deal.market_median_ppsf)})` : "—"],
    ["Est. monthly rent", deal.est_monthly_rent ? money(deal.est_monthly_rent) : "—"],
    ["Est. gross yield", deal.gross_yield != null ? pct(deal.gross_yield, 1) : "—"],
    ["Days on market", listing.days_on_market ?? "—"],
    ["Price cut so far", deal.price_cut_pct ? pct(deal.price_cut_pct, 1) : "None"],
    ["Year built", listing.year_built ?? "—"],
    ["HOA", listing.hoa_monthly ? `$${listing.hoa_monthly}/mo` : "None"],
    ["Confidence", deal.confidence],
  ]
    .map(([k, v]) => `<li><span>${k}</span><span>${v}</span></li>`)
    .join("");

  const size = [
    listing.beds ? `${listing.beds} bd` : null,
    listing.baths ? `${listing.baths} ba` : null,
    listing.sqft ? `${Math.round(listing.sqft).toLocaleString()} sqft` : null,
    TYPE_LABELS[listing.property_type] || listing.property_type,
  ]
    .filter(Boolean)
    .join(" · ");

  return `
  <article class="deal" data-id="${listing.id}">
    <div class="deal-main" role="button" aria-expanded="false" tabindex="0">
      <div class="rank">#${rank}<small>rank</small></div>
      <div class="score ${cls}">${deal.deal_score.toFixed(0)}<small>SCORE</small></div>
      <div class="addr">
        ${listing.address}, ${listing.city} ${listing.zip_code ?? ""}
        <div class="sub">${size}</div>
        <div class="chips">${chips}</div>
      </div>
      <div class="nums">
        <div class="price">${money(listing.price)}</div>
        <div class="metric">${deal.price_per_sqft ? `$${Math.round(deal.price_per_sqft)}/sqft` : ""} ${discountHtml}</div>
        <div class="metric">${deal.est_monthly_rent ? `Est. rent <b>${money(deal.est_monthly_rent)}/mo</b>` : ""}</div>
      </div>
    </div>
    <div class="deal-detail">
      <div><h4>Why this score</h4>${bars}</div>
      <div><h4>Deal facts</h4><ul class="facts">${facts}</ul></div>
    </div>
  </article>`;
}

async function refresh() {
  const results = $("#results");
  results.setAttribute("aria-busy", "true");
  try {
    const data = await fetchJSON(`/api/deals?${currentQuery()}`);
    renderStats(data.deals, data.total);
    if (!data.deals.length) {
      results.innerHTML = `<div class="empty">No deals match these filters. Try widening the search.</div>`;
    } else {
      results.innerHTML = data.deals.map((d, i) => dealCard(d, i + 1)).join("");
    }
    $("#dataset-pill").textContent = `${data.total} listings ranked`;
  } catch (err) {
    results.innerHTML = `<div class="empty">Failed to load deals: ${err.message}</div>`;
  } finally {
    results.removeAttribute("aria-busy");
  }
}

document.addEventListener("click", (e) => {
  const main = e.target.closest(".deal-main");
  if (main) {
    const card = main.closest(".deal");
    card.classList.toggle("open");
    main.setAttribute("aria-expanded", card.classList.contains("open"));
  }
});

for (const id of ["#city", "#max-price", "#min-beds", "#property-type"]) {
  $(id).addEventListener("change", refresh);
}
$("#reset").addEventListener("click", () => {
  for (const id of ["#city", "#max-price", "#min-beds", "#property-type"]) $(id).value = "";
  refresh();
});

loadCities().then(refresh).catch(() => refresh());
