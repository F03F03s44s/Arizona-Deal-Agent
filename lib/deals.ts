import { Deal, DealFilterOptions, DealStats, DealCategory, ArizonaRegion } from '@/types/deal';
import { calculateValueScore } from './scoring';

export const ARIZONA_DEALS: Deal[] = [
  // 1. Real Estate Deals
  {
    id: 'az-re-001',
    title: 'Modern 4-Bed Home in Gilbert (Bank Foreclosure Wholesale)',
    description: 'Renovated 4-bedroom, 3-bath 2,450 sqft single family home with private pool in Gilbert, AZ. Bank foreclosure asset liquidation, priced $135k below neighborhood comps for rapid closing.',
    category: 'real-estate',
    source: 'AZ MLS Trustee Sales',
    sourceUrl: 'https://arizonahomes.example.com/listing/gilbert-az-001',
    price: 465000,
    originalPrice: 600000,
    currency: 'USD',
    location: {
      city: 'Gilbert',
      region: 'Scottsdale & East Valley',
      zipCode: '85296',
      lat: 33.3528,
      lng: -111.7890,
      address: '2840 E Higley Rd, Gilbert, AZ 85296',
    },
    images: [
      'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Foreclosure', 'Pool', 'High Equity', 'Gilbert School District'],
    features: {
      sqft: 2450,
      beds: 4,
      baths: 3,
      yearBuilt: 2018,
      hoaFee: '$65/mo',
      capRateEstimate: '8.4%',
    },
    postedAt: '2026-08-14T09:30:00Z',
    expiresAt: '2026-08-20T23:59:59Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'real-estate',
      price: 465000,
      originalPrice: 600000,
      marketAveragePrice: 595000,
      conditionRating: 4.8,
      estimatedResaleValue: 590000,
      daysOnMarketOrExpiresInDays: 6,
      verified: true,
    }),
  },
  {
    id: 'az-re-002',
    title: 'Downtown Phoenix Historic 2-Bed Bungalow (Off-Market Fixer)',
    description: 'Rare Coronado historic district craftsman bungalow with detached guest house / casita. Great short-term rental rental potential or flip opportunity near Roosevelt Row arts district.',
    category: 'real-estate',
    source: 'Phoenix Off-Market Wholesalers',
    price: 340000,
    originalPrice: 450000,
    currency: 'USD',
    location: {
      city: 'Phoenix',
      region: 'Phoenix Metro',
      zipCode: '85006',
      lat: 33.4688,
      lng: -112.0526,
      address: '1422 E Coronado Rd, Phoenix, AZ 85006',
    },
    images: [
      'https://images.unsplash.com/photo-1570129477492-45c003edd2be?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Historic District', 'ADU / Casita', 'Short-Term Rental Ready', 'Cash Flow'],
    features: {
      sqft: 1650,
      beds: 2,
      baths: 2,
      guestHouse: true,
      yearBuilt: 1948,
    },
    postedAt: '2026-08-13T14:15:00Z',
    expiresAt: '2026-08-18T18:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'real-estate',
      price: 340000,
      originalPrice: 450000,
      marketAveragePrice: 440000,
      conditionRating: 4.2,
      estimatedResaleValue: 470000,
      daysOnMarketOrExpiresInDays: 5,
      verified: true,
    }),
  },
  {
    id: 'az-re-003',
    title: 'Tucson Foothills Panoramic Mountain View Villa',
    description: 'Sprawling 3-bed desert retreat nestled in Catalina Foothills with unobstructed mountain and city light views, solar array, and private patio courtyards.',
    category: 'real-estate',
    source: 'Southern AZ MLS Liquidation',
    price: 520000,
    originalPrice: 660000,
    currency: 'USD',
    location: {
      city: 'Tucson',
      region: 'Tucson & Southern AZ',
      zipCode: '85718',
      lat: 32.2989,
      lng: -110.9265,
      address: '5610 N Campbell Ave, Tucson, AZ 85718',
    },
    images: [
      'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Mountain Views', 'Solar Equipped', 'Catalina Foothills'],
    features: {
      sqft: 2800,
      beds: 3,
      baths: 3,
      lotSize: '0.85 Acres',
    },
    postedAt: '2026-08-11T10:00:00Z',
    expiresAt: '2026-08-25T00:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'real-estate',
      price: 520000,
      originalPrice: 660000,
      marketAveragePrice: 645000,
      conditionRating: 4.7,
      estimatedResaleValue: 650000,
      daysOnMarketOrExpiresInDays: 10,
      verified: true,
    }),
  },

  // 2. Vehicles Deals
  {
    id: 'az-veh-001',
    title: '2023 Tesla Model Y Long Range AWD (Low Mileage)',
    description: 'Clean title Arizona garage-kept Tesla Model Y with only 14,200 miles. Full Self-Driving hardware, pristine interior, dual motor all-wheel drive, ceramic tint for AZ heat.',
    category: 'vehicles',
    source: 'Scottsdale Private Collector Sale',
    price: 31500,
    originalPrice: 42000,
    currency: 'USD',
    location: {
      city: 'Scottsdale',
      region: 'Scottsdale & East Valley',
      zipCode: '85251',
      lat: 33.4942,
      lng: -111.9261,
    },
    images: [
      'https://images.unsplash.com/photo-1560958089-b8a1929cea89?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Electric', 'Clean Title', 'Low Mileage', 'AWD', 'AZ Tinted'],
    features: {
      mileage: '14,200 mi',
      transmission: 'Automatic',
      color: 'Pearl White Multi-Coat',
      batteryHealth: '98%',
      range: '330 mi',
    },
    postedAt: '2026-08-15T08:00:00Z',
    expiresAt: '2026-08-19T18:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'vehicles',
      price: 31500,
      originalPrice: 42000,
      marketAveragePrice: 38500,
      conditionRating: 4.9,
      estimatedResaleValue: 37500,
      daysOnMarketOrExpiresInDays: 4,
      verified: true,
    }),
  },
  {
    id: 'az-veh-002',
    title: '2022 Toyota 4Runner TRD Off-Road 4x4 (Sedona Ready)',
    description: 'One-owner Toyota 4Runner TRD Off-Road with Fox suspension upgrade, roof rack, and all-terrain tires. Zero rust desert vehicle serviced strictly at Camelback Toyota.',
    category: 'vehicles',
    source: 'Phoenix Auto Exchange',
    price: 35900,
    originalPrice: 45000,
    currency: 'USD',
    location: {
      city: 'Phoenix',
      region: 'Phoenix Metro',
      zipCode: '85016',
      lat: 33.5092,
      lng: -112.0435,
    },
    images: [
      'https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['4x4', 'TRD Off-Road', 'Toyota Reliability', 'Zero Rust'],
    features: {
      mileage: '28,500 mi',
      drivetrain: '4WD',
      engine: '4.0L V6',
      serviceHistory: 'Complete Dealership Records',
    },
    postedAt: '2026-08-14T16:20:00Z',
    expiresAt: '2026-08-22T00:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'vehicles',
      price: 35900,
      originalPrice: 45000,
      marketAveragePrice: 43000,
      conditionRating: 4.8,
      estimatedResaleValue: 41000,
      daysOnMarketOrExpiresInDays: 7,
      verified: true,
    }),
  },
  {
    id: 'az-veh-003',
    title: '2021 Can-Am Maverick X3 Turbo RR (AZ Off-Road Spec)',
    description: 'Street-legal Arizona registered UTV with 195hp Turbo RR engine, beadlock wheels, upgraded Rugged Radios, and light bar. Ready for Glamis or Tonto trails.',
    category: 'vehicles',
    source: 'Mesa Powersports Clearance',
    price: 18500,
    originalPrice: 28000,
    currency: 'USD',
    location: {
      city: 'Mesa',
      region: 'Scottsdale & East Valley',
      zipCode: '85204',
      lat: 33.4152,
      lng: -111.8315,
    },
    images: [
      'https://images.unsplash.com/photo-1558981403-c5f9899a28bc?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Street Legal', 'Turbo', 'Desert Racing', 'Powersport Deal'],
    features: {
      hours: '62 hrs',
      horsepower: '195 hp',
      registration: 'AZ Plate Active',
    },
    postedAt: '2026-08-12T11:00:00Z',
    expiresAt: '2026-08-17T12:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'vehicles',
      price: 18500,
      originalPrice: 28000,
      marketAveragePrice: 24500,
      conditionRating: 4.6,
      estimatedResaleValue: 23500,
      daysOnMarketOrExpiresInDays: 2,
      verified: true,
    }),
  },

  // 3. Travel & Resort Stays
  {
    id: 'az-trv-001',
    title: '3-Night Luxury Villa Package at Enchantment Resort Sedona',
    description: 'All-inclusive 3-night getaway at Sedona’s premier red rock canyon resort. Includes $300 Mii amo spa credit, complimentary daily breakfast for 2, and guided vortex hiking tour.',
    category: 'travel-resorts',
    source: 'Sedona Escapes Flash Sale',
    price: 899,
    originalPrice: 2450,
    currency: 'USD',
    location: {
      city: 'Sedona',
      region: 'Sedona & Verde Valley',
      zipCode: '86336',
      lat: 34.8697,
      lng: -111.7610,
    },
    images: [
      'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Luxury Stay', 'Spa Credit', 'Red Rock Views', '63% Off'],
    features: {
      nights: 3,
      guests: 2,
      spaCreditIncluded: '$300',
      validThru: 'Dec 2026 (No Blackout)',
    },
    postedAt: '2026-08-15T06:00:00Z',
    expiresAt: '2026-08-18T23:59:59Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'travel-resorts',
      price: 899,
      originalPrice: 2450,
      marketAveragePrice: 2200,
      conditionRating: 5.0,
      daysOnMarketOrExpiresInDays: 3,
      verified: true,
    }),
  },
  {
    id: 'az-trv-002',
    title: 'The Phoenician Scottsdale 2-Night Golf & Pool Cabana Package',
    description: 'AAA Five-Diamond resort experience in Scottsdale. Deluxe room overlooking Camelback Mountain, 1 round of championship golf for 2, and all-day private pool cabana with refreshments.',
    category: 'travel-resorts',
    source: 'Valley Luxury Getaways',
    price: 480,
    originalPrice: 1250,
    currency: 'USD',
    location: {
      city: 'Scottsdale',
      region: 'Scottsdale & East Valley',
      zipCode: '85251',
      lat: 33.5118,
      lng: -111.9547,
    },
    images: [
      'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Golf Package', 'Five Diamond', 'Camelback View', 'Cabana Pass'],
    features: {
      nights: 2,
      golfRounds: '18 Holes x 2 Players',
      resortRating: '5 Star',
    },
    postedAt: '2026-08-14T12:00:00Z',
    expiresAt: '2026-08-19T23:59:59Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'travel-resorts',
      price: 480,
      originalPrice: 1250,
      marketAveragePrice: 1100,
      conditionRating: 4.9,
      daysOnMarketOrExpiresInDays: 4,
      verified: true,
    }),
  },
  {
    id: 'az-trv-003',
    title: 'Grand Canyon South Rim Cabin + Helicopter Flight Pass for 2',
    description: '2 nights in a private pine cabin outside Tusayan with VIP South Rim Canyon spirit helicopter flight for two and park passes included.',
    category: 'travel-resorts',
    source: 'Northern AZ Excursions',
    price: 550,
    originalPrice: 1190,
    currency: 'USD',
    location: {
      city: 'Flagstaff',
      region: 'Flagstaff & Northern AZ',
      zipCode: '86001',
      lat: 35.1983,
      lng: -111.6513,
    },
    images: [
      'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Grand Canyon', 'Helicopter Tour', 'Cabin Stay', 'Bucket List'],
    features: {
      nights: 2,
      flightDuration: '45 mins',
      parkPass: 'Included',
    },
    postedAt: '2026-08-13T09:00:00Z',
    expiresAt: '2026-08-21T23:59:59Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'travel-resorts',
      price: 550,
      originalPrice: 1190,
      marketAveragePrice: 1050,
      conditionRating: 4.8,
      daysOnMarketOrExpiresInDays: 6,
      verified: true,
    }),
  },

  // 4. Experiences & Dining
  {
    id: 'az-exp-001',
    title: 'Sonora Desert Sunrise Hot Air Balloon Flight + Champagne Breakfast (Pair)',
    description: '1-hour peaceful flight over Sonoran Desert cactus forest at sunrise, followed by traditional champagne celebration and gourmet hot breakfast in Phoenix North.',
    category: 'experiences-dining',
    source: 'Phoenix Balloon Adventures',
    price: 195,
    originalPrice: 460,
    currency: 'USD',
    location: {
      city: 'Phoenix',
      region: 'Phoenix Metro',
      zipCode: '85085',
      lat: 33.7297,
      lng: -112.0831,
    },
    images: [
      'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Hot Air Balloon', 'Sunrise Tour', 'Champagne Breakfast', '58% Off'],
    features: {
      participants: '2 Adults',
      duration: '3.5 hours total',
      beverage: 'Champagne / Cider included',
    },
    postedAt: '2026-08-15T07:15:00Z',
    expiresAt: '2026-08-17T20:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'experiences-dining',
      price: 195,
      originalPrice: 460,
      marketAveragePrice: 420,
      conditionRating: 4.9,
      daysOnMarketOrExpiresInDays: 2,
      verified: true,
    }),
  },
  {
    id: 'az-exp-002',
    title: '6-Course Michelin-Caliber Tasting Menu for 2 in Old Town Scottsdale',
    description: 'Award-winning chef tasting menu pairing Arizona heritage ingredients with sommelier wine selection. Valid Friday or Saturday night bookings.',
    category: 'experiences-dining',
    source: 'Scottsdale Culinary Club',
    price: 175,
    originalPrice: 380,
    currency: 'USD',
    location: {
      city: 'Scottsdale',
      region: 'Scottsdale & East Valley',
      zipCode: '85251',
      lat: 33.4925,
      lng: -111.9254,
    },
    images: [
      'https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Fine Dining', 'Wine Pairing', 'Old Town Scottsdale'],
    features: {
      courses: 6,
      winePairing: 'Included',
      partySize: 2,
    },
    postedAt: '2026-08-14T19:00:00Z',
    expiresAt: '2026-08-20T00:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'experiences-dining',
      price: 175,
      originalPrice: 380,
      marketAveragePrice: 350,
      conditionRating: 4.7,
      daysOnMarketOrExpiresInDays: 5,
      verified: true,
    }),
  },

  // 5. Electronics & High-Value Goods
  {
    id: 'az-elec-001',
    title: 'Apple MacBook Pro 16" M3 Max (64GB RAM, 1TB SSD) - Open Box Chandler Tech Hub',
    description: 'Mint condition Apple Silicon powerhouse originally purchased from Chandler Intel/Tech campus employee. 100% battery capacity, AppleCare+ active until 2027.',
    category: 'electronics-goods',
    source: 'Chandler Tech Liquidators',
    price: 2199,
    originalPrice: 3499,
    currency: 'USD',
    location: {
      city: 'Chandler',
      region: 'Scottsdale & East Valley',
      zipCode: '85226',
      lat: 33.3062,
      lng: -111.8413,
    },
    images: [
      'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['AppleCare+', 'M3 Max', '64GB RAM', 'Huge Discount'],
    features: {
      chip: 'Apple M3 Max 16-Core',
      memory: '64GB Unified',
      storage: '1TB NVMe',
      cycleCount: 12,
    },
    postedAt: '2026-08-15T11:00:00Z',
    expiresAt: '2026-08-18T16:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'electronics-goods',
      price: 2199,
      originalPrice: 3499,
      marketAveragePrice: 3100,
      conditionRating: 5.0,
      estimatedResaleValue: 2850,
      daysOnMarketOrExpiresInDays: 3,
      verified: true,
    }),
  },
  {
    id: 'az-elec-002',
    title: 'Full Commercial Solar Power Inverter & Battery Bank (15kWh Tesla Powerwall 2 equivalent)',
    description: 'Surplus warehouse solar storage bundle in Tempe. Sealed in original crates, UL certified for APS and SRP solar interconnection programs in Arizona.',
    category: 'electronics-goods',
    source: 'Tempe Clean Energy Surplus',
    price: 4900,
    originalPrice: 9800,
    currency: 'USD',
    location: {
      city: 'Tempe',
      region: 'Scottsdale & East Valley',
      zipCode: '85281',
      lat: 33.4255,
      lng: -111.9400,
    },
    images: [
      'https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['SRP/APS Compatible', 'Solar Storage', '50% Off Wholesale', 'Clean Energy'],
    features: {
      capacity: '15.4 kWh',
      inverterOutput: '10 kW Continuous',
      warranty: '10 Year Manufacturer',
    },
    postedAt: '2026-08-12T13:45:00Z',
    expiresAt: '2026-08-24T18:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'electronics-goods',
      price: 4900,
      originalPrice: 9800,
      marketAveragePrice: 8900,
      conditionRating: 4.8,
      estimatedResaleValue: 7500,
      daysOnMarketOrExpiresInDays: 9,
      verified: true,
    }),
  },
  {
    id: 'az-elec-003',
    title: 'Sony Alpha A7 IV Full-Frame Camera + 24-70mm f/2.8 G Master Lens',
    description: 'Camera bundle from Sedona landscape photographer moving abroad. Barely 1,800 shutter clicks, Includes 2 genuine Sony batteries, dual charger, and PolarPro ND filters.',
    category: 'electronics-goods',
    source: 'Flagstaff / Sedona Photographers Exchange',
    price: 1850,
    originalPrice: 3200,
    currency: 'USD',
    location: {
      city: 'Sedona',
      region: 'Sedona & Verde Valley',
      zipCode: '86336',
      lat: 34.8697,
      lng: -111.7610,
    },
    images: [
      'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['G Master Lens', 'Low Shutter Count', '4K60p Video', 'Landscape Pro'],
    features: {
      sensor: '33MP Full-Frame Exmor R',
      shutterCount: 1820,
      lensIncluded: 'Sony 24-70mm GM f/2.8',
    },
    postedAt: '2026-08-15T05:30:00Z',
    expiresAt: '2026-08-17T18:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'electronics-goods',
      price: 1850,
      originalPrice: 3200,
      marketAveragePrice: 2800,
      conditionRating: 4.9,
      estimatedResaleValue: 2600,
      daysOnMarketOrExpiresInDays: 2,
      verified: true,
    }),
  },
  {
    id: 'az-re-004',
    title: 'North Scottsdale Luxury Equestrian Estate on 2.5 Acres (Distressed Note)',
    description: 'Custom Santa Fe luxury estate with 6-stall barn, lighted arena, resort swimming pool, and guest home. Lender note liquidation priced dramatically below replacement cost.',
    category: 'real-estate',
    source: 'Scottsdale Luxury Distressed Assets',
    price: 1250000,
    originalPrice: 1890000,
    currency: 'USD',
    location: {
      city: 'Scottsdale',
      region: 'Scottsdale & East Valley',
      zipCode: '85262',
      lat: 33.7431,
      lng: -111.8340,
    },
    images: [
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Equestrian', '2.5 Acres', 'Luxury Guest House', 'Pinnacle Peak'],
    features: {
      sqft: 5200,
      beds: 5,
      baths: 6,
      acreage: 2.5,
      barnStalls: 6,
    },
    postedAt: '2026-08-10T15:00:00Z',
    expiresAt: '2026-08-26T23:59:59Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'real-estate',
      price: 1250000,
      originalPrice: 1890000,
      marketAveragePrice: 1800000,
      conditionRating: 4.9,
      estimatedResaleValue: 1750000,
      daysOnMarketOrExpiresInDays: 11,
      verified: true,
    }),
  },
  {
    id: 'az-veh-004',
    title: '2020 Chevrolet Corvette Stingray 3LT Z51 Coupe',
    description: 'Torch Red mid-engine Corvette with GT2 bucket seats, magnetic ride control, front lift system, and transparent roof panel. Arizona garaged with 9,100 miles.',
    category: 'vehicles',
    source: 'Chandler Supercars Liquidation',
    price: 54900,
    originalPrice: 76000,
    currency: 'USD',
    location: {
      city: 'Chandler',
      region: 'Scottsdale & East Valley',
      zipCode: '85224',
      lat: 33.3062,
      lng: -111.8413,
    },
    images: [
      'https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=800&q=80',
    ],
    tags: ['Z51 Package', 'Low Mileage', '3LT Top Trim', 'Under Book Value'],
    features: {
      mileage: '9,100 mi',
      engine: '6.2L LT2 V8 (495 hp)',
      transmission: '8-Speed Dual-Clutch',
      color: 'Torch Red',
    },
    postedAt: '2026-08-15T03:00:00Z',
    expiresAt: '2026-08-19T12:00:00Z',
    verified: true,
    valueScore: calculateValueScore({
      category: 'vehicles',
      price: 54900,
      originalPrice: 76000,
      marketAveragePrice: 68000,
      conditionRating: 4.9,
      estimatedResaleValue: 66000,
      daysOnMarketOrExpiresInDays: 4,
      verified: true,
    }),
  }
];

