import { deals, marketOptions } from "./deals-data.js";
import {
  filterDeals,
  formatCurrency,
  formatPercent,
  rankDeals,
  scoreDeal,
} from "./ranking.js";

const state = {
  market: "All Arizona",
  query: "",
  type: "All homes",
  maxPrice: "",
  minBeds: "0",
  lens: "balanced",
  sort: "score",
  saved: new Set(),
  showingSaved: false,
  renderedDeals: [],
};

const elements = {
  marketTabs: document.querySelector("#marketTabs"),
  dealSearch: document.querySelector("#dealSearch"),
  typeFilter: document.querySelector("#typeFilter"),
  priceFilter: document.querySelector("#priceFilter"),
  bedFilter: document.querySelector("#bedFilter"),
  clearFilters: document.querySelector("#clearFilters"),
  dealGrid: document.querySelector("#dealGrid"),
  emptyState: document.querySelector("#emptyState"),
  emptyReset: document.querySelector("#emptyReset"),
  resultCount: document.querySelector("#resultCount"),
  sortSelect: document.querySelector("#sortSelect"),
  lensButtons: document.querySelectorAll(".lens-button"),
  savedNavCount: document.querySelector("#savedNavCount"),
  refreshButton: document.querySelector("#refreshButton"),
  updatedAt: document.querySelector("#updatedAt"),
  modal: document.querySelector("#dealModal"),
  modalImage: document.querySelector("#modalImage"),
  modalLabel: document.querySelector("#modalLabel"),
  modalTitle: document.querySelector("#modalTitle"),
  modalLocation: document.querySelector("#modalLocation"),
  modalScore: document.querySelector("#modalScore"),
  modalGap: document.querySelector("#modalGap"),
  modalYield: document.querySelector("#modalYield"),
  modalInsight: document.querySelector("#modalInsight"),
  modalSave: document.querySelector("#modalSave"),
  discoverNav: document.querySelector('a[href="#deals"]'),
  savedNav: document.querySelector('a[href="#saved"]'),
};

const compactMoney = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 0,
  }).format(value);

const cardTemplate = (deal, index) => {
  const isSaved = state.saved.has(deal.id);
  const isFeatured = state.sort === "score" && index === 0;
  const label = deal.valueRank === 1 ? "Top value" : `#${deal.valueRank} value`;

  return `
    <article class="deal-card ${isFeatured ? "featured-card" : ""}" data-deal-id="${deal.id}">
      <div class="deal-image">
        <img src="${deal.image}" alt="${deal.title} in ${deal.neighborhood}" loading="${index > 2 ? "lazy" : "eager"}" />
        <div class="rank-badge">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.6 14.6 8.8l5.7.8-4.1 4 .97 5.65L12 16.55l-5.1 2.7.97-5.65-4.1-4 5.67-.8L12 3.6Z" fill="currentColor"/></svg>
          ${label}
        </div>
        <button class="save-button ${isSaved ? "saved" : ""}" data-save="${deal.id}" type="button" aria-label="${isSaved ? "Remove" : "Save"} ${deal.title}" aria-pressed="${isSaved}">
          <svg viewBox="0 0 24 24" fill="${isSaved ? "currentColor" : "none"}" aria-hidden="true"><path d="M6.5 4.5h11v15l-5.5-3.4-5.5 3.4v-15Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
        </button>
      </div>
      <div class="deal-body">
        <div class="deal-topline">
          <div>
            <div class="deal-location"><span class="location-pin"></span>${deal.neighborhood}, ${deal.city}</div>
            <h3 class="deal-title">${deal.title}</h3>
          </div>
          <div class="score-ring" style="--score: ${deal.valueScore}" aria-label="Value score ${deal.valueScore} out of 99">
            <strong>${deal.valueScore}</strong>
          </div>
        </div>
        <div class="price-row">
          <strong>${formatCurrency(deal.price)}</strong>
          <span>${deal.beds} bd · ${deal.baths} ba · ${deal.sqft.toLocaleString()} sq ft</span>
        </div>
        <div class="quick-stats">
          <div class="quick-stat"><span>Value gap</span><strong>${compactMoney(deal.valueGap)}</strong></div>
          <div class="quick-stat"><span>Net yield</span><strong>${formatPercent(deal.netYield)}</strong></div>
          <div class="quick-stat"><span>Cash / mo.</span><strong>${compactMoney(deal.monthlyCashFlow)}</strong></div>
        </div>
        <div class="deal-footer">
          <span class="deal-tag">${deal.tag}</span>
          <button class="analyze-button" data-open-deal="${deal.id}" type="button">View analysis →</button>
        </div>
      </div>
    </article>
  `;
};

