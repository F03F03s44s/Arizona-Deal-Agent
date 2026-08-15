"""Topic pages: houses, household, electronics, furniture, cars, tools.

Each topic has its own default search, budget, and which allowlisted sources
feed it. Property always includes the curated Arizona house catalog.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import SourceInfo, TopicInfo
from .trust import LOOKUP_ONLY_HOSTS


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    blurb: str
    default_query: str
    default_budget: float
    craigslist_path: str
    min_live_price: float
    uses_catalog: bool
    path: str


TOPICS: dict[str, Topic] = {
    "property": Topic(
        id="property",
        title="Houses",
        blurb="Arizona house deals from the verified catalog, plus allowlisted Craigslist housing.",
        default_query="arizona house",
        default_budget=350_000.0,
        craigslist_path="rea",
        min_live_price=20_000.0,
        uses_catalog=True,
        path="/houses",
    ),
    "household": Topic(
        id="household",
        title="Household",
        blurb="Kitchen, laundry, and home goods from allowlisted Phoenix Craigslist.",
        default_query="household",
        default_budget=2_000.0,
        craigslist_path="hsh",
        min_live_price=20.0,
        uses_catalog=False,
        path="/household",
    ),
    "electronics": Topic(
        id="electronics",
        title="Electronics",
        blurb="Phones, laptops, TVs, and audio from allowlisted Phoenix Craigslist.",
        default_query="electronics",
        default_budget=2_000.0,
        craigslist_path="ele",
        min_live_price=20.0,
        uses_catalog=False,
        path="/electronics",
    ),
    "furniture": Topic(
        id="furniture",
        title="Furniture",
        blurb="Sofas, tables, and bedroom sets from allowlisted Phoenix Craigslist.",
        default_query="furniture",
        default_budget=5_000.0,
        craigslist_path="fuo",
        min_live_price=20.0,
        uses_catalog=False,
        path="/furniture",
    ),
    "autos": Topic(
        id="autos",
        title="Cars",
        blurb="Cars and trucks from allowlisted Phoenix Craigslist.",
        default_query="car",
        default_budget=15_000.0,
        craigslist_path="cta",
        min_live_price=500.0,
        uses_catalog=False,
        path="/cars",
    ),
    "tools": Topic(
        id="tools",
        title="Tools",
        blurb="Power tools and shop gear from allowlisted Phoenix Craigslist.",
        default_query="power tools",
        default_budget=15_000.0,
        craigslist_path="tls",
        min_live_price=20.0,
        uses_catalog=False,
        path="/tools",
    ),
}

TOPIC_ALIASES = {
    "houses": "property",
    "house": "property",
    "homes": "property",
    "real-estate": "property",
    "household-items": "household",
    "household-item": "household",
    "electronic": "electronics",
    "cars": "autos",
    "car": "autos",
    "auto": "autos",
    "vehicles": "autos",
}


def get_topic(name: str | None) -> Topic | None:
    """Return a topic when the caller asked for one; None keeps legacy behavior."""
    if not name:
        return None
    key = TOPIC_ALIASES.get(name.strip().lower(), name.strip().lower())
    return TOPICS.get(key)


def require_topic(name: str) -> Topic:
    topic = get_topic(name)
    if topic is None:
        known = ", ".join(TOPICS)
        raise KeyError(f"unknown topic {name!r}. Choose one of: {known}")
    return topic


def topic_infos() -> list[TopicInfo]:
    return [
        TopicInfo(
            id=topic.id,
            title=topic.title,
            blurb=topic.blurb,
            path=topic.path,
            default_query=topic.default_query,
            default_budget=topic.default_budget,
        )
        for topic in TOPICS.values()
    ]


def page_slugs() -> frozenset[str]:
    """URL path segments that serve a topic page."""
    slugs = {topic.path.strip("/") for topic in TOPICS.values()}
    slugs.update(TOPICS)
    slugs.update(TOPIC_ALIASES)
    return frozenset(slugs)


def source_infos() -> list[SourceInfo]:
    """What the agent will fetch vs what it only links out to."""
    live_topics = [topic.id for topic in TOPICS.values()]
    sources = [
        SourceInfo(
            id="verified-catalog",
            name="Arizona verified catalog",
            kind="catalog",
            topics=["property"],
            blurb="Curated Arizona house listings that ship with this project. Same file the CLI ranks.",
        ),
        SourceInfo(
            id="craigslist",
            name="Craigslist Phoenix",
            kind="live",
            topics=live_topics,
            blurb="Allowlisted live classifieds. Gift-card / wire / crypto scam titles are dropped.",
            url="https://phoenix.craigslist.org/",
        ),
    ]
    for link in LOOKUP_ONLY_HOSTS:
        sources.append(
            SourceInfo(
                id=link.name.lower().replace(" ", "-").replace(".", ""),
                name=link.name,
                kind="lookup-only",
                topics=["property"],
                blurb="Official site — open in your browser to verify an address. We do not scrape it.",
                url=link.url,
            )
        )
    return sources
