export type Strategy = 'balanced' | 'cash-flow' | 'appreciation' | 'affordable'

export type PropertyType = 'Single family' | 'Townhome' | 'Condo' | 'Duplex'

export interface Deal {
  id: string
  address: string
  city: string
  zip: string
  neighborhood: string
  propertyType: PropertyType
  price: number
  marketValue: number
  monthlyRent: number
  monthlyCashFlow: number
  capRate: number
  annualGrowth: number
  rehabEstimate: number
  beds: number
  baths: number
  sqft: number
  yearBuilt: number
  daysOnMarket: number
  image: string
  imageAlt: string
  tags: string[]
  summary: string
  source: string
}

export interface ScoreBreakdown {
  total: number
  affordability: number
  cashFlow: number
  yield: number
  discount: number
  market: number
}

export type SortOption = 'score' | 'price' | 'cap-rate' | 'discount'

export type ViewMode = 'list' | 'grid'
