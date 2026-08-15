"""Generate the bundled sample dataset of Arizona listings (deterministic).

Run from the repo root:  python scripts/generate_sample_data.py

Prices are drawn around each city's real median $/sqft with a wide spread so
the dataset contains genuine bargains, fairly-priced homes, and overpriced
ones — which is what the ranking engine needs to demonstrate value.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

CITIES = {
    # city: (median_ppsf, zips, weight)
    "Phoenix": (282.0, ["85008", "85032", "85041", "85021"], 10),
    "Scottsdale": (455.0, ["85251", "85254", "85260"], 5),
    "Tucson": (215.0, ["85710", "85719", "85745"], 8),
    "Mesa": (281.0, ["85201", "85204", "85213"], 6),
    "Chandler": (305.0, ["85224", "85286"], 4),
    "Gilbert": (298.0, ["85233", "85295"], 4),
    "Tempe": (312.0, ["85281", "85283"], 4),
    "Glendale": (258.0, ["85301", "85308"], 4),
    "Peoria": (272.0, ["85345", "85383"], 3),
    "Surprise": (243.0, ["85374", "85379"], 3),
    "Goodyear": (258.0, ["85338", "85395"], 3),
    "Queen Creek": (268.0, ["85142"], 2),
    "Buckeye": (228.0, ["85326"], 2),
    "Casa Grande": (198.0, ["85122"], 2),
    "Flagstaff": (392.0, ["86001", "86004"], 3),
    "Prescott": (332.0, ["86301", "86305"], 2),
    "Yuma": (196.0, ["85364"], 2),
    "Sierra Vista": (172.0, ["85635"], 1),
}

STREETS = [
    "Cactus Wren Rd", "Saguaro Blvd", "Camelback Rd", "Ocotillo Ln", "Mesquite Dr",
    "Palo Verde Ave", "Desert Bloom Way", "Sunset Vista Ct", "Dusty Trail Rd",
    "Cholla St", "Ironwood Dr", "Agave Pl", "Sonoran Way", "Painted Rock Rd",
    "Copper Canyon Dr", "Javelina Run", "Quail Hollow Ln", "Rincon Peak Dr",
]

PROPERTY_TYPES = ["single_family"] * 7 + ["townhouse", "condo", "manufactured"]


def make_listing(rng: random.Random, idx: int, city: str, median_ppsf: float, zips: list[str]) -> dict:
    property_type = rng.choice(PROPERTY_TYPES)
    if property_type == "condo":
        sqft = rng.randint(650, 1600)
    elif property_type == "townhouse":
        sqft = rng.randint(1000, 2100)
    else:
        sqft = rng.randint(1050, 3900)

    # Spread listings from clear bargains (~26% under) to overpriced (~28% over).
    ppsf = median_ppsf * rng.uniform(0.74, 1.28)
    price = round(ppsf * sqft / 500) * 500

    beds = max(1, min(6, round(sqft / rng.uniform(550, 750))))
    baths = max(1.0, min(5.0, round((beds - rng.uniform(0.0, 1.0)) * 2) / 2))
    year_built = rng.randint(1958, 2024)
    days_on_market = int(min(rng.expovariate(1 / 38.0), 170))

    original_price = None
    if days_on_market > 25 and rng.random() < 0.45:
        cut = rng.uniform(0.01, 0.09)
        original_price = round(price / (1 - cut) / 500) * 500

    hoa = None
    if property_type in ("condo", "townhouse"):
        hoa = rng.randrange(120, 420, 5)
    elif rng.random() < 0.25:
        hoa = rng.randrange(30, 130, 5)

    lot = None
    if property_type in ("single_family", "manufactured"):
        lot = rng.randrange(4500, 22000, 250)

    return {
        "id": f"AZ-{idx:04d}",
        "address": f"{rng.randint(1000, 19999)} {rng.choice(['N', 'S', 'E', 'W'])} {rng.choice(STREETS)}",
        "city": city,
        "state": "AZ",
        "zip_code": rng.choice(zips),
        "price": price,
        "original_price": original_price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "lot_sqft": lot,
        "year_built": year_built,
        "days_on_market": days_on_market,
        "property_type": property_type,
        "hoa_monthly": hoa,
        "url": None,
    }


def main() -> None:
    rng = random.Random(42)
    listings = []
    idx = 1
    for city, (median_ppsf, zips, weight) in CITIES.items():
        for _ in range(weight):
            listings.append(make_listing(rng, idx, city, median_ppsf, zips))
            idx += 1

    out = Path(__file__).resolve().parent.parent / "data" / "sample_listings.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(listings, indent=2) + "\n")
    print(f"Wrote {len(listings)} listings to {out}")


if __name__ == "__main__":
    main()
