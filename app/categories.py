"""Craigslist category reference for the areas this agent watches.

Every search row carries a numeric category id, and Craigslist keeps separate
ids for the same category depending on whether a private seller, a dealer or a
broker posted it. That is what lets a listing be labelled as a dealer
(wholesale) listing without fetching its page.

Generated from https://reference.craigslist.org/Categories.
"""

from __future__ import annotations

from dataclasses import dataclass

OWNER = "owner"
DEALER = "dealer"

FOR_SALE = "S"
HOUSING = "H"


@dataclass(frozen=True)
class Category:
    """One Craigslist category."""

    abbreviation: str
    label: str
    seller_type: str | None
    kind: str

    @property
    def is_property(self) -> bool:
        return self.kind == HOUSING


CATEGORIES: dict[int, Category] = {
    1: Category("apa", "apartments / housing for rent", None, "H"),
    2: Category("hou", "wanted: apts", None, "H"),
    5: Category("for", "general for sale", OWNER, "S"),
    7: Category("sys", "computers", OWNER, "S"),
    18: Category("roo", "rooms & shares", None, "H"),
    19: Category("sha", "wanted: room/share", None, "H"),
    20: Category("wan", "wanted", OWNER, "S"),
    39: Category("sub", "sublets & temporary", None, "H"),
    40: Category("off", "office & commercial", None, "H"),
    41: Category("prk", "parking & storage", None, "H"),
    42: Category("bar", "barter", None, "S"),
    44: Category("tix", "tickets", OWNER, "S"),
    58: Category("sbw", "wanted: sublet/temp", None, "H"),
    65: Category("swp", "housing swap", None, "H"),
    68: Category("bik", "bicycles", OWNER, "S"),
    69: Category("mcy", "motorcycles/scooters", OWNER, "S"),
    73: Category("gms", "garage & moving sales", None, "S"),
    92: Category("bks", "books & magazines", OWNER, "S"),
    93: Category("spo", "sporting goods", OWNER, "S"),
    94: Category("clo", "clothing & accessories", OWNER, "S"),
    95: Category("clt", "collectibles", OWNER, "S"),
    96: Category("ele", "electronics", OWNER, "S"),
    97: Category("hsh", "household items", OWNER, "S"),
    98: Category("msg", "musical instruments", OWNER, "S"),
    99: Category("vac", "vacation rentals", None, "H"),
    101: Category("zip", "free stuff", None, "S"),
    107: Category("bab", "baby & kid stuff", OWNER, "S"),
    117: Category("emd", "cds / dvds / vhs", OWNER, "S"),
    118: Category("tls", "tools", OWNER, "S"),
    119: Category("boa", "boats", OWNER, "S"),
    120: Category("jwl", "jewelry", OWNER, "S"),
    121: Category("rew", "wanted: real estate", None, "H"),
    122: Category("pts", "auto parts", OWNER, "S"),
    124: Category("rvs", "rvs", OWNER, "S"),
    132: Category("tag", "toys & games", OWNER, "S"),
    133: Category("grd", "farm & garden", OWNER, "S"),
    134: Category("bfs", "business/commercial", OWNER, "S"),
    135: Category("art", "arts & crafts", OWNER, "S"),
    136: Category("mat", "materials", OWNER, "S"),
    137: Category("pho", "photo/video", OWNER, "S"),
    141: Category("fuo", "furniture", OWNER, "S"),
    142: Category("fud", "furniture", DEALER, "S"),
    143: Category("reo", "real estate", OWNER, "H"),
    144: Category("reb", "real estate", DEALER, "H"),
    145: Category("cto", "cars & trucks", OWNER, "S"),
    146: Category("ctd", "cars & trucks", DEALER, "S"),
    149: Category("app", "appliances", OWNER, "S"),
    150: Category("atq", "antiques", OWNER, "S"),
    151: Category("vgm", "video gaming", OWNER, "S"),
    152: Category("hab", "health and beauty", OWNER, "S"),
    153: Category("mob", "cell phones", OWNER, "S"),
    160: Category("mcd", "motorcycles/scooters", DEALER, "S"),
    161: Category("tid", "tickets", DEALER, "S"),
    162: Category("ppd", "appliances", DEALER, "S"),
    163: Category("ptd", "auto parts", DEALER, "S"),
    164: Category("bod", "boats", DEALER, "S"),
    165: Category("mod", "cell phones", DEALER, "S"),
    166: Category("syd", "computers", DEALER, "S"),
    167: Category("eld", "electronics", DEALER, "S"),
    168: Category("rvd", "rvs", DEALER, "S"),
    169: Category("atd", "antiques", DEALER, "S"),
    170: Category("ard", "arts & crafts", DEALER, "S"),
    171: Category("bad", "baby & kid stuff", DEALER, "S"),
    172: Category("bid", "bicycles", DEALER, "S"),
    173: Category("bkd", "books & magazines", DEALER, "S"),
    174: Category("bfd", "business/commercial", DEALER, "S"),
    175: Category("emq", "cds / dvds / vhs", DEALER, "S"),
    176: Category("cld", "clothing & accessories", DEALER, "S"),
    177: Category("cbd", "collectibles", DEALER, "S"),
    178: Category("grq", "farm & garden", DEALER, "S"),
    179: Category("fod", "general for sale", DEALER, "S"),
    180: Category("had", "health and beauty", DEALER, "S"),
    181: Category("hsd", "household items", DEALER, "S"),
    182: Category("jwd", "jewelry", DEALER, "S"),
    183: Category("mad", "materials", DEALER, "S"),
    184: Category("msd", "musical instruments", DEALER, "S"),
    185: Category("phd", "photo/video", DEALER, "S"),
    186: Category("sgd", "sporting goods", DEALER, "S"),
    187: Category("tld", "tools", DEALER, "S"),
    188: Category("tad", "toys & games", DEALER, "S"),
    189: Category("vgd", "video gaming", DEALER, "S"),
    190: Category("wad", "wanted", DEALER, "S"),
    191: Category("snw", "atvs, utvs, snowmobiles", OWNER, "S"),
    192: Category("snd", "atvs, utvs, snowmobiles", DEALER, "S"),
    193: Category("hvo", "heavy equipment", OWNER, "S"),
    194: Category("hvd", "heavy equipment", DEALER, "S"),
    195: Category("mpo", "motorcycle parts", OWNER, "S"),
    196: Category("mpd", "motorcycle parts", DEALER, "S"),
    197: Category("bop", "bicycle parts", OWNER, "S"),
    198: Category("bdp", "bicycle parts", DEALER, "S"),
    199: Category("sop", "computer parts", OWNER, "S"),
    200: Category("sdp", "computer parts", DEALER, "S"),
    201: Category("bpo", "boat parts", OWNER, "S"),
    202: Category("bpd", "boat parts", DEALER, "S"),
    203: Category("wto", "auto wheels & tires", OWNER, "S"),
    204: Category("wtd", "auto wheels & tires", DEALER, "S"),
    205: Category("tro", "trailers", OWNER, "S"),
    206: Category("trb", "trailers", DEALER, "S"),
    208: Category("avo", "aviation", OWNER, "S"),
    209: Category("avd", "aviation", DEALER, "S"),
}

# Search paths that cover owner, dealer and broker listings together.
# Craigslist uses a third abbreviation for the combined view, so these cannot
# be derived from the per-seller ids above.
SEARCH_PATHS: dict[str, str] = {
    "All for sale": "sss",
    "Real estate for sale": "rea",
    "Apartments / rentals": "apa",
    "Office & commercial": "off",
    "Tools": "tla",
    "Heavy equipment": "hva",
    "Materials": "maa",
    "Business / commercial goods": "bfa",
    "General for sale": "foa",
    "Electronics": "ela",
    "Household items": "hsa",
    "Appliances": "ppa",
    "Sporting goods": "sga",
    "Farm & garden": "gra",
}

# Search paths that return property rather than goods.
PROPERTY_SEARCH_PATHS = frozenset({"rea", "reo", "reb", "apa", "off"})

DEFAULT_SEARCH_PATH = "sss"


def describe(category_id: int | None) -> Category | None:
    """Look up a category by the id embedded in a search row."""
    if category_id is None:
        return None
    return CATEGORIES.get(category_id)
