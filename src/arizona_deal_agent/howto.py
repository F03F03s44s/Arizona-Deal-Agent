"""How to use copy and named ranking scenarios for the CLI."""

from __future__ import annotations

from typing import Sequence

from .brand import PRODUCT, PROGRAM

DEFAULT_LISTINGS = "data/sample_listings.csv"

SCENARIOS: dict[str, dict[str, object]] = {
    "balanced": {
        "title": "Balanced",
        "why": "Default mix: price 0.25, profit 0.40, affordability 0.35.",
        "extra": ["--top", "100"],
        "expect": "AZ-003  3110 E Fort Lowell Rd, Tucson  (score 84.8)",
    },
    "profit": {
        "title": "Max profit",
        "why": "Rank purely on returns (cap rate, cash-on-cash, DSCR, cash flow).",
        "extra": ["--top", "100", "--weight-profit", "1", "--weight-price", "0", "--weight-afford", "0"],
        "expect": "AZ-012  5402 S 12th Ave, Tucson  (score 65.6)",
    },
    "affordability": {
        "title": "Max affordability",
        "why": "Rank on rent coverage / budget headroom only.",
        "extra": ["--top", "100", "--weight-afford", "1", "--weight-price", "0", "--weight-profit", "0"],
        "expect": "AZ-003  3110 E Fort Lowell Rd, Tucson  (score 100.0)",
    },
    "tight": {
        "title": "Tight budget",
        "why": "Hard filters: list price ≤ $350k, cash to close ≤ $90k, cash flow ≥ $0.",
        "extra": ["--max-price", "350000", "--budget-cash", "90000", "--min-cash-flow", "0"],
        "expect": "AZ-003  3110 E Fort Lowell Rd, Tucson  (only row that still qualifies)",
    },
    "houses": {
        "title": "Houses",
        "why": "Rank Arizona house listings (top 100).",
        "extra": ["--top", "100"],
        "expect": "AZ-003  3110 E Fort Lowell Rd, Tucson  (score 84.8)",
    },
}


def scenario_names() -> tuple[str, ...]:
    return tuple(SCENARIOS)


def scenario_argv(name: str, listings: str) -> list[str]:
    """Return the `rank` argv for a named How to use scenario."""
    spec = SCENARIOS.get(name)
    if spec is None:
        known = ", ".join(scenario_names())
        raise KeyError(f"unknown scenario '{name}'. Choose one of: {known}")
    extra = list(spec["extra"])  # type: ignore[arg-type]
    return ["rank", "-i", listings, *extra]


def format_command(argv: Sequence[str]) -> str:
    parts = [f"'{part}'" if any(ch.isspace() for ch in part) else part for part in argv]
    return PROGRAM + " " + " ".join(parts)


def render_howto(listings: str = DEFAULT_LISTINGS) -> str:
    """Operator guide printed by `deals howto`."""
    lines = [
        f"How to use {PRODUCT}",
        "",
        "One product: live deal ranking, Arizona property profit ranking,",
        "How to use, and transmit. Open the page or use the deals command.",
        "",
        "0. Open the page (leave the server window open)",
        "   cd into the folder that contains pyproject.toml (not C:\\Users\\kietl)",
        "   Windows: double-click start-deals.bat",
        "   or:  pip install -e \".[web]\"",
        "        python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
        "   Chrome/Opera address bar: http://127.0.0.1:8000",
        "",
        "1. Install the command (run these inside the cloned folder)",
        "   python -m venv .venv",
        "   Windows CMD:  .venv\\Scripts\\activate.bat",
        "   Windows PS:   .venv\\Scripts\\Activate.ps1",
        "   macOS/Linux:  source .venv/bin/activate",
        "   pip install -e .",
        "",
        "2. Find the best-value Arizona houses (sample catalog, no file needed)",
        f"   {PROGRAM} find --top 100",
        f"   or {format_command(['rank', '-i', listings, '--top', '100'])}",
        "",
        "3. Keep only what you can buy",
        f"   {format_command(['rank', '-i', listings, '--max-price', '350000', '--budget-cash', '90000', '--min-cash-flow', '0'])}",
        "",
        "4. Open the winner",
        f"   {format_command(['explain', '-i', listings, '--id', 'AZ-003'])}",
        "",
        "5. Score a deal that is not in a file yet",
        f"   {PROGRAM} score --price 240000 --rent 2100 --rehab 15000 --arv 330000",
        "",
        "6. Transmit the top pick",
        f"   {format_command(['transmit', '-i', listings, '--to', 'Investment team'])}",
        "",
        "Named scenarios (print this card, or run one with --run):",
        f"  {PROGRAM} howto --run balanced",
        f"  {PROGRAM} howto --run profit",
        f"  {PROGRAM} howto --run affordability",
        f"  {PROGRAM} howto --run tight",
        f"  {PROGRAM} howto --run houses",
        "",
    ]
    for name, spec in SCENARIOS.items():
        title = spec["title"]
        why = spec["why"]
        expect = spec["expect"]
        command = format_command(scenario_argv(name, listings))
        lines.append(f"{title} ({name})")
        lines.append(f"  {why}")
        lines.append(f"  $ {command}")
        lines.append(f"  Sample winner: {expect}")
        lines.append("")
    lines.append(f"Full guide: HOW_TO_USE.md   Flags and scoring: {PROGRAM} --help")
    return "\n".join(lines)


def unknown_scenario_message(name: str) -> str:
    known = ", ".join(scenario_names())
    return f"unknown scenario '{name}'. Choose one of: {known}"


def is_known_scenario(name: str) -> bool:
    return name in SCENARIOS
