# Arizona-Deal-Agent

Lowest most profitable, most affordable deal-finding agent.

The agent scrapes live Phoenix-area Craigslist listings, prices each one against
comparable listings, and ranks them by blending two signals:

- **Profit margin** — how far under the going rate the item is listed.
- **Affordability** — how little of your budget the deal consumes.

A single tunable `profit_weight` (0–1) trades profit against affordability, and
the agent surfaces the best deal that still fits your budget. Saved searches
re-run on a schedule and email you when something scores above your threshold.

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

| Method | Path                              | Description                                       |
| ------ | --------------------------------- | ------------------------------------------------- |
| GET    | `/api/health`                     | Health check.                                     |
| GET    | `/api/deals`                      | Scrape (or serve cached) Phoenix listings.        |
| POST   | `/api/rank`                       | Rank deals against a budget and profit weight.    |
| GET    | `/api/saved-searches`             | List saved searches.                              |
| POST   | `/api/saved-searches`             | Save a search and check it immediately.           |
| POST   | `/api/saved-searches/{id}/run`    | Re-run one saved search now.                      |
| DELETE | `/api/saved-searches/{id}`        | Delete a saved search.                            |
| GET    | `/api/alerts`                     | Alert emails the agent has sent, newest first.    |

Examples:

```bash
# Rank live listings
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 2000, "profit_weight": 0.6, "query": "power tools"}'

# Get me an email when a cordless drill scores above 0.9
curl -s http://localhost:8000/api/saved-searches \
  -H 'Content-Type: application/json' \
  -d '{"query": "cordless drill", "email": "you@example.com", "min_score": 0.9}'
```

`GET /api/deals?refresh=true` bypasses the scrape cache. If Craigslist is
unreachable the agent falls back to the sample deals in `app/data.py` and says
so in the response's `warning` field.

## Live re-ranking

Scrapes are cached per query (10 minutes by default), so `POST /api/rank` is
pure arithmetic on cached data. That is what lets the UI re-rank on every slider
tick without putting a network call in the request path.

## Email alerts

Saved searches are polled in the background and each matching listing is emailed
exactly once. Configure a real mail server with environment variables:

| Variable             | Default                          | Purpose                                  |
| -------------------- | -------------------------------- | ---------------------------------------- |
| `SMTP_HOST`          | _unset_                          | Mail server. Unset logs alerts instead.  |
| `SMTP_PORT`          | `587`                            | Mail server port.                        |
| `SMTP_USERNAME`      | _unset_                          | Login, if the server requires one.       |
| `SMTP_PASSWORD`      | _unset_                          | Password for `SMTP_USERNAME`.            |
| `SMTP_FROM`          | `arizona-deal-agent@localhost`   | Envelope sender.                         |
| `SMTP_STARTTLS`      | `true`                           | Upgrade the connection before sending.   |
| `ALERT_POLL_SECONDS` | `900`                            | Saved-search poll interval; `0` disables.|
| `DEAL_AGENT_DATA_DIR`| `data`                           | Where saved searches are persisted.      |

With no `SMTP_HOST` set, alerts are written to the application log and still
recorded in `/api/alerts`, so the feature stays observable without credentials.

## Tests

```bash
.venv/bin/python -m pytest
```

Tests never hit the network: the scraper is exercised against a saved real
Craigslist response in `tests/fixtures/`, and the SMTP transport against a
throwaway SMTP server in `tests/smtp_stub.py`.

## Cloud Agent environment

`.cursor/environment.json` provisions this project for Cursor Cloud Agents:
`install` creates the virtualenv and installs dependencies, and the `api`
terminal runs the Uvicorn dev server on port 8000.