export function getFilteredAndRankedDeals(deals: Deal[], filters: DealFilterOptions = {}): Deal[] {
  let filtered = [...deals];

  // Category filter
  if (filters.category && filters.category !== 'all') {
    filtered = filtered.filter((deal) => deal.category === filters.category);
  }

  // Region filter
  if (filters.region && filters.region !== 'all') {
    filtered = filtered.filter((deal) => deal.location.region === filters.region);
  }

  // Value tier filter
  if (filters.valueTier && filters.valueTier !== 'all') {
    filtered = filtered.filter((deal) => deal.valueScore.valueTier === filters.valueTier);
  }

  // Minimum score filter
  if (filters.minScore !== undefined && filters.minScore > 0) {
    filtered = filtered.filter((deal) => deal.valueScore.compositeScore >= (filters.minScore || 0));
  }

  // Price range filter
  if (filters.minPrice !== undefined) {
    filtered = filtered.filter((deal) => deal.price >= (filters.minPrice || 0));
  }
  if (filters.maxPrice !== undefined && filters.maxPrice > 0) {
    filtered = filtered.filter((deal) => deal.price <= (filters.maxPrice || Infinity));
  }

  // Search keyword filter
  if (filters.search && filters.search.trim() !== '') {
    const q = filters.search.toLowerCase().trim();
    filtered = filtered.filter((deal) => {
      const inTitle = deal.title.toLowerCase().includes(q);
      const inDesc = deal.description.toLowerCase().includes(q);
      const inCity = deal.location.city.toLowerCase().includes(q);
      const inRegion = deal.location.region.toLowerCase().includes(q);
      const inTags = deal.tags.some((t) => t.toLowerCase().includes(q));
      return inTitle || inDesc || inCity || inRegion || inTags;
    });
  }

  // Sorting
  const sortBy = filters.sortBy || 'score';
  filtered.sort((a, b) => {
    switch (sortBy) {
      case 'score':
        return b.valueScore.compositeScore - a.valueScore.compositeScore;
      case 'savings_desc':
        return b.valueScore.savingsDollars - a.valueScore.savingsDollars;
      case 'savings_pct':
        return b.valueScore.savingsPercentage - a.valueScore.savingsPercentage;
      case 'price_asc':
        return a.price - b.price;
      case 'price_desc':
        return b.price - a.price;
      case 'newest':
        return new Date(b.postedAt).getTime() - new Date(a.postedAt).getTime();
      default:
        return b.valueScore.compositeScore - a.valueScore.compositeScore;
    }
  });

  return filtered;
}

