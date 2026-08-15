# Arizona Deal Agent

Finds Arizona real-estate deals and ranks them by best value. Every listing gets a transparent **Deal Score (0–100)** so the cheapest-*and*-most-profitable properties rise to the top.

## How the ranking works

| Component | Weight | What it measures |
|---|---|---|
| Price vs. market | 40% | Listing $/sqft vs. the city's median $/sqft (below market = good) |
| Rental yield | 30% | Estimated gross yield: city rent/sqft × size × 12 ÷ price |
| Seller motivation | 20% | Days on market + price cuts already taken (negotiating room) |
| Property risk | 10% | Age of the home and HOA drag (capex/carry proxy) |

Each component is scored 0–100, blended by weight, and every deal ships with human-readable reasons (e.g. *"21% below Surprise median $/sqft"*, *"Est. gross rental yield 7.8%"*) plus a confidence level based on data completeness. City baselines live in `deal_agent/market.py` and are easy to tune.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Web app + API
uvicorn deal_agent.api:app --port 8000
# open http://localhost:8000

# Or rank deals in the terminal
python -m deal_agent.cli --top 10 --why
python -m deal_agent.cli --city Phoenix --max-price 450000
```

## Data sources

- **Bundled sample dataset** (default): 68 realistic AZ listings across 18 cities in `data/sample_listings.json`, regenerable via `python scripts/generate_sample_data.py`.
- **Real CSV exports**: point the agent at a CSV — including an unmodified Redfin "Download All" export — and it ranks real listings:
  ```bash
  python -m deal_agent.cli --csv my_redfin_export.csv
  DEAL_AGENT_CSV=my_redfin_export.csv uvicorn deal_agent.api:app
  ```
- **Next step**: live MLS/portal APIs can be added behind `deal_agent/sources.py:load_listings()` without touching the scorer or UI.

## API

| Endpoint | Description |
|---|---|
| `GET /api/deals` | Ranked deals; filters: `city`, `max_price`, `min_beds`, `min_score`, `property_type`, `limit` |
| `GET /api/deals/{id}` | One deal with full score breakdown |
| `GET /api/cities` | Cities in the dataset with counts and median price |
| `GET /api/health` | Health check |

## Tests

```bash
pytest
```

## Disclaimer

Rent and market baselines are city-level estimates for triage, not appraisals — verify comps before making offers.
