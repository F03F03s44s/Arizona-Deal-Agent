# Arizona Deal Agent

Finds Arizona property deals from public data and ranks them by best value.

Most deal tools make you bring a spreadsheet. This one goes and looks: it pulls
live Arizona candidates from HUD's public foreclosure feed, fills in the market
value and rent for each ZIP from Zillow's public research data, underwrites
every property with real rental math, and ranks what comes back.

```text
$ arizona-deal-agent find --top 4

#  SOURCE  ADDRESS               CITY              PRICE    RENT  CASH FLOW   CAP    CoC  SCORE
-  ------  --------------------  -------------  --------  ------  ---------  ----  -----  -----
1  sample  3418 E 33rd St        Tucson         $189,000  $1,450        $23  5.8%   0.5%   65.8
2  sample  2216 W Roeser Rd      Phoenix        $289,000  $2,150       -$18  5.6%  -0.3%   63.8
3  sample  1105 E Cottonwood Ln  Casa Grande    $262,000  $1,720      -$195  5.1%  -3.5%   50.7
4  sample  6725 N Highway 95     Bullhead City  $231,000  $1,425      -$243  4.7%  -4.8%   45.3

Found 35 candidate(s), ranked 4. Sources: hud-reo=20, sample=15.

Best value: 3418 E 33rd St, Tucson — score 65.8/100
  - $37,000 below market value (15% equity at close)
  - Cash flow $23/mo
  - Cap rate 5.8% is under the 6% target
  - DSCR 1.02 is below the 1.20 lenders want
  - $35,300 above the 70%-rule offer of $153,700
  - Needs $15,000 of rehab
```