export function computeDealStats(deals: Deal[]): DealStats {
  const totalDeals = deals.length;
  if (totalDeals === 0) {
    return {
      totalDeals: 0,
      averageDiscountPct: 0,
      totalPotentialSavings: 0,
      topCategory: 'real-estate',
      topRegion: 'Phoenix Metro',
      dealCountsByCategory: {
        'real-estate': 0,
        'vehicles': 0,
        'travel-resorts': 0,
        'experiences-dining': 0,
        'electronics-goods': 0,
      },
      dealCountsByRegion: {
        'Phoenix Metro': 0,
        'Scottsdale & East Valley': 0,
        'Tucson & Southern AZ': 0,
        'Flagstaff & Northern AZ': 0,
        'Sedona & Verde Valley': 0,
        'Yuma & Western AZ': 0,
        'Statewide / Online': 0,
      },
    };
  }

  let totalSavings = 0;
  let totalPct = 0;
  const categoryCounts: Record<DealCategory, number> = {
    'real-estate': 0,
    'vehicles': 0,
    'travel-resorts': 0,
    'experiences-dining': 0,
    'electronics-goods': 0,
  };

  const regionCounts: Record<ArizonaRegion, number> = {
    'Phoenix Metro': 0,
    'Scottsdale & East Valley': 0,
    'Tucson & Southern AZ': 0,
    'Flagstaff & Northern AZ': 0,
    'Sedona & Verde Valley': 0,
    'Yuma & Western AZ': 0,
    'Statewide / Online': 0,
  };

  deals.forEach((d) => {
    totalSavings += d.valueScore.savingsDollars;
    totalPct += d.valueScore.savingsPercentage;
    categoryCounts[d.category] = (categoryCounts[d.category] || 0) + 1;
    regionCounts[d.location.region] = (regionCounts[d.location.region] || 0) + 1;
  });

  const topCategory = (Object.keys(categoryCounts) as DealCategory[]).reduce((a, b) =>
    categoryCounts[a] > categoryCounts[b] ? a : b
  );

  const topRegion = (Object.keys(regionCounts) as ArizonaRegion[]).reduce((a, b) =>
    regionCounts[a] > regionCounts[b] ? a : b
  );

  return {
    totalDeals,
    averageDiscountPct: Math.round(totalPct / totalDeals),
    totalPotentialSavings: Math.round(totalSavings),
    topCategory,
    topRegion,
    dealCountsByCategory: categoryCounts,
    dealCountsByRegion: regionCounts,
  };
}
