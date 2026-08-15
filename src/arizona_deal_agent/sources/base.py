"""Shared plumbing for discovery sources."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

from ..models import Listing

USER_AGENT = "arizona-deal-agent/0.1 (+https://github.com/F03F03s44s/Arizona-Deal-Agent)"


class SourceError(RuntimeError):
    """A source could not produce listings."""


class Source(ABC):
    """A place the agent looks for candidate Arizona deals."""

    name: str = "source"
    description: str = ""
    is_live: bool = False

    @abstractmethod
    def fetch(self, limit: int | None = None) -> list[Listing]:
        """Return candidate listings, newest or most relevant first."""


def http_get_json(url: str, params: dict[str, str] | None = None, timeout: float = 30.0) -> dict:
    """GET a JSON document, raising :class:`SourceError` on any failure."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{url} returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SourceError(f"could not reach {url}: {exc}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SourceError(f"{url} did not return JSON") from exc


def parse_money(value: object) -> float | None:
    """Read ``$385,000``, ``385000``, or ``385000.00`` as a number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(",", "").replace("_", "")
    if not text or text.lower() in {"na", "n/a", "none", "null", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    number = parse_money(value)
    return int(number) if number is not None else None


def clean_text(value: object) -> str:
    return " ".join(str(value or "").split())
