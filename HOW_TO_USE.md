# How to use Arizona Deal Agent

Arizona Deal Agent scrapes **Phoenix Craigslist** for-sale listings, ranks them
by blending **profit margin** with **affordability**, and recommends the best
in-budget deal. The ranked table updates **live as you drag the slider**. Saved
searches email you when any deal scores **≥ 0.9**.

Use any of three surfaces: the **web UI**, the **command line**, or the **HTTP API**.

## 1. Start the app

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Then open [http://localhost:8000](http://localhost:8000).

If you only want a ranking in the terminal, skip the server and use
`python -m app` (see [Command line](#3-command-line)).

## 2. Web UI

1. **Set Budget ($)** — the cash ceiling. Anything costing more than this is
   marked `over` and cannot be the recommendation.
2. **Drag Profit vs. affordability** — rankings recompute immediately (no button).
   - **0.00** prefers leftover budget.
   - **1.00** prefers the fattest profit margin that still fits.
   - **0.60** (default) is a balanced mix.
3. Optionally filter with a **Craigslist query** (e.g. `desk`, `macbook`).
4. Read the **green recommendation card** and the live table. Rows scoring ≥ 0.9
   are highlighted.
5. **Save a search** with your email to get alerts when score ≥ 0.9.

Click **Refresh listings** only when you want a fresh scrape (otherwise the
10-minute cache is reused while you tune the slider).

### Saved-search email alerts

1. Enter your email and click **Save search (alert ≥ 0.9)**.
2. The agent stores your current budget, profit weight, and optional query.
3. A background loop (default every 5 minutes) re-scrapes and emails matches.
4. Click **Check now** to force an immediate evaluation.

SMTP env vars (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM`) deliver real email. Without SMTP, alerts are appended to
`data/alerts.log` so you can still verify the pipeline.

## 3. Command line

```bash
# Default: scrape Phoenix CL, $15,000 budget, profit weight 0.60
.venv/bin/python -m app

# Prefer leftover budget
.venv/bin/python -m app --budget 15000 --profit-weight 0

# Prefer profit margin + optional query
.venv/bin/python -m app --budget 15000 --profit-weight 1 --query tools --refresh

# Tight budget, machine-readable output
.venv/bin/python -m app --budget 2000 --profit-weight 0.5 --json

# Usage / flags
.venv/bin/python -m app --help
```

## 4. HTTP API

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/deals?refresh=true` | Live Phoenix Craigslist deals |
| `POST` | `/api/rank` | Rank deals (`deals: []` scrapes live) |
| `GET` | `/api/saved-searches` | List saved searches |
| `POST` | `/api/saved-searches` | Create a saved search |
| `DELETE` | `/api/saved-searches/{id}` | Delete a saved search |
| `POST` | `/api/saved-searches/check` | Evaluate searches / send alerts now |

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 15000, "profit_weight": 0.6, "deals": [], "refresh": true}'

curl -s http://localhost:8000/api/saved-searches \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","budget":5000,"profit_weight":0.7,"min_score":0.9}'
```

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs).

## 5. How scoring works

```
normalized_margin        = clamp(0.5 + profit_margin / 2, 0, 1)
normalized_affordability = clamp(1 - cost / budget, 0, 1)
score = profit_weight * normalized_margin
      + (1 - profit_weight) * normalized_affordability
```

Asking price from Craigslist is treated as acquisition cost. Market value is
estimated from category heuristics (furniture, tools, electronics, etc.) plus a
small bump for urgency keywords like “must sell” / “estate”.

If Craigslist blocks the scrape, the agent falls back to a tiny offline sample
catalog so ranking still works.

## 6. Tests

```bash
.venv/bin/python -m pytest
```
