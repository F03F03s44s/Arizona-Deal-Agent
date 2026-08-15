# How to use Arizona Deal Agent

Arizona Deal Agent ranks a catalog of deals and recommends the one that is
**most profitable and most affordable** for a cash budget. Over-budget deals
stay in the table so you can see them, but they are never recommended.

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

The home page is the operator console.

1. **Set Budget ($)** — the cash ceiling. Anything costing more than this is
   marked `over` and cannot be the recommendation.
2. **Move Profit vs. affordability** — this is `profit_weight` from 0 to 1.
   - **0.00** prefers leftover budget (cheap relative to the ceiling).
   - **1.00** prefers the fattest profit margin, as long as it still fits.
   - **0.60** (default) is a balanced mix.
3. **Pick a scenario** or click **Rank deals**.
4. Read the **green recommendation card**. That is the agent's pick.
5. Scan the table. Rank `#1` is best. Faded rows are over budget.

The slider helper text updates as you drag so you can see which signal is
winning before you re-rank.

### Built-in scenarios

| Scenario | Budget | Weight | Recommendation |
| -------- | ------ | ------ | -------------- |
| Balanced | $15,000 | 0.60 | Estate-sale tool collection (Tempe) |
| Max profit | $15,000 | 1.00 | Wholesale patio furniture lot (Tucson) |
| Max affordability | $15,000 | 0.00 | Estate-sale tool collection (Tempe) |
| Tight $2,000 | $2,000 | 0.50 | Estate-sale tool collection (Tempe); Corolla, MacBooks, and the mobile home drop to `over` |

### Sample catalog (what you are ranking)

| ID | Deal | Cost | Market value |
| -- | ---- | ---- | ------------ |
| az-001 | 2015 Toyota Corolla (Phoenix) | $8,200 | $11,200 |
| az-002 | Wholesale patio furniture lot (Tucson) | $1,500 | $3,200 |
| az-003 | Fixer-upper mobile home (Mesa) | $42,000 | $61,000 |
| az-004 | Refurbished MacBook lot (Scottsdale) | $5,400 | $6,100 |
| az-005 | Estate-sale tool collection (Tempe) | $650 | $1,800 |

On the default $15,000 / 0.60 run the mobile home is over budget. The agent
recommends the Tempe estate-sale tools (high margin, tiny cash outlay). Slide
all the way to profit and the Tucson patio-furniture lot wins instead.

## 3. Command line

```bash
# Default: $15,000 budget, profit weight 0.60
.venv/bin/python -m app

# Prefer leftover budget
.venv/bin/python -m app --budget 15000 --profit-weight 0

# Prefer profit margin
.venv/bin/python -m app --budget 15000 --profit-weight 1

# Tight budget, machine-readable output
.venv/bin/python -m app --budget 2000 --profit-weight 0.5 --json

# Usage / flags
.venv/bin/python -m app --help
```

The text report prints the recommendation first, then a ranked table. `--json`
prints the same payload the API returns.

## 4. HTTP API

With the server running:

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/` | Operator UI |
| `GET` | `/api/health` | Liveness + version |
| `GET` | `/api/deals` | Sample catalog + default budget |
| `POST` | `/api/rank` | Rank deals for a budget and weight |

### Rank the sample catalog

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 15000, "profit_weight": 0.6, "deals": []}'
```

An empty `deals` array means “use the built-in Arizona sample catalog.”

### Rank your own deals

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{
    "budget": 10000,
    "profit_weight": 0.7,
    "deals": [
      {
        "id": "az-custom-1",
        "title": "Storage-unit pallet (Chandler)",
        "category": "wholesale",
        "acquisition_cost": 2200,
        "market_value": 4800
      },
      {
        "id": "az-custom-2",
        "title": "Used work van (Glendale)",
        "category": "auto",
        "acquisition_cost": 9500,
        "market_value": 12000
      }
    ]
  }'
```

### Response shape

```json
{
  "budget": 15000,
  "profit_weight": 0.6,
  "recommendation": {
    "deal": { "id": "az-002", "title": "…", "acquisition_cost": 1500, "market_value": 3200 },
    "profit": 1700,
    "profit_margin": 1.1333,
    "affordability": 0.9,
    "score": 0.8667,
    "within_budget": true
  },
  "ranked": [ "…scored deals, best first…" ]
}
```

`recommendation` is `null` when every deal is over budget.

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs).

## 5. How scoring works

For each deal the agent computes two signals, then blends them:

1. **Profit margin** = `(market_value - acquisition_cost) / acquisition_cost`.
   A 100% margin maps near 1.0; break-even maps near 0.5. Extreme flips are
   clamped so one outlier cannot dominate.
2. **Affordability** = `1 - acquisition_cost / budget`.
   A cheap deal relative to the ceiling scores high. Over-budget deals get a
   negative affordability and `within_budget = false`.
3. **Score** = `profit_weight * margin + (1 - profit_weight) * affordability`.

Sort order is: in-budget first, then highest score. The recommendation is the
first in-budget row.

Change the demo catalog in `app/data.py`. Change the blend math in `app/agent.py`.

## 6. Tests

```bash
.venv/bin/python -m pytest
```

That covers the ranking engine, HTTP API, and CLI report.

## 7. Cursor Cloud Agents

`.cursor/environment.json` installs dependencies into `.venv` and starts the
API on port 8000. After a Cloud Agent boots, open port 8000 for the UI, or run
`.venv/bin/python -m app` / `.venv/bin/python -m pytest` in the workspace.
