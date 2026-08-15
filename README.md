# Arizona Deal Agent

MVP that finds Arizona property deals and ranks them by **best value**.

Each listing is scored on three axes — price, profitability, and affordability —
then ranked so the lowest-priced deal that is still profitable and still affordable
floats to the top, with a plain-language explanation of why it won.

**Start here:** `arizona-deal-agent howto` or [HOW_TO_USE.md](HOW_TO_USE.md).

There are currently **two front ends in this repository**, built in parallel and
kept side by side rather than one overwriting the other:

| Front end | Deals it looks at | Where |
| --------- | ----------------- | ----- |
| CLI (`arizona-deal-agent`) | Arizona property listings you supply, scored on mortgage, cap rate and DSCR | `src/arizona_deal_agent/` |
| Web app | Live Phoenix Craigslist for-sale listings, priced against comparable listings | `app/` — see [Web app](#web-app-live-craigslist-deals) |

They share a name and a philosophy, not code. Consolidating them is an open
decision.

## How to use

### 1. Install

Python 3.10 or newer is the only requirement. The tool itself has no dependencies.

Clone the repo, then run these **inside `Arizona-Deal-Agent`** (not your user home folder).

Windows Command Prompt, no Git (download the zip):

```bat
cd C:\Users\%USERNAME%
curl -L -o Arizona-Deal-Agent.zip https://github.com/F03F03s44s/Arizona-Deal-Agent/archive/refs/heads/main.zip
tar -xf Arizona-Deal-Agent.zip
cd Arizona-Deal-Agent-main
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

Windows Command Prompt, with Git:

```bat
git clone https://github.com/F03F03s44s/Arizona-Deal-Agent.git
cd Arizona-Deal-Agent
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

Windows PowerShell (`curl` is an alias here — use `curl.exe`):

```powershell
cd C:\Users\$env:USERNAME
curl.exe -L -o Arizona-Deal-Agent.zip https://github.com/F03F03s44s/Arizona-Deal-Agent/archive/refs/heads/main.zip
tar -xf Arizona-Deal-Agent.zip
cd Arizona-Deal-Agent-main
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -e .
```

macOS / Linux:

```bash
git clone https://github.com/F03F03s44s/Arizona-Deal-Agent.git
cd Arizona-Deal-Agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

That installs the `arizona-deal-agent` command. If you would rather not install anything,
from the repo folder use `python -m arizona_deal_agent` after `set PYTHONPATH=src` (Windows)
or `PYTHONPATH=src python3 -m arizona_deal_agent` (macOS / Linux).

Print the in-tool How to use card (steps plus named scenarios):

```bash
arizona-deal-agent howto
arizona-deal-agent howto --run profit
```

### 2. Find the best-value deals

A sample catalog of 13 Arizona properties ships with the repo. Zero-config:

```bash
arizona-deal-agent find --top 100
```

Or point at your own CSV/JSON:

```bash
arizona-deal-agent rank -i data/sample_listings.csv --top 100
```

```text
#  ID      ADDRESS                CITY            PRICE    RENT  CASH FLOW   CAP    CoC  SCORE
-  ------  ---------------------  -----------  --------  ------  ---------  ----  -----  -----
1  AZ-003  3110 E Fort Lowell Rd  Tucson       $319,000  $2,800       $288  7.0%   4.2%   84.8
2  AZ-012  5402 S 12th Ave        Tucson       $415,000  $3,600       $365  6.8%   3.9%   84.7
3  AZ-011  1420 W Mohave St       Phoenix      $189,000  $1,450        -$4  4.9%  -0.1%   64.1
4  AZ-008  1105 E Cottonwood Ln   Casa Grande  $259,900  $1,650      -$257  4.6%  -4.1%   39.7
5  AZ-009  2870 S Avenue B        Yuma         $239,000  $1,500      -$255  4.7%  -5.0%   38.5

Scored 25 listing(s), showing 25. Best: 3110 E Fort Lowell Rd, Tucson.
  - Strong cash flow at $288/mo
  - DSCR 1.18 is under the 1.20 lenders look for
  - $79,500 above the 70%-rule offer
  - Needs $9,000 of rehab
```

### 3. Narrow it to what you can actually buy

Budget limits are hard filters: anything that breaks one disappears from the list. Add
`--include-over-budget` to keep those rows visible and simply marked as not fitting.

```bash
arizona-deal-agent rank -i data/sample_listings.csv \
  --max-price 350000 --budget-cash 90000 --min-cash-flow 0
```

```text
#  ID      ADDRESS                CITY       PRICE    RENT  CASH FLOW   CAP   CoC  SCORE
-  ------  ---------------------  ------  --------  ------  ---------  ----  ----  -----
1  AZ-003  3110 E Fort Lowell Rd  Tucson  $319,000  $2,800       $288  7.0%  4.2%   74.5
```

Other filters: `--city Tucson` (repeatable), `--min-cap-rate 6`, `--budget-monthly 2000`,
`--top 10`.

### 4. Open up one deal

```bash
arizona-deal-agent explain -i data/sample_listings.csv --id AZ-003
```

```text
AZ-003 - 3110 E Fort Lowell Rd, Tucson
========================================
  4 bd / 2 ba | 1,860 sqft | built 1974 | $172/sqft

PURCHASE
  List price               $319,000
  Rehab budget             $9,000
  Total cost basis         $328,000
  Down payment (20%)       $63,800
  Closing costs (3%)       $9,570
  Cash to close            $82,370

MONTHLY
  Market rent              $2,800
  Mortgage payment         $1,613
  Taxes + insurance        $283
  HOA                      $0
  Carrying cost            $1,896
  Cash flow                $288

ANNUAL
  Effective gross rent     $31,584
  Operating expenses       $8,774
  Net operating income     $22,810
  Debt service             $19,356
  Cash flow                $3,454

RETURNS
  Cap rate                 6.95%
  Cash-on-cash             4.19%
  DSCR                     1.18
  Price-to-rent            9.49
  Rent coverage            1.48
  70%-rule max offer       $239,500
  Equity capture           -$79,500

SCORES (0-100)
  Price                    95.1
  Profitability            65.1
  Affordability            100.0
  Composite                84.8
```

### 5. Check a deal you have not put in a file yet

```bash
arizona-deal-agent score --price 240000 --rent 2100 --rehab 15000 --arv 330000
```

Same breakdown as `explain`, straight from the flags. Only `--price` and `--rent` are
required; taxes and insurance are estimated from the price when you leave them out.

### 6. Transmit the top pick

Format the best deal as a copy-paste-ready message for email or chat:

```bash
arizona-deal-agent transmit -i data/sample_listings.csv --to "Investment team"
```

```text
To: Investment team

ARIZONA DEAL RECOMMENDATION
============================
3110 E Fort Lowell Rd, Tucson (AZ-003)
Score 84.8/100 — price 95, profit 65, afford 100

List price:    $319,000
Monthly rent:  $2,800
Cash flow:     $288/mo
Cap rate:      7.0%
Cash to close: $82,370

Why this deal:
  • Strong cash flow at $288/mo
  • DSCR 1.18 is under the 1.20 lenders look for
  • $79,500 above the 70%-rule offer

— Arizona Deal Agent
```

Use `--format json` to pipe the recommendation into another tool. Budget filters
(`--max-price`, `--budget-cash`, and so on) apply before the top deal is chosen.

## Bring your own listings

Pass any `.csv` or `.json` file to `-i`. Only three columns are required:

| Column | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Unique identifier, used by `explain --id` |
| `list_price` | yes | Asking price |
| `monthly_rent` | yes | Expected market rent |
| `address`, `city`, `zip_code` | no | Labels for the output |
| `beds`, `baths`, `sqft`, `year_built` | no | Shown in `explain` |
| `annual_taxes` | no | Defaults to 0.62% of price, the Arizona average |
| `annual_insurance` | no | Defaults to 0.35% of price |
| `monthly_hoa` | no | Defaults to 0 |
| `rehab_cost` | no | Added to the cost basis and to cash to close |
| `arv` | no | After-repair value; unlocks the 70%-rule numbers |

Values may be written the way a spreadsheet exports them: `$385,000` and `385000` both work.
Common aliases (`price`, `rent`, `hoa`, `zip`, `taxes`, `after_repair_value`) are recognised,
and columns the tool does not know about are ignored, so an MLS export usually loads unedited.

## How the score works

Every deal gets three 0-100 scores and a weighted composite.

| Score | Built from | Weight |
| --- | --- | --- |
| Price | Price-to-rent ratio, or equity below the 70%-rule offer when an ARV is given | 0.25 |
| Profitability | Cap rate (0.30), cash-on-cash (0.30), DSCR (0.20), monthly cash flow (0.20) | 0.40 |
| Affordability | Headroom against your budget limits, or rent coverage when no budget is set | 0.35 |

Change the mix with `--weight-price`, `--weight-profit` and `--weight-afford`. The values are
normalised, so `--weight-profit 1 --weight-price 0 --weight-afford 0` ranks purely on returns.

Two properties of the scoring worth knowing:

- Scores are anchored to fixed benchmarks (7% cap rate scores 70, 1.25 DSCR scores 75, and so
  on), not to the other rows in your file. A property therefore scores the same whether you
  rank it alone or against a thousand others.
- Supplying an ARV can only raise the price score, never lower it. A rental is not penalised
  for being a poor flip.

## Assumptions you can override

Defaults describe a conventional 30-year investor loan. Percentages accept either form:
`--rate 6.5` and `--rate 0.065` mean the same thing.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--down-payment` | 20% | Share of price paid in cash |
| `--rate` | 6.5% | Annual interest rate |
| `--term` | 30 | Loan term in years |
| `--closing-costs` | 3% | Closing costs as a share of price |
| `--vacancy` | 6% | Vacancy allowance against gross rent |
| `--maintenance` | 8% | Maintenance reserve, share of gross rent |
| `--management` | 8% | Property management, share of gross rent |
| `--flip-rule` | 70% | ARV multiplier behind the max allowable offer |

## Output formats

`--format table` (default) is for reading, `--format json` for piping into something else, and
`--format csv` for a spreadsheet.

```bash
arizona-deal-agent rank -i data/sample_listings.csv --format json | jq '.deals[0].scores'
arizona-deal-agent rank -i data/sample_listings.csv --format csv > ranked.csv
```

## Use it from Python

```python
from arizona_deal_agent import Assumptions, Budget, load_listings, rank_listings

deals = rank_listings(
    load_listings("data/sample_listings.csv"),
    Assumptions(down_payment_pct=0.25, interest_rate=0.06),
    Budget(max_cash_to_close=100_000),
)

best = deals[0]
print(best.listing.label, round(best.composite_score, 1), best.notes)
```

## Web app: topic pages from allowlisted sources

A second front end in `app/` has a page per topic — houses, household items,
electronics, furniture, cars, tools, gold, silver, diamonds, designer, luxury
and rare items, coins, Pokémon cards, sports cards, jerseys, bulk sales,
pallets, bundles, big sales, and free items with a high estimated return.
An open page
**re-pulls live listings about every 45 seconds** so new posts show up without
a reload. Live rows come from allowlisted Craigslist sections and, when
`EBAY_OAUTH_TOKEN` is set, the official eBay Browse API. Listing URLs must be
HTTPS on craigslist.org or ebay.com; unknown hosts, shorteners, and gift-card /
wire / crypto / replica titles are dropped. Houses also include the curated
Arizona catalog plus official Zillow / Redfin / Realtor.com lookup links. Those
sites and eBay HTML pages are **not** scraped. This checks the **site**, not
every seller.

The UI re-ranks as you drag a profit-vs-affordability slider.

```bash
pip install -e ".[dev,web]"
.venv/bin/uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

### Where the numbers come from

Craigslist only publishes an asking price, so market value is **estimated from
comparable listings in the same search**: the median asking price of other
listings whose titles share meaningful words with it. A listing well under that
median is what the agent treats as profit.

Listings with no real comparables are dropped rather than priced against an
unrelated cohort — a search for power tools also drags in loafers and used cars,
and pricing those off the rest of the results would invent margins that do not
exist. Listings under $20 are ignored as placeholders.

Craigslist's search pages are a JavaScript app and the legacy `format=rss`
endpoint answers 403, so `app/craigslist.py` reads the JSON search service the
site's own front end calls, decoding its position-encoded rows.

### API

| Method | Path                           | Description                                    |
| ------ | ------------------------------ | ---------------------------------------------- |
| GET    | `/api/health`                  | Health check.                                  |
| GET    | `/api/deals`                   | Scrape (or serve cached) Phoenix listings.     |
| POST   | `/api/rank`                    | Rank deals against a budget and profit weight. |
| GET    | `/api/saved-searches`          | List saved searches.                           |
| POST   | `/api/saved-searches`          | Save a search and check it immediately.        |
| POST   | `/api/saved-searches/{id}/run` | Re-run one saved search now.                   |
| DELETE | `/api/saved-searches/{id}`     | Delete a saved search.                         |
| GET    | `/api/alerts`                  | Alert emails the agent has sent, newest first. |

```bash
# Rank live listings
curl -s http://localhost:8000/api/rank \
  -H 'Content-Type: application/json' \
  -d '{"budget": 2000, "profit_weight": 0.6, "query": "power tools"}'

# Get me an email when a cordless drill scores above 0.9
curl -s http://localhost:8000/api/saved-searches \
  -H 'Content-Type: application/json' \
  -d '{"query": "cordless drill", "email": "you@example.com", "min_score": 0.9}'
```

`GET /api/deals?refresh=true` bypasses the scrape cache. If Craigslist is
unreachable the agent falls back to the sample deals in `app/data.py` and says
so in the response's `warning` field.

### Live re-ranking

Scrapes are cached per query (10 minutes by default), so `POST /api/rank` is
pure arithmetic on cached data. That is what lets the UI re-rank on every slider
tick without putting a network call in the request path. A new search query is
the one thing that does re-scrape, so it waits for Enter rather than firing on
each keystroke.

### Email alerts

Saved searches are polled in the background and each matching listing is emailed
exactly once. Configure a real mail server with environment variables:

| Variable              | Default                        | Purpose                                   |
| --------------------- | ------------------------------ | ----------------------------------------- |
| `SMTP_HOST`           | _unset_                        | Mail server. Unset logs alerts instead.   |
| `SMTP_PORT`           | `587`                          | Mail server port.                         |
| `SMTP_USERNAME`       | _unset_                        | Login, if the server requires one.        |
| `SMTP_PASSWORD`       | _unset_                        | Password for `SMTP_USERNAME`.             |
| `SMTP_FROM`           | `arizona-deal-agent@localhost` | Envelope sender.                          |
| `SMTP_STARTTLS`       | `true`                         | Upgrade the connection before sending.    |
| `ALERT_POLL_SECONDS`  | `900`                          | Saved-search poll interval; `0` disables. |
| `DEAL_AGENT_DATA_DIR` | `.agent-state`                 | Where saved searches are persisted.       |

With no `SMTP_HOST` set, alerts are written to the application log and still
recorded in `/api/alerts`, so the feature stays observable without credentials.

## Development

```bash
pip install -e ".[dev,web]"
pytest
```

The suite covers the finance math against hand-checked values, the scoring curves, file
parsing and every CLI command.

Web app tests live in `tests/web/` and never hit the network: the scraper is
exercised against a saved real Craigslist response in `tests/web/fixtures/`, and
the SMTP transport against a throwaway SMTP server in `tests/web/smtp_stub.py`.
Installing without the `web` extra skips nothing else — the CLI tests do not
import the web stack.

## Scope

The numbers are estimates built from the inputs you supply and the assumptions above. They are
a way to sort a long list down to the few worth a closer look — not an appraisal, a loan quote
or investment advice. `data/sample_listings.csv` is illustrative sample data, not live
listings; replace it with a real export before making decisions.
