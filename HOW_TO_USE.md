# How to use Arizona Deal Agent

The agent is a **CLI**. Point it at a listings file. It scores every property on
price, profitability, and affordability, ranks them, and can **transmit** the
top pick as a shareable recommendation.

In-product guide (prints this path and the named scenarios):

```bash
arizona-deal-agent howto
```

## 60 seconds

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

| Step | Command |
| ---- | ------- |
| Rank the sample catalog | `arizona-deal-agent rank -i data/sample_listings.csv --top 5` |
| Keep only what you can buy | `arizona-deal-agent rank -i data/sample_listings.csv --max-price 350000 --budget-cash 90000 --min-cash-flow 0` |
| Open the winner | `arizona-deal-agent explain -i data/sample_listings.csv --id AZ-003` |
| Score a deal not in a file | `arizona-deal-agent score --price 240000 --rent 2100 --rehab 15000 --arv 330000` |
| Transmit the top pick | `arizona-deal-agent transmit -i data/sample_listings.csv --to "Investment team"` |

Without installing: prefix the same commands with
`PYTHONPATH=src python3 -m arizona_deal_agent`.

## Named scenarios

Each named scenario is a `rank` recipe you can print or run:

```bash
arizona-deal-agent howto --run balanced
arizona-deal-agent howto --run profit
arizona-deal-agent howto --run affordability
arizona-deal-agent howto --run tight
```

Against `data/sample_listings.csv`:

| Scenario | What it does | Sample winner |
| -------- | ------------ | ------------- |
| `balanced` | Default weights (price 0.25 / profit 0.40 / afford 0.35), top 5 | AZ-003 3110 E Fort Lowell Rd, Tucson (84.8) |
| `profit` | `--weight-profit 1` (returns only) | AZ-012 5402 S 12th Ave, Tucson (65.6) |
| `affordability` | `--weight-afford 1` (rent coverage / headroom) | AZ-003 3110 E Fort Lowell Rd, Tucson (100.0) |
| `tight` | `--max-price 350000 --budget-cash 90000 --min-cash-flow 0` | AZ-003 only — everything else is filtered out |

Budget flags are hard filters. Add `--include-over-budget` on `rank` if you want
over-limit rows visible and marked instead of dropped.

## Commands

| Command | Purpose |
| ------- | ------- |
| `howto` | Print this path, or `--run` a named scenario |
| `rank` | Score a `.csv` / `.json` listings file |
| `explain` | Full purchase / monthly / returns breakdown for one `--id` |
| `score` | Same breakdown from flags (`--price` and `--rent` required) |
| `transmit` | Copy-paste recommendation for the current top deal |

`rank` and `transmit` share the same filters (`--city`, `--max-price`,
`--budget-cash`, `--min-cash-flow`, `--min-cap-rate`, score weights).

## Bring your own listings

`-i` accepts `.csv` or `.json`. Required columns: `id`, `list_price`,
`monthly_rent`. Spreadsheet-style values (`$385,000`) and common aliases
(`price`, `rent`, `arv`) work. See the README table for the full column list.

## How the score works

Three 0–100 scores, then a weighted composite (defaults 0.25 / 0.40 / 0.35).
Scores are anchored to fixed benchmarks, not to the other rows in the file.
Override the mix with `--weight-price`, `--weight-profit`, `--weight-afford`.

Financing defaults are a conventional 30-year investor loan (20% down, 6.5%,
3% closing). `--rate 6.5` and `--rate 0.065` mean the same thing.

## Output formats

```bash
arizona-deal-agent rank -i data/sample_listings.csv --format json
arizona-deal-agent rank -i data/sample_listings.csv --format csv
arizona-deal-agent transmit -i data/sample_listings.csv --format json
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Flags, scoring math, and every command (including `howto`) are covered there.
The long-form reference — assumptions table, Python API, and scope notes — is
in `README.md`.
