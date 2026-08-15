# Arizona Deal Agent

Ranks **Phoenix Craigslist** deals by blending profit margin with
affordability. A single `profit_weight` (0–1) trades those two signals.
Over-budget deals sort last and are never recommended. The ranked table
updates live as you drag the slider. Saved searches email you when any
in-budget deal scores ≥ 0.9.

**Start here:** [How to use](HOW_TO_USE.md)

## How to use (60 seconds)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

1. Open [http://localhost:8000](http://localhost:8000).
2. Enter a **Budget ($)**.
3. Drag **Profit vs. affordability** — rankings update live (no button click).
4. Optionally save a search with your email for ≥ 0.9 score alerts.

No browser? Rank live listings from the terminal:

```bash
.venv/bin/python -m app
.venv/bin/python -m app --budget 2000 --profit-weight 0.5 --query desk
.venv/bin/python -m app --help
```

## API

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/deals` | Live Phoenix Craigslist deals |
| `POST` | `/api/rank` | Rank deals for a budget and profit weight |
| `GET/POST` | `/api/saved-searches` | List / create email alert searches |
| `POST` | `/api/saved-searches/check` | Evaluate searches and send alerts now |

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 15000, "profit_weight": 0.6, "deals": [], "refresh": true}'
```

Empty `deals` scrapes Phoenix Craigslist (falls back to sample catalog if the
scrape is blocked). Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs).

## Email alerts

Set SMTP env vars to deliver mail (otherwise alerts are appended to
`data/alerts.log`):

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=you@example.com
export SMTP_PASSWORD=secret
export SMTP_FROM=alerts@example.com
```

Background checks run every `ALERT_CHECK_INTERVAL_SECONDS` (default 300).

## Tests

```bash
.venv/bin/python -m pytest
```

## Cloud Agent environment

`.cursor/environment.json` creates `.venv`, installs dependencies, and starts
the API on port 8000 for Cursor Cloud Agents.
