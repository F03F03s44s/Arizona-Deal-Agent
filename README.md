# Arizona Deal Agent

Lowest-cost, most profitable, most affordable deal-finding agent.

The agent ranks candidate deals by blending **profit margin** with
**affordability** (how little of your budget a deal consumes). A single
`profit_weight` (0–1) trades those two signals. Over-budget deals sort last
and are never recommended.

**Start here:** [How to use](HOW_TO_USE.md)

## How to use (60 seconds)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

1. Open [http://localhost:8000](http://localhost:8000).
2. Enter a **Budget ($)**.
3. Drag **Profit vs. affordability** (or click a scenario).
4. Click **Rank deals**.
5. Take the green **Agent recommendation**. Faded rows are over budget.

No browser? Rank the same catalog from the terminal:

```bash
.venv/bin/python -m app
.venv/bin/python -m app --budget 2000 --profit-weight 0.5
.venv/bin/python -m app --help
```

## API

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/deals` | Sample deals and default budget |
| `POST` | `/api/rank` | Rank deals for a budget and profit weight |

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 15000, "profit_weight": 0.6, "deals": []}'
```

Empty `deals` uses the built-in Arizona sample catalog. Interactive docs:
[http://localhost:8000/docs](http://localhost:8000/docs).

## Tests

```bash
.venv/bin/python -m pytest
```

## Cloud Agent environment

`.cursor/environment.json` creates `.venv`, installs dependencies, and starts
the API on port 8000 for Cursor Cloud Agents.
