# Arizona Deal Agent

CLI tool that ranks Arizona property deals by price, profitability, and affordability.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
arizona-deal-agent rank -i data/sample_listings.csv --top 5
```

Without installing, `PYTHONPATH=src python3 -m arizona_deal_agent` works the same way.

## How to test

```bash
.venv/bin/python -m pytest
```

## Key commands

| Command | Purpose |
| ------- | ------- |
| `rank` | Score a listings file and show the best deals |
| `explain` | Full breakdown for one listing by id |
| `score` | Score a single deal from command-line flags |
| `transmit` | Format the top deal as a shareable recommendation |

## Key files

| Path | Role |
| ---- | ---- |
| `src/arizona_deal_agent/scoring.py` | Composite scoring and ranking |
| `src/arizona_deal_agent/finance.py` | Mortgage, NOI, cap rate, DSCR |
| `src/arizona_deal_agent/sources.py` | CSV/JSON listing loader |
| `src/arizona_deal_agent/report.py` | Table, JSON, CSV, explain, transmit output |
| `src/arizona_deal_agent/cli.py` | Command-line entry point |
| `data/sample_listings.csv` | Sample Arizona listings |
| `tests/` | Finance, scoring, sources, and CLI tests |

## Cloud Agent environment

`install` creates `.venv` and installs the package with dev dependencies.