The 20 `hud-reo` rows are live Arizona foreclosures pulled at run time; the
`sample` rows are the bundled offline catalogue. Every row says which source it
came from.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/arizona-deal-agent find --top 10      # search and rank
.venv/bin/arizona-deal-agent serve              # then open http://127.0.0.1:8000
```

The core package has no third-party dependencies. `.[dev]` adds FastAPI and
uvicorn for the web UI, plus pytest.

## How it works

1. **Find.** Each discovery source returns candidate properties. HUD's REO
   feature service is live and needs no API key; you can also point the agent
   at your own CSV or JSON export.
2. **Enrich.** Public feeds publish an address, rarely a price, and never a
   rent. Missing numbers are filled from a packaged Arizona market snapshot and
   tagged with where they came from, so an estimate is never mistaken for a
   listed figure. Estimated prices are marked `~` everywhere they appear.
3. **Underwrite.** Mortgage payment, operating expenses, net operating income,
   cap rate, cash-on-cash, DSCR, cash to close, the 70%-rule max offer, and the
   breakeven purchase price.
4. **Rank.** A weighted composite of discount, profitability, and affordability,
   with your budget applied as a hard filter.

## Where the data comes from

| Source | What it gives | Live? |
| --- | --- | --- |
| [HUD REO feature service](https://egis.hud.gov/arcgis/rest/services/cpdmaps/HudSfReo/MapServer/1) | FHA foreclosures HUD owns in Arizona: address, city, ZIP, coordinates, where each one sits in HUD's disposition pipeline | yes, no key needed |
| [Zillow ZHVI](https://www.zillow.com/research/data/) | Typical home value per ZIP, used for market value and for the price stand-in when a feed publishes none | packaged snapshot |
| [Zillow ZORI](https://www.zillow.com/research/data/) | Typical asking rent per ZIP | packaged snapshot |
| `sample` | 15 bundled Arizona listings for offline demos and tests | no |
| Any `.csv` / `.json` | Your own MLS or agent export | no |

`arizona-deal-agent sources` lists them. The market snapshot covers 302 Arizona
ZIPs and 153 cities; regenerate it with
`python3 scripts/refresh_market_data.py`, which streams the national files and
keeps only Arizona.

### What "price" means for a HUD lead

The HUD feed publishes no asking price. Rather than invent one, the agent uses
the typical value of the surrounding ZIP as a neutral stand-in, marks the row
`~`, and reports two prices that *are* actionable:

- **70%-rule max offer** — `0.70 × market value − rehab`
- **Breakeven price** — the highest price that still breaks even each month

So an unpriced lead is never ranked as if its price were known; it is ranked on
the strength of its market, and the output tells you what to offer.

## Web UI

```bash
.venv/bin/arizona-deal-agent serve --port 8000
```

Pick sources, set a budget, adjust the financing assumptions, and drag the three
weight sliders to change what "best value" means. The top result gets a summary
card; click any row for the full underwriting breakdown, including which numbers
were estimated.

## Command line

```bash
arizona-deal-agent find --top 5                          # live + bundled sources
arizona-deal-agent find --source hud-reo --city Tucson   # live only, one city
arizona-deal-agent find --max-price 350000 --budget-cash 90000 --min-cash-flow 0
arizona-deal-agent rank -i my_listings.csv               # rank a file, no network
arizona-deal-agent explain --id AZ-001                   # full breakdown
arizona-deal-agent rank -i my_listings.csv -f csv > ranked.csv
```

`find` searches live sources; `rank` never leaves the machine. Budget flags are
hard filters, so anything that breaks one disappears — add
`--include-over-budget` to keep those rows visible and marked `!` instead.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness and version |
| `GET` | `/api/sources` | Available discovery sources |
| `GET` | `/api/market` | Coverage and vintage of the market snapshot |
| `POST` | `/api/search` | Run a search and get ranked deals |

```bash
curl -s http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"sources": ["hud-reo", "sample"], "max_price": 350000, "top": 10}'
```

The response is identical to `--format json`. Only built-in source names are
accepted over HTTP; file paths are rejected. Interactive docs at `/docs`.

## Bring your own listings

Pass any `.csv` or `.json` file to `-i`. Column names are matched loosely, so an
MLS export usually loads unedited: `price`/`list_price`, `rent`/`monthly_rent`,
`arv`/`market_value`, `zip`/`zip_code` all resolve to the same field, `$385,000`
and `385000` both parse, and unrecognised columns are kept rather than dropped.

Only an identifier and a price *or* a rent are required — anything else missing
gets filled from the market snapshot for that ZIP.

## How the score works

Every deal gets three 0-100 pillars and a weighted composite.

| Pillar | Built from | Default weight |
| --- | --- | --- |
| Discount | Equity captured at close, against the market value | 0.25 |
| Profitability | Cap rate (0.30), cash-on-cash (0.30), DSCR (0.20), monthly cash flow (0.20) | 0.40 |
| Affordability | Headroom against your budget limits, or rent coverage when no budget is set | 0.35 |

Change the mix with `--weight-discount`, `--weight-profit`, and
`--weight-afford`; the values are normalised, so only their relative size
matters.

Two properties worth knowing:

- Scores are anchored to fixed benchmarks — a 7% cap rate is 70, a 1.25 DSCR is
  75 — not to the other rows in the batch. A property therefore scores the same
  whether it is ranked alone or against a thousand others, and two runs are
  comparable.
- An all-cash purchase has no debt service, so it is scored as fully covering
  it rather than as having failed a coverage test.

## Assumptions you can override

Defaults describe a conventional 30-year investor loan. Percentages accept
either form: `--rate 6.5` and `--rate 0.065` mean the same thing.

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

Taxes default to 0.62% of price a year and insurance to 0.35%, the Arizona
averages, unless the listing carries its own.

## Use it from Python

```python
from arizona_deal_agent import Budget, SearchRequest, search

result = search(SearchRequest(sources=["hud-reo"], budget=Budget(max_price=400_000)))

for deal in result.deals[:5]:
    print(deal.listing.label, deal.score.composite, deal.reasons[0])
```

## Development

```bash
.venv/bin/python -m pytest
```

116 tests cover the finance math against hand-checked values, the score curves,
provenance tagging, file and feed parsing, pipeline dedupe and filtering,
graceful degradation when a live source is down, the CLI, and the API. Nothing
in the suite touches the network.

## Scope

Every number is an estimate built from the inputs above. This is a way to sort a
long list down to the few worth a closer look — not an appraisal, a loan quote,
or investment advice. HUD publishes no asking price, and ZHVI/ZORI describe a
ZIP rather than a specific house, so confirm the real ask and a real rent comp
before making an offer. `sample` data is illustrative, not live listings.
