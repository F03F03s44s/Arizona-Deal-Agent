# Arizona-Deal-Agent

Lowest most profitable, most affordable deal-finding agent.

The agent scrapes live Phoenix-area Craigslist listings, prices each one against
comparable listings, and ranks them by blending two signals:

- **Profit margin** — how far under the going rate the item is listed.
- **Affordability** — how little of your budget the deal consumes.

A single tunable `profit_weight` (0–1) trades profit against affordability, and
the agent surfaces the best deal that still fits your budget.

## Where the numbers come from

Craigslist only publishes an asking price, so market value is **estimated from
comparable listings in the same search**: the median asking price of other
listings whose titles share meaningful words with it. A listing well under that
median is what the agent treats as profit.

Listings with no real comparables are dropped rather than priced against an
unrelated cohort — a search for power tools also drags in loafers and used cars,
and pricing those off the rest of the results would invent margins that do not
exist. Listings under $20 are ignored as placeholders.

Craigslist's search pages are a JavaScript app and the legacy `format=rss`
endpoint answers 403, so `app/craigslist.py` reads the JSON search service the
site's own front end calls, decoding its position-encoded rows.

## Tech stack

- Python 3.12 + [FastAPI](https://fastapi.tiangolo.com/) for the API
- [Uvicorn](https://www.uvicorn.org/) as the ASGI dev server
- A single-page HTML/JS UI served by FastAPI
- `pytest` for tests

## Getting started

```bash
# 1. Create a virtualenv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Run the dev server (auto-reload)
.venv/bin/uvicorn app.main:app --reload --port 8000

# 3. Open the UI
#    http://localhost:8000
```

## API

| Method | Path          | Description                                    |
| ------ | ------------- | ---------------------------------------------- |
| GET    | `/api/health` | Health check.                                  |
| GET    | `/api/deals`  | Scrape (or serve cached) Phoenix listings.     |
| POST   | `/api/rank`   | Rank deals against a budget and profit weight. |

Example:

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 2000, "profit_weight": 0.6, "query": "power tools"}'
```

`GET /api/deals?refresh=true` bypasses the scrape cache. If Craigslist is
unreachable the agent falls back to the sample deals in `app/data.py` and says
so in the response's `warning` field.

## Tests

```bash
.venv/bin/python -m pytest
```

Tests never hit the network: the scraper is exercised against a saved real
Craigslist response in `tests/fixtures/`.

## Cloud Agent environment

`.cursor/environment.json` provisions this project for Cursor Cloud Agents:
`install` creates the virtualenv and installs dependencies, and the `api`
terminal runs the Uvicorn dev server on port 8000.
