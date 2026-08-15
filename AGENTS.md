# DEALS DEALS DEALS

One product: live deal ranking, Arizona property profit ranking, How to use,
and transmit. The page and the `deals` command are two ways to use the same
product — do not split them back into separate apps.

| How you use it | Deals | Code |
| -------------- | ----- | ---- |
| Command (`deals`) | Arizona property listings you supply | `src/arizona_deal_agent/` |
| Page | Live-updating topic pages from allowlisted Craigslist + official eBay | `app/` |

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,web]"

# Command
deals find --top 100
deals howto
deals transmit --to "Investment team"

# Page
.venv/bin/uvicorn app.main:app --reload --port 8000   # http://localhost:8000
```

Without installing, `PYTHONPATH=src python3 -m arizona_deal_agent` runs the
command the same way. The CLI is stdlib-only; the `web` extra is what pulls in
FastAPI. The old `arizona-deal-agent` command name still works.

## How to test

```bash
.venv/bin/python -m pytest
```

Web app tests are in `tests/web/` with their own `conftest.py`, so the CLI tests
never import the web stack. Neither suite touches the network: the scraper runs
against a saved Craigslist response in `tests/web/fixtures/`, and SMTP against a
throwaway server in `tests/web/smtp_stub.py`.

## Key commands

| Command | Purpose |
| ------- | ------- |
| `howto` | Print How to use, or `--run` a named scenario (`balanced`, `profit`, `affordability`, `tight`, `houses`) |
| `find` | Find Arizona deals and rank by best value (sample catalog by default) |
| `rank` | Score a listings file and show the best deals |
| `explain` | Full breakdown for one listing by id |
| `score` | Score a single deal from command-line flags |
| `transmit` | Format the top deal as a shareable recommendation |

Operator guide: `HOW_TO_USE.md`.

## Key files

| Path | Role |
| ---- | ---- |
| `src/arizona_deal_agent/brand.py` | Product name: DEALS DEALS DEALS |
| `src/arizona_deal_agent/scoring.py` | Composite scoring and ranking |
| `src/arizona_deal_agent/finance.py` | Mortgage, NOI, cap rate, DSCR |
| `src/arizona_deal_agent/sources.py` | CSV/JSON listing loader |
| `src/arizona_deal_agent/report.py` | Table, JSON, CSV, explain, transmit output |
| `src/arizona_deal_agent/cli.py` | Command-line entry point (`deals`) |
| `data/sample_listings.csv` | Sample Arizona listings (tracked input, not runtime state) |
| `app/topics.py` | Topic pages and aliases (houses, household, electronics, …) |
| `app/trust.py` | Allowlisted hosts (HTTPS craigslist.org / ebay.com only) and scam-signal title filter |
| `app/catalog.py` | Curated Arizona house catalog as web deals |
| `app/resale.py` | Conservative resale floors for free-pile listings |
| `app/ebay.py` | Official eBay Browse API client (token optional) |
| `app/craigslist.py` | Craigslist JSON search scraper (per-topic section) |
| `app/market.py` | Market value estimated from comparable listings |
| `app/deals.py` | Per-topic scrape cache that keeps ranking off the network |
| `app/alerts.py` | Saved searches, dedupe, and SMTP alert emails |
| `app/transmit.py` | Shareable recommendation text for the page |
| `app/main.py` | FastAPI routes and the saved-search poller |
| `app/static/index.html` | Single-page UI with live slider re-ranking, How to use, and transmit |
| `tests/` | Finance, scoring, sources, and CLI tests |
| `tests/web/` | Scraper, comparables, cache, alerts, and API tests |

## Cloud Agent environment

`install` creates `.venv` and installs the package with the `dev` and `web`
extras. The `api` terminal serves the page on port 8000.
