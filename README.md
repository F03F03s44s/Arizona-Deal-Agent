# Arizona Deal Scout

A polished, dependency-free MVP for exploring representative Arizona real-estate opportunities and ranking them by best value.

The interface lets an investor:

- Search and filter sample listings by Arizona market, property type, price, bedrooms, and neighborhood.
- Re-rank opportunities using balanced value, cash-flow, or appreciation-upside lenses.
- Compare each deal’s estimated value gap, net yield, monthly operating cash flow, and modeled value score.
- Save contenders to a local shortlist and open a concise deal analysis.

## Run locally

```bash
npm start
```

Then open [http://localhost:4173](http://localhost:4173).

## Verify the ranking model

```bash
npm test
```

## Data note

This MVP uses clearly marked representative demo data. Its value model is a transparent first-pass heuristic, not investment advice or a live listing feed. Validate listing data, rent, operating costs, and local regulations before making an offer.
