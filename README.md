# Arizona Deal Agent MVP 🌵

An AI-powered intelligence platform that continuously identifies Arizona opportunities across Real Estate, Vehicles, Luxury Resorts, Dining, and Surplus Tech, ranking them by a proprietary **Best Value Score**.

---

## 🌟 Key Features

1. **Multi-Category Value Ranking**:
   - **Real Estate**: Foreclosures, off-market wholesaler fixers, luxury equestrian distress sales across Phoenix, Scottsdale, Gilbert, and Tucson.
   - **Vehicles & 4x4**: Low-mileage EVs, desert-ready off-road rigs, sports cars, and UTVs evaluated below AZ book value.
   - **Travel & Resorts**: Luxury red rock villas in Sedona, five-diamond golf getaways in Scottsdale, and Grand Canyon excursions at up to 65% off.
   - **Dining & Experiences**: Michelin-caliber tasting menus in Old Town Scottsdale and Sonoran desert sunrise hot air balloon flights.
   - **Electronics & Surplus Tech**: Open-box Silicon desert hardware, solar storage banks (APS/SRP compatible), and professional camera packages.

2. **Proprietary Best Value Score (0–100)**:
   - **Discount Depth (30–50%)**: Percentage and absolute dollar spread vs regular market rate.
   - **ROI & Resale Upside (15–30%)**: Secondary market margin, resale potential, and yield.
   - **Historical Comps (15–25%)**: Valuation vs recent Arizona regional comps.
   - **Quality & Condition (10–20%)**: Hardware/property condition, verified provenance.
   - **Urgency & Liquidity (5–10%)**: Time-sensitivity and liquidation speed.

3. **Regional Arizona Value Radar**:
   - Interactive regional analysis across Phoenix Metro, Scottsdale & East Valley, Tucson & Southern AZ, Flagstaff & Northern AZ, and Sedona & Verde Valley.

4. **Deal ROI & Resale Simulator**:
   - Live calculator modeling purchase price, target resale, holding/rehab costs, and net ROI yield.

5. **AI Listing Ingestion & Evaluator**:
   - Instant scoring API for evaluating custom user-submitted listings or web crawler feeds.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Run the Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to explore the Arizona Deal Agent.

### 3. Run Automated Tests
```bash
npm test
```

### 4. Build for Production
```bash
npm run build
npm start
```

---

## 🔌 API Endpoints

- `GET /api/deals` - Retrieve ranked Arizona deals with filters (`category`, `region`, `minPrice`, `maxPrice`, `sortBy`, `valueTier`, `search`).
- `POST /api/deals` - Analyze and ingest a new Arizona deal listing into the database.
- `POST /api/score` - Run on-the-fly AI scoring on arbitrary price & comp inputs.
- `GET /api/crawl` - Trigger agent crawler against Arizona marketplace categories.