function renderMarkets() {
  elements.marketTabs.innerHTML = marketOptions
    .map(
      (market) => `
        <button
          class="market-tab ${market === state.market ? "active" : ""}"
          data-market="${market}"
          type="button"
          role="tab"
          aria-selected="${market === state.market}"
        >${market === "All Arizona" ? "All AZ" : market}</button>`,
    )
    .join("");
}

function scoreAndSortDeals() {
  const filteredDeals = filterDeals(deals, {
    market: state.market,
    query: state.query,
    type: state.type,
    maxPrice: state.maxPrice,
    minBeds: state.minBeds,
  });

  const ranked = rankDeals(filteredDeals, state.lens).map((deal, index) => ({
    ...deal,
    valueRank: index + 1,
  }));
  const shortlist = state.showingSaved
    ? ranked.filter((deal) => state.saved.has(deal.id))
    : ranked;

  return [...shortlist].sort((left, right) => {
    if (state.sort === "price") return left.price - right.price;
    if (state.sort === "yield") return right.netYield - left.netYield;
    if (state.sort === "gap") return right.valueGap - left.valueGap;
    return left.valueRank - right.valueRank;
  });
}

function renderDeals() {
  const visibleDeals = scoreAndSortDeals();
  state.renderedDeals = visibleDeals;
  const countLabel = `${visibleDeals.length} ${visibleDeals.length === 1 ? "deal" : "deals"}`;

  elements.resultCount.textContent = countLabel;
  elements.dealGrid.hidden = visibleDeals.length === 0;
  elements.emptyState.hidden = visibleDeals.length !== 0;
  elements.dealGrid.innerHTML = visibleDeals.map(cardTemplate).join("");

  document.querySelector(".results-header .section-kicker").textContent = state.showingSaved
    ? "Your saved shortlist"
    : "Curated for your brief";
  document.querySelector(".results-header h2").childNodes[0].textContent = state.showingSaved
    ? "Saved contenders "
    : "Best value, first ";
  updateSavedNavigation();
}

function updateSavedNavigation() {
  const savedCount = state.saved.size;
  elements.savedNavCount.textContent = savedCount;
  elements.savedNavCount.style.display = savedCount ? "inline-block" : "none";
  elements.savedNav.classList.toggle("active", state.showingSaved);
  elements.discoverNav.classList.toggle("active", !state.showingSaved);
}

function resetFilters() {
  state.market = "All Arizona";
  state.query = "";
  state.type = "All homes";
  state.maxPrice = "";
  state.minBeds = "0";
  state.showingSaved = false;
  elements.dealSearch.value = "";
  elements.typeFilter.value = "All homes";
  elements.priceFilter.value = "";
  elements.bedFilter.value = "0";
  renderMarkets();
  renderDeals();
}

function getCurrentDeal(id) {
  const baseDeal = deals.find((deal) => deal.id === id);
  return baseDeal ? scoreDeal(baseDeal, state.lens) : null;
}

function updateModalSaveButton(deal) {
  const isSaved = state.saved.has(deal.id);
  elements.modalSave.dataset.save = deal.id;
  elements.modalSave.textContent = isSaved ? "Saved to shortlist" : "Save to shortlist";
}

