"""Discovery sources: the places the agent looks for Arizona deals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import Listing
from .base import Source, SourceError, parse_money
from .hud_reo import HudReoSource
from .listing_file import FileSource, load_listings

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "az_sample_listings.csv"

__all__ = [
    "FileSource",
    "HudReoSource",
    "Source",
    "SourceError",
    "SourceResult",
    "available_sources",
    "collect",
    "load_listings",
    "parse_money",
    "resolve",
]


class SampleSource(FileSource):
    """A small fixed catalogue of Arizona listings, bundled for offline use."""

    name = "sample"
    description = "Bundled Arizona sample listings (offline demo data)"

    def __init__(self) -> None:
        super().__init__(SAMPLE_PATH, name="sample")
        self.description = type(self).description


BUILTIN = {
    "hud-reo": lambda: HudReoSource(listed_only=True),
    "hud-reo-all": lambda: HudReoSource(listed_only=False),
    "sample": SampleSource,
}


def available_sources() -> dict[str, str]:
    """Names of the built-in sources mapped to a one-line description."""
    return {
        "hud-reo": "HUD FHA foreclosures listed for sale in Arizona (live)",
        "hud-reo-all": "HUD FHA foreclosures listed or heading to market (live)",
        "sample": "Bundled Arizona sample listings (offline)",
    }


def resolve(spec: str) -> Source:
    """Turn a source spec into a :class:`Source`.

    Accepts a built-in name (``hud-reo``), an explicit file (``file:deals.csv``)
    or a bare path to a ``.csv``/``.json`` file.
    """
    spec = (spec or "").strip()
    if not spec:
        raise SourceError("empty source")

    if spec in BUILTIN:
        return BUILTIN[spec]()

    path = spec[5:] if spec.startswith("file:") else spec
    if Path(path).suffix.lower() in {".csv", ".tsv", ".txt", ".json"}:
        return FileSource(path)

    known = ", ".join(sorted(BUILTIN))
    raise SourceError(f"unknown source '{spec}' (expected one of {known}, or a .csv/.json path)")


@dataclass
class SourceResult:
    """What one source produced, including the reason it produced nothing."""

    name: str
    listings: list[Listing]
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


def collect(specs: list[str], limit: int | None = None) -> list[SourceResult]:
    """Fetch from every source, keeping going when one of them fails.

    A live feed can be down or blocked by the network the agent runs on. That
    should degrade the result set, not abort the search, so failures are
    captured per source and reported alongside the listings.
    """
    results: list[SourceResult] = []
    for spec in specs:
        try:
            source = resolve(spec)
            results.append(SourceResult(name=source.name, listings=source.fetch(limit=limit)))
        except SourceError as exc:
            results.append(SourceResult(name=spec, listings=[], error=str(exc)))
    return results
