# Arizona Deal Agent

Ranks Phoenix Craigslist deals by blending profit margin with affordability.
Over-budget deals are never recommended. The UI re-ranks live while you drag
the profit/affordability slider. Saved searches email when score ≥ 0.9.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- UI: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- CLI: `.venv/bin/python -m app --help`

Full operator guide: `HOW_TO_USE.md`.

## How to test

```bash
.venv/bin/python -m pytest
```

## Key files

| Path | Role |
| ---- | ---- |
| `app/agent.py` | Scoring and ranking |
| `app/scraper.py` | Phoenix Craigslist scraper |
| `app/data.py` | Live loader + sample fallback |
| `app/alerts.py` | Saved searches and threshold checks |
| `app/emailer.py` | SMTP / local alert delivery |
| `app/main.py` | FastAPI routes + background alert loop |
| `app/cli.py` | `python -m app` |
| `app/static/index.html` | Live UI + saved-search form |
| `tests/` | Engine, scraper, API, alert, and CLI tests |

## Cloud Agent environment

`install` creates `.venv` and installs `requirements.txt`. The `api` terminal
runs Uvicorn on port 8000.
