# Arizona Deal Agent

Finds Arizona deals and ranks them by best value
(price + profitability + affordability).

Two front ends live here, built in parallel and kept side by side:

| Front end | Deals | Code |
| --------- | ----- | ---- |
| CLI (`arizona-deal-agent`) | Arizona property listings you supply | `src/arizona_deal_agent/` |
| Web app (FastAPI) | Live-updating topic pages from allowlisted Craigslist + official eBay | `app/` |

They share a name and a philosophy, not code. Consolidating them is an open
decision — do not delete one to make room for the other without being asked.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,web]"

# CLI
arizona-deal-agent find --top 100

# Web app
.venv/bin/uvicorn app.main:app --reload --port 8000   # http://localhost:8000
```

Without installing, `PYTHONPATH=src python3 -m arizona_deal_agent` runs the CLI
the same way. The CLI is stdlib-only; the `web` extra is what pulls in FastAPI.

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
| `src/arizona_deal_agent/scoring.py` | Composite scoring and ranking |
| `src/arizona_deal_agent/finance.py` | Mortgage, NOI, cap rate, DSCR |
| `src/arizona_deal_agent/sources.py` | CSV/JSON listing loader |
| `src/arizona_deal_agent/report.py` | Table, JSON, CSV, explain, transmit output |
| `src/arizona_deal_agent/cli.py` | Command-line entry point |
| `data/sample_listings.csv` | Sample Arizona listings (tracked input, not runtime state) |
| `app/topics.py` | Topic pages and aliases (houses, household, electronics, …) |
| `app/trust.py` | Allowlisted hosts and scam-signal title filter |
| `app/catalog.py` | Curated Arizona house catalog as web deals |
| `app/resale.py` | Conservative resale floors for free-pile listings |
| `app/ebay.py` | Official eBay Browse API client (token optional) |
| `app/craigslist.py` | Craigslist JSON search scraper (per-topic section) |
| `app/market.py` | Market value estimated from comparable listings |
| `app/deals.py` | Per-topic scrape cache that keeps ranking off the network |
| `app/alerts.py` | Saved searches, dedupe, and SMTP alert emails |
| `app/main.py` | FastAPI routes and the saved-search poller |
| `app/static/index.html` | Single-page UI with live slider re-ranking |
| `tests/` | Finance, scoring, sources, and CLI tests |
| `tests/web/` | Scraper, comparables, cache, alerts, and API tests |

## Cloud Agent environment

`install` creates `.venv` and installs the package with the `dev` and `web`
extras. The `api` terminal serves the web app on port 8000.
