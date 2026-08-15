# Arizona-Deal-Agent

Lowest most profitable, most affordable deal-finding agent.

The agent evaluates candidate deals and ranks them by blending two signals:

- **Profit margin** — how much value a deal creates relative to its cost.
- **Affordability** — how little of your budget the deal consumes.

A single tunable `profit_weight` (0–1) trades profit against affordability, and
the agent surfaces the best deal that still fits your budget.

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

| Method | Path          | Description                                  |
| ------ | ------------- | -------------------------------------------- |
| GET    | `/api/health` | Health check.                                |
| GET    | `/api/deals`  | Seeded sample deals and the default budget.  |
| POST   | `/api/rank`   | Rank deals against a budget and profit weight. |

Example:

```bash
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 15000, "profit_weight": 0.6, "deals": []}'
```

When `deals` is empty the built-in Arizona sample deals are used.

## Tests

```bash
.venv/bin/python -m pytest
```

## Cloud Agent environment

`.cursor/environment.json` provisions this project for Cursor Cloud Agents:
`install` creates the virtualenv and installs dependencies, and the `api`
terminal runs the Uvicorn dev server on port 8000.
