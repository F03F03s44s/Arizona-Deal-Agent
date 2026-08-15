# Arizona Deal Agent

Finds Arizona property deals from public data and ranks them by best value.
Python 3.10+, no third-party dependencies in the core package.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/arizona-deal-agent find --top 10   # search live + bundled sources
.venv/bin/arizona-deal-agent serve           # web UI on http://127.0.0.1:8000
```

Without installing, `PYTHONPATH=src python3 -m arizona_deal_agent` works the
same way.

## How to test

```bash
.venv/bin/python -m pytest
```

No test may touch the network. Stub `arizona_deal_agent.sources.hud_reo.http_get_json`
when a live source is involved, and use the `market` fixture rather than the
packaged snapshot so scores do not move when the snapshot is refreshed.

## Pipeline

`find` → `enrich` → `underwrite` → `rank`, wired together in `pipeline.search`.

| Path | Role |
| --- | --- |
| `src/arizona_deal_agent/sources/` | Discovery: HUD REO feed, CSV/JSON files, bundled sample |
| `src/arizona_deal_agent/market.py` | Arizona ZIP values and rents; snapshot loading and rebuild |
| `src/arizona_deal_agent/enrich.py` | Fills missing price/rent/value and tags each with its origin |
| `src/arizona_deal_agent/finance.py` | Mortgage, NOI, cap rate, DSCR, breakeven price |
| `src/arizona_deal_agent/scoring.py` | Anchored 0-100 curves and the weighted composite |
| `src/arizona_deal_agent/pipeline.py` | Dedupe, filter, score, rank |
| `src/arizona_deal_agent/report.py` | Table, JSON, CSV, and per-deal breakdown |
| `src/arizona_deal_agent/cli.py` | `find`, `rank`, `explain`, `sources`, `serve` |
| `src/arizona_deal_agent/web/` | FastAPI app and the single-page UI |
| `scripts/refresh_market_data.py` | Rebuilds the packaged market snapshot |

## Conventions that matter

- **Never invent a number silently.** Anything not published by a source is
  filled in `enrich.py` and tagged in `DealInputs.provenance`. Reports mark
  estimated prices with `~` and list the estimates used.
- **Scores are anchored, not relative.** Curves in `scoring.py` interpolate
  between fixed benchmarks, so a deal scores the same alone or in a batch.
  Changing an anchor changes every historical score; do it deliberately.
- **Live sources fail gracefully.** `sources.collect` captures a `SourceError`
  per source and keeps going, so a network outage degrades the result set
  instead of aborting the search.
- **The web API accepts built-in source names only.** A file path there would
  let a caller read arbitrary CSV or JSON off the server.
- **The CLI and the API share `report.result_to_dict`**, so the two surfaces
  cannot drift in how they describe a deal.

## Refreshing market data

```bash
python3 scripts/refresh_market_data.py
```

Streams Zillow's national ZHVI and ZORI files, keeps Arizona, and rewrites
`src/arizona_deal_agent/data/az_market.json` (~64 KB). Expect the committed
snapshot to change wholesale; the tests use fixtures, not the snapshot, so they
should stay green.

## Cursor Cloud specific instructions

`.cursor/environment.json` creates `.venv`, installs `.[dev]`, and starts the
API on port 8000 in the `api` terminal. To test the UI manually, open
`http://127.0.0.1:8000`. Egress is required for the HUD feed; without it, `find`
reports the source as failed and still ranks the bundled `sample` listings.
