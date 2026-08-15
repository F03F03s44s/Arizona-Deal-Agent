# How to use Arizona Deal Agent

## Open the page in Chrome or Opera

That page is **not on Google**. It is a local page on your PC: `http://127.0.0.1:8000`.

1. In PowerShell, from the repo folder, start the server (leave the window open):

```powershell
# from the unzipped or cloned Arizona-Deal-Agent folder
.\.venv\Scripts\Activate.ps1
pip install -e ".[web]"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Open **Chrome** or **Opera**.
3. Click the **address bar** at the very top (the box that shows `opera://startpage` or a website URL). Do **not** type in the Google search box on google.com.
4. Type exactly: `http://127.0.0.1:8000`
5. Press Enter.

You should see “Arizona Deal Agent” and topic tabs including **big sales**, **bundles**, **pallets**, **bulk**, and **free & high return**. The list **live-updates** about every 45 seconds. Free posts are ranked by a conservative resale estimate (working TVs and tools rise; broken / parts-only posts are dropped). Gift-card / wire / crypto / replica titles are dropped. eBay is used through its official API when `EBAY_OAUTH_TOKEN` is set; otherwise you get an official eBay search link (pages are not scraped).

Every listing URL must be **HTTPS** on **craigslist.org** or **ebay.com**. Unknown hosts, URL shorteners, and chat/pay links are dropped. That is **site verification**, not a promise that every seller is honest — still meet in a public place and never wire money to a stranger.

Or run `powershell -ExecutionPolicy Bypass -File scripts\open-ui.ps1` from the repo folder; it starts the server and opens the browser.

The agent is also a **CLI**. Point it at a listings file. It scores every property on
price, profitability, and affordability, ranks them, and can **transmit** the
top pick as a shareable recommendation.

In-product guide (prints this path and the named scenarios):

```bash
arizona-deal-agent howto
```

## 60 seconds

Clone the repo first, then install **inside that folder** (not your home directory).

**Windows Command Prompt (no Git needed)**

Open a **new** Command Prompt. Paste only these lines — not old `C:\>` prompts or `ERROR:` text.

```bat
cd C:\Users\%USERNAME%
curl -L -o Arizona-Deal-Agent.zip https://github.com/F03F03s44s/Arizona-Deal-Agent/archive/refs/heads/main.zip
tar -xf Arizona-Deal-Agent.zip
cd Arizona-Deal-Agent-main
dir pyproject.toml
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
arizona-deal-agent howto
arizona-deal-agent find --top 100
```

`dir pyproject.toml` must show that file. If it says file not found, you are in the wrong folder.

**Windows Command Prompt (if Git is installed)**

```bat
git clone https://github.com/F03F03s44s/Arizona-Deal-Agent.git
cd Arizona-Deal-Agent
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
```

**Windows PowerShell (no Git needed)**

In PowerShell, `curl` is not the real curl. Use `curl.exe` or `Invoke-WebRequest`.

```powershell
cd C:\Users\$env:USERNAME
curl.exe -L -o Arizona-Deal-Agent.zip https://github.com/F03F03s44s/Arizona-Deal-Agent/archive/refs/heads/main.zip
tar -xf Arizona-Deal-Agent.zip
cd Arizona-Deal-Agent-main
dir pyproject.toml
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -e .
arizona-deal-agent howto
arizona-deal-agent find --top 100
```

**macOS / Linux**

```bash
git clone https://github.com/F03F03s44s/Arizona-Deal-Agent.git
cd Arizona-Deal-Agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

| Step | Command |
| ---- | ------- |
| Find best-value deals (sample catalog, no `-i`) | `arizona-deal-agent find --top 100` |
| Rank a listings file | `arizona-deal-agent rank -i data/sample_listings.csv --top 100` |
| Keep only what you can buy | `arizona-deal-agent rank -i data/sample_listings.csv --max-price 350000 --budget-cash 90000 --min-cash-flow 0` |
| Open the winner | `arizona-deal-agent explain -i data/sample_listings.csv --id AZ-003` |
| Score a deal not in a file | `arizona-deal-agent score --price 240000 --rent 2100 --rehab 15000 --arv 330000` |
| Transmit the top pick | `arizona-deal-agent transmit -i data/sample_listings.csv --to "Investment team"` |

Without installing, from the repo folder:

- Windows CMD: `set PYTHONPATH=src` then `python -m arizona_deal_agent find --top 100`
- macOS / Linux: `PYTHONPATH=src python3 -m arizona_deal_agent find --top 100`

## Named scenarios

Each named scenario is a `rank` recipe you can print or run:

```bash
arizona-deal-agent howto --run balanced
arizona-deal-agent howto --run profit
arizona-deal-agent howto --run affordability
arizona-deal-agent howto --run tight
arizona-deal-agent howto --run houses
```

Against `data/sample_listings.csv`:

| Scenario | What it does | Sample winner |
| -------- | ------------ | ------------- |
| `balanced` | Default weights (price 0.25 / profit 0.40 / afford 0.35), top 100 | AZ-003 3110 E Fort Lowell Rd, Tucson (84.8) |
| `houses` | Same catalog — Arizona houses, top 100 | AZ-003 3110 E Fort Lowell Rd, Tucson (84.8) |
| `profit` | `--weight-profit 1` (returns only) | AZ-012 5402 S 12th Ave, Tucson (65.6) |
| `affordability` | `--weight-afford 1` (rent coverage / headroom) | AZ-003 3110 E Fort Lowell Rd, Tucson (100.0) |
| `tight` | `--max-price 350000 --budget-cash 90000 --min-cash-flow 0` | AZ-003 only — everything else is filtered out |

Budget flags are hard filters. Add `--include-over-budget` on `rank` if you want
over-limit rows visible and marked instead of dropped.

## Commands

| Command | Purpose |
| ------- | ------- |
| `howto` | Print this path, or `--run` a named scenario |
| `find` | Rank the bundled sample catalog (or `-i` your file) by best value |
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
pip install -e ".[dev,web]"
pytest
```

Flags, scoring math, and every command (including `howto`) are covered there.
The long-form reference — assumptions table, Python API, and scope notes — is
in `README.md`.
