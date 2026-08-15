"""Topic pages for houses, goods, designer, cards, coins, and jewelry.

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
    uses_ebay: bool
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
        uses_ebay=False,
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
        uses_ebay=True,
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
        uses_ebay=True,
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
        uses_ebay=True,
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
        uses_ebay=True,
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
        uses_ebay=True,
        path="/tools",
    ),
    "gold": Topic(
        id="gold",
        title="Gold",
        blurb="Gold jewelry and bullion from allowlisted Phoenix Craigslist jewelry.",
        default_query="gold",
        default_budget=5_000.0,
        craigslist_path="jwa",
        min_live_price=50.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/gold",
    ),
    "silver": Topic(
        id="silver",
        title="Silver",
        blurb="Silver jewelry, coins, and flatware from allowlisted Phoenix Craigslist jewelry.",
        default_query="silver",
        default_budget=2_000.0,
        craigslist_path="jwa",
        min_live_price=50.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/silver",
    ),
    "diamonds": Topic(
        id="diamonds",
        title="Diamonds",
        blurb="Diamond rings and loose stones from allowlisted Phoenix Craigslist jewelry.",
        default_query="diamond",
        default_budget=10_000.0,
        craigslist_path="jwa",
        min_live_price=100.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/diamonds",
    ),
    "designer": Topic(
        id="designer",
        title="Designer",
        blurb="Designer clothing and bags from allowlisted Craigslist and official eBay.",
        default_query="designer",
        default_budget=3_000.0,
        craigslist_path="cla",
        min_live_price=40.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/designer",
    ),
    "luxury": Topic(
        id="luxury",
        title="Luxury & rare",
        blurb="High-end and rare items from allowlisted Craigslist and official eBay.",
        default_query="luxury rare",
        default_budget=10_000.0,
        craigslist_path="sss",
        min_live_price=100.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/luxury",
    ),
    "coins": Topic(
        id="coins",
        title="Coins",
        blurb="Collectible coins from allowlisted Craigslist and official eBay.",
        default_query="collectible coins",
        default_budget=2_000.0,
        craigslist_path="cba",
        min_live_price=20.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/coins",
    ),
    "pokemon": Topic(
        id="pokemon",
        title="Pokémon cards",
        blurb="Pokémon cards from allowlisted Craigslist and official eBay.",
        default_query="pokemon cards",
        default_budget=500.0,
        craigslist_path="taa",
        min_live_price=20.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/pokemon",
    ),
    "sports-cards": Topic(
        id="sports-cards",
        title="Sports cards",
        blurb="Sports cards from allowlisted Craigslist and official eBay.",
        default_query="sports cards",
        default_budget=500.0,
        craigslist_path="cba",
        min_live_price=20.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/sports-cards",
    ),
    "jerseys": Topic(
        id="jerseys",
        title="Jerseys",
        blurb="Team jerseys from allowlisted Craigslist and official eBay.",
        default_query="jersey",
        default_budget=400.0,
        craigslist_path="cla",
        min_live_price=20.0,
        uses_catalog=False,
        uses_ebay=True,
        path="/jerseys",
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
    "silvers": "silver",
    "sterling": "silver",
    "diamond": "diamonds",
    "jewelry": "gold",
    "jewellery": "gold",
    "high-class": "luxury",
    "highclass": "luxury",
    "expensive": "luxury",
    "rare": "luxury",
    "collectible": "coins",
    "collectibles": "coins",
    "coin": "coins",
    "pokemon-cards": "pokemon",
    "pokemon-card": "pokemon",
    "sport-cards": "sports-cards",
    "sportscards": "sports-cards",
    "trading-cards": "sports-cards",
    "jersey": "jerseys",
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
            blurb="Allowlisted live classifieds. The open page re-pulls this feed on a timer.",
            url="https://phoenix.craigslist.org/",
        ),
        SourceInfo(
            id="ebay",
            name="eBay",
            kind="live",
            topics=[topic.id for topic in TOPICS.values() if topic.uses_ebay],
            blurb="Official Browse API when EBAY_OAUTH_TOKEN is set; otherwise an official search link. We do not scrape eBay HTML.",
            url="https://www.ebay.com/",
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
    sources.extend(
        [
            SourceInfo(
                id="kitco",
                name="Kitco",
                kind="lookup-only",
                topics=["gold", "silver"],
                blurb="Spot prices — open in your browser to check melt value. We do not scrape it.",
                url="https://www.kitco.com/",
            ),
            SourceInfo(
                id="gia",
                name="GIA",
                kind="lookup-only",
                topics=["diamonds"],
                blurb="Diamond grading reports — open in your browser to verify a cert. We do not scrape it.",
                url="https://www.gia.edu/report-check-landing",
            ),
            SourceInfo(
                id="stockx",
                name="StockX",
                kind="lookup-only",
                topics=["designer", "jerseys", "luxury"],
                blurb="Official marketplace — open to check comps. We do not scrape it.",
                url="https://stockx.com/",
            ),
            SourceInfo(
                id="tcgplayer",
                name="TCGplayer",
                kind="lookup-only",
                topics=["pokemon"],
                blurb="Official card marketplace — open to check comps. We do not scrape it.",
                url="https://www.tcgplayer.com/",
            ),
            SourceInfo(
                id="pcgs",
                name="PCGS",
                kind="lookup-only",
                topics=["coins"],
                blurb="Coin certification lookup. We do not scrape it.",
                url="https://www.pcgs.com/",
            ),
        ]
    )
    return sources