function openModal(id) {
  const deal = getCurrentDeal(id);
  if (!deal) return;

  elements.modalImage.src = deal.image;
  elements.modalImage.alt = `${deal.title} in ${deal.neighborhood}`;
  elements.modalLabel.textContent = deal.valueScore >= 80 ? "High-conviction opportunity" : "Worth a closer look";
  elements.modalTitle.textContent = deal.title;
  elements.modalLocation.textContent = `${deal.neighborhood}, ${deal.city} · ${deal.type}`;
  elements.modalScore.textContent = `${deal.valueScore}/99`;
  elements.modalGap.textContent = compactMoney(deal.valueGap);
  elements.modalYield.textContent = formatPercent(deal.netYield);
  elements.modalInsight.textContent = deal.detail;
  updateModalSaveButton(deal);
  elements.modal.classList.add("open");
  elements.modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeModal() {
  elements.modal.classList.remove("open");
  elements.modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

function toggleSaved(id) {
  if (state.saved.has(id)) {
    state.saved.delete(id);
  } else {
    state.saved.add(id);
  }
  renderDeals();
  const deal = getCurrentDeal(id);
  if (deal && elements.modal.classList.contains("open")) updateModalSaveButton(deal);
}

elements.marketTabs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-market]");
  if (!button) return;
  state.market = button.dataset.market;
  state.showingSaved = false;
  renderMarkets();
  renderDeals();
});

elements.dealSearch.addEventListener("input", (event) => {
  state.query = event.target.value;
  state.showingSaved = false;
  renderDeals();
});

elements.typeFilter.addEventListener("change", (event) => {
  state.type = event.target.value;
  state.showingSaved = false;
  renderDeals();
});

elements.priceFilter.addEventListener("change", (event) => {
  state.maxPrice = event.target.value;
  state.showingSaved = false;
  renderDeals();
});

elements.bedFilter.addEventListener("change", (event) => {
  state.minBeds = event.target.value;
  state.showingSaved = false;
  renderDeals();
});

elements.clearFilters.addEventListener("click", resetFilters);
elements.emptyReset.addEventListener("click", resetFilters);

elements.lensButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.lens = button.dataset.lens;
    state.sort = "score";
    elements.sortSelect.value = "score";
    elements.lensButtons.forEach((lensButton) =>
      lensButton.classList.toggle("active", lensButton === button),
    );
    renderDeals();
  });
});

elements.sortSelect.addEventListener("change", (event) => {
  state.sort = event.target.value;
  renderDeals();
});

elements.dealGrid.addEventListener("click", (event) => {
  const saveButton = event.target.closest("[data-save]");
  if (saveButton) {
    toggleSaved(saveButton.dataset.save);
    return;
  }
  const dealButton = event.target.closest("[data-open-deal]");
  if (dealButton) openModal(dealButton.dataset.openDeal);
});

elements.modal.addEventListener("click", (event) => {
  if (event.target.closest("[data-close-modal]")) closeModal();
});

elements.modalSave.addEventListener("click", () => {
  const id = elements.modalSave.dataset.save;
  if (id) toggleSaved(id);
});

elements.refreshButton.addEventListener("click", () => {
  elements.refreshButton.classList.add("is-refreshing");
  elements.updatedAt.textContent = "Scores recalculated just now";
  window.setTimeout(() => elements.refreshButton.classList.remove("is-refreshing"), 700);
  renderDeals();
});

elements.discoverNav.addEventListener("click", () => {
  state.showingSaved = false;
  renderDeals();
});

elements.savedNav.addEventListener("click", (event) => {
  event.preventDefault();
  state.showingSaved = true;
  renderDeals();
  document.querySelector("#deals").scrollIntoView({ behavior: "smooth", block: "start" });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && elements.modal.classList.contains("open")) closeModal();
});

renderMarkets();
renderDeals();
