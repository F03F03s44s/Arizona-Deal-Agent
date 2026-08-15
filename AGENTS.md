# Arizona Deal Agent

Ranks Arizona sample deals by blending profit margin with affordability.
Over-budget deals are never recommended.

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
| `app/data.py` | Sample catalog and default budget |
| `app/main.py` | FastAPI routes |
| `app/cli.py` | `python -m app` |
| `app/static/index.html` | Operator UI, including How to use + scenarios |
| `tests/` | Engine, API, and CLI tests |

## Cloud Agent environment

`install` creates `.venv` and installs `requirements.txt`. The `api` terminal
runs Uvicorn on port 8000.
