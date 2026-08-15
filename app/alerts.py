"""Saved-search persistence and high-score alert checks."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .agent import rank_deals
from .data import load_deals
from .emailer import send_deal_alert
from .models import AlertCheckResponse, SavedSearch, SavedSearchCreate, ScoredDeal

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "saved_searches.json"
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_store() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        STORE_PATH.write_text("[]\n", encoding="utf-8")


def list_saved_searches() -> list[SavedSearch]:
    _ensure_store()
    with _lock:
        raw = json.loads(STORE_PATH.read_text(encoding="utf-8") or "[]")
    return [SavedSearch.model_validate(item) for item in raw]


def _write_all(searches: list[SavedSearch]) -> None:
    _ensure_store()
    payload = [s.model_dump(mode="json") for s in searches]
    with _lock:
        STORE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_saved_search(payload: SavedSearchCreate) -> SavedSearch:
    search = SavedSearch(
        id=str(uuid.uuid4()),
        created_at=_now(),
        **payload.model_dump(),
    )
    searches = list_saved_searches()
    searches.append(search)
    _write_all(searches)
    return search


def delete_saved_search(search_id: str) -> bool:
    searches = list_saved_searches()
    kept = [s for s in searches if s.id != search_id]
    if len(kept) == len(searches):
        return False
    _write_all(kept)
    return True


def _format_alert(search: SavedSearch, hits: list[ScoredDeal]) -> tuple[str, str]:
    subject = f"Arizona Deal Agent: {len(hits)} deal(s) scored ≥ {search.min_score:.2f}"
    lines = [
        "Your saved search found high-scoring Phoenix Craigslist deals.",
        "",
        f"Budget: ${search.budget:,.0f}",
        f"Profit weight: {search.profit_weight:.2f}",
        f"Query: {search.query or '(all for-sale)'}",
        f"Min score: {search.min_score:.2f}",
        "",
    ]
    for scored in hits[:10]:
        deal = scored.deal
        lines.append(
            f"- {deal.title} | score {scored.score:.3f} | "
            f"cost ${deal.acquisition_cost:,.0f} | profit ${scored.profit:,.0f}"
        )
        if deal.url:
            lines.append(f"  {deal.url}")
    lines.append("")
    lines.append("— Arizona Deal Agent")
    return subject, "\n".join(lines)


def check_saved_searches(*, refresh: bool = False) -> AlertCheckResponse:
    """Rank live deals for each saved search and email score ≥ threshold hits."""
    searches = list_saved_searches()
    alerts_sent = 0
    details: list[str] = []
    updated: list[SavedSearch] = []

    for search in searches:
        deals, source = load_deals(query=search.query, refresh=refresh)
        ranked = rank_deals(deals, search.budget, search.profit_weight)
        hits = [
            s
            for s in ranked.ranked
            if s.within_budget and s.score >= search.min_score
        ]
        search.last_checked_at = _now()
        if hits:
            subject, body = _format_alert(search, hits)
            delivery = send_deal_alert(search.email, subject, body)
            search.last_alerted_at = _now()
            search.alert_count += 1
            alerts_sent += 1
            details.append(
                f"{search.id}: {len(hits)} hit(s) via {delivery} from {source}"
            )
        else:
            details.append(f"{search.id}: no hits from {source}")
        updated.append(search)

    _write_all(updated)
    return AlertCheckResponse(
        checked=len(searches),
        alerts_sent=alerts_sent,
        details=details,
    )
