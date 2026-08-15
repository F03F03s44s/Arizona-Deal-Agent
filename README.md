# Arizona-Deal-Agent

Lowest most profitable, most affordable deal-finding agent.

The agent evaluates candidate deals and ranks them by blending two signals:

- **Profit margin** — how much value a deal creates relative to its cost.
- **Affordability** — how little of your budget the deal consumes.

A single tunable `profit_weight` (0–1) trades profit against affordability, and
the agent surfaces the best deal that still fits your budget. **Send** transmits
that recommendation to the built-in inbox, a public webhook, or a local log.

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

## Send a recommendation

From the UI: rank deals, then click **Send recommendation**. Inbox delivers on
this server (Outbox + Inbox update immediately). Webhook POSTs a JSON envelope
to a public `https` URL. Log only records the payload without delivering it.

From the terminal:

```bash
python -m app send --inbox --note "daily pick"
python -m app send --url https://example.com/hooks/deals --format slack
python -m app send --log-only --json
```

Webhook hosts that resolve to loopback, private, or metadata addresses are
rejected. Query-string tokens are not stored; only the hostname is kept on the
audit record.

## API

| Method | Path                 | Description                                         |
| ------ | -------------------- | --------------------------------------------------- |
| GET    | `/api/health`        | Health check.                                       |
| GET    | `/api/deals`         | Seeded sample deals and the default budget.         |
| POST   | `/api/rank`          | Rank deals against a budget and profit weight.      |
| POST   | `/api/send`          | Rank, then transmit to inbox, webhook, or log.      |
| GET    | `/api/transmissions` | Recent outbound sends.                              |
| GET    | `/api/inbox`         | Recent inbound deliveries.                          |
| POST   | `/api/inbox`         | Accept an inbound JSON payload from a partner.      |

Example:

```bash
curl -s http://localhost:8000/api/send \
  -H 'Content-Type: application/json' \
  -d '{"budget": 15000, "profit_weight": 0.6, "destination": "inbox", "note": "daily pick"}'
```

When `deals` is empty the built-in Arizona sample deals are used.

The send payload uses schema `arizona-deal-agent.transmission.v1` and includes
`recommendation`, optional `ranked`, `budget`, `profit_weight`, and `note`.

## Tests

```bash
.venv/bin/python -m pytest
```

## Cloud Agent environment

`.cursor/environment.json` provisions this project for Cursor Cloud Agents:
`install` creates the virtualenv and installs dependencies, and the `api`
terminal runs the Uvicorn dev server on port 8000.
