# Arizona Deal Agent

MVP that finds Arizona deals and ranks them by **best value** — the lowest price that still leaves the most profit.

## What it does

1. Pulls live Slickdeals RSS (climate / shade / Arizona mentions + frontpage).
2. Mixes those with a curated Arizona local sample (Valley marketplace, vehicles, and housing).
3. Drops listings that are not useful in Arizona (no local hook and no desert-climate use).
4. Scores every remaining deal and ranks the board.

The ranking is deterministic and explained on each card. There is no LLM in the loop.

## Value score

| Weight | Signal | Why it matters |
| --- | --- | --- |
| 36% | Price vs Arizona market comps | How far below typical street / retail price |
| 24% | Profit or cap rate | Flip room after a resale haircut, or housing cash-on-cash |
| 20% | Affordability | Cheaper asks are easier to act on; housing is scaled to Valley prices |
| 10% | Recency | Fresh listings are less picked over |
| 10% | Arizona fit | City mention or heat / shade / water usefulness |

**Buy** = score 70+ and either ≥22% under comp or positive estimated profit.  
**Watch** = score 50–69. **Skip** = everything else.

## Run it

```bash
npm install
npm test
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

```bash
npm run rank            # top 15 in the terminal
npm run rank -- --offline
```

`GET /api/deals` accepts `city`, `category`, `maxPrice`, `minScore`, `recommendation`, and `q`.

## Notes

- Craigslist and other classifieds are not scraped. Their terms disallow bots; the local sample stands in for that inventory.
- Live feeds can fail or rate-limit. The local sample still ranks so the product is usable offline.
- Comps are typical Arizona street prices, not a live appraisal.
