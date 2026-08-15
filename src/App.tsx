import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  Bath,
  BedDouble,
  Bookmark,
  Building2,
  Check,
  ChevronDown,
  CircleDollarSign,
  Clock3,
  Grid2X2,
  Heart,
  House,
  Info,
  LayoutList,
  MapPin,
  RotateCcw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Square,
  TrendingUp,
  X,
} from 'lucide-react'
import { deals } from './data/deals'
import {
  formatCurrency,
  getDiscountPercent,
  getScoreLabel,
  rankDeals,
  scoreDeal,
} from './lib/scoring'
import type {
  Deal,
  PropertyType,
  SortOption,
  Strategy,
  ViewMode,
} from './types'
import './App.css'

const strategies: { id: Strategy; label: string; description: string }[] = [
  {
    id: 'balanced',
    label: 'Best overall',
    description: 'Balances price, yield, upside, and market momentum.',
  },
  {
    id: 'cash-flow',
    label: 'Cash flow',
    description: 'Prioritizes monthly income and cap rate.',
  },
  {
    id: 'appreciation',
    label: 'Growth',
    description: 'Favors resilient markets with stronger appreciation.',
  },
  {
    id: 'affordable',
    label: 'Lowest entry',
    description: 'Surfaces the most accessible purchase prices first.',
  },
]

const propertyTypes: Array<'All types' | PropertyType> = [
  'All types',
  'Single family',
  'Townhome',
  'Condo',
  'Duplex',
]

const scoreFactors = [
  { key: 'discount', label: 'Price advantage' },
  { key: 'yield', label: 'Cap rate' },
  { key: 'cashFlow', label: 'Cash flow' },
  { key: 'affordability', label: 'Affordability' },
  { key: 'market', label: 'Market strength' },
] as const

function App() {
  const [strategy, setStrategy] = useState<Strategy>('balanced')
  const [query, setQuery] = useState('')
  const [city, setCity] = useState('All Arizona')
  const [maxPrice, setMaxPrice] = useState(500000)
  const [propertyType, setPropertyType] = useState<
    'All types' | PropertyType
  >('All types')
  const [minScore, setMinScore] = useState(50)
  const [sort, setSort] = useState<SortOption>('score')
  const [view, setView] = useState<ViewMode>('list')
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [methodologyOpen, setMethodologyOpen] = useState(false)
  const [savedOnly, setSavedOnly] = useState(false)
  const [savedIds, setSavedIds] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('az-deal-scout-saved') ?? '[]')
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem('az-deal-scout-saved', JSON.stringify(savedIds))
  }, [savedIds])

  useEffect(() => {
    document.body.style.overflow =
      selectedDeal || methodologyOpen || filtersOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [selectedDeal, methodologyOpen, filtersOpen])

  const cities = useMemo(
    () => ['All Arizona', ...new Set(deals.map((deal) => deal.city))],
    [],
  )

  const rankedDeals = useMemo(() => rankDeals(deals, strategy), [strategy])
  const topDeal = rankedDeals[0]

  const visibleDeals = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    const filtered = deals.filter((deal) => {
      const searchable = [
        deal.address,
        deal.city,
        deal.zip,
        deal.neighborhood,
      ]
        .join(' ')
        .toLowerCase()

      return (
        (!normalizedQuery || searchable.includes(normalizedQuery)) &&
        (city === 'All Arizona' || deal.city === city) &&
        deal.price <= maxPrice &&
        (propertyType === 'All types' ||
          deal.propertyType === propertyType) &&
        scoreDeal(deal, strategy).total >= minScore &&
        (!savedOnly || savedIds.includes(deal.id))
      )
    })

    return [...filtered].sort((first, second) => {
      if (sort === 'price') return first.price - second.price
      if (sort === 'cap-rate') return second.capRate - first.capRate
      if (sort === 'discount') {
        return getDiscountPercent(second) - getDiscountPercent(first)
      }
      return (
        scoreDeal(second, strategy).total -
        scoreDeal(first, strategy).total
      )
    })
  }, [
    city,
    maxPrice,
    minScore,
    propertyType,
    query,
    savedIds,
    savedOnly,
    sort,
    strategy,
  ])

  const activeFilterCount = [
    city !== 'All Arizona',
    maxPrice !== 500000,
    propertyType !== 'All types',
    minScore !== 50,
    savedOnly,
  ].filter(Boolean).length

  const averageDiscount = Math.round(
    deals.reduce((total, deal) => total + getDiscountPercent(deal), 0) /
      deals.length,
  )

  const toggleSaved = (dealId: string) => {
    setSavedIds((current) =>
      current.includes(dealId)
        ? current.filter((id) => id !== dealId)
        : [...current, dealId],
    )
  }

  const resetFilters = () => {
    setCity('All Arizona')
    setMaxPrice(500000)
    setPropertyType('All types')
    setMinScore(50)
    setSavedOnly(false)
  }

  const scrollToDeals = () => {
    document.getElementById('deals')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="container header-inner">
          <button className="brand" type="button" onClick={() => scrollTo(0, 0)}>
            <span className="brand-mark">
              <House size={19} strokeWidth={2.4} />
            </span>
            <span>
              Arizona
              <strong>Deal Scout</strong>
            </span>
          </button>

          <nav className="desktop-nav" aria-label="Primary navigation">
            <button type="button" onClick={scrollToDeals}>
              Deal finder
            </button>
            <button type="button" onClick={() => setMethodologyOpen(true)}>
              How scoring works
            </button>
          </nav>

          <div className="header-actions">
            <button
              className={`saved-button ${savedOnly ? 'active' : ''}`}
              type="button"
              onClick={() => {
                setSavedOnly((current) => !current)
                scrollToDeals()
              }}
            >
              <Heart
                size={17}
                fill={savedOnly ? 'currentColor' : 'none'}
              />
              <span>Saved</span>
              <span className="saved-count">{savedIds.length}</span>
            </button>
            <span className="avatar" aria-label="Demo user">
              KD
            </span>
          </div>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-sun" aria-hidden="true" />
          <div className="container hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">
                <Sparkles size={15} />
                Arizona investment intelligence
              </div>
              <h1>
                Find the upside
                <br />
                <em>before everyone else.</em>
              </h1>
              <p>
                Compare residential opportunities across Arizona with one
                transparent value score—built from price, yield, cash flow, and
                local momentum.
              </p>

              <div className="hero-search">
                <Search size={20} />
                <input
                  aria-label="Search by city, ZIP, or neighborhood"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') scrollToDeals()
                  }}
                  placeholder="Search city, ZIP, or neighborhood"
                />
                <button type="button" onClick={scrollToDeals}>
                  Find deals
                  <ArrowRight size={18} />
                </button>
              </div>

              <div className="market-pulse">
                <span>
                  <strong>{deals.length}</strong> opportunities
                </span>
                <span className="pulse-divider" />
                <span>
                  <strong>{cities.length - 1}</strong> Arizona markets
                </span>
                <span className="pulse-divider" />
                <span>
                  <strong>{averageDiscount}%</strong> avg. price advantage
                </span>
              </div>
            </div>

            <div className="standout-card">
              <div className="standout-image-wrap">
                <img src={topDeal.image} alt={topDeal.imageAlt} />
                <span className="demo-pill">Curated demo data</span>
                <div className="top-score">
                  <span>{scoreDeal(topDeal, strategy).total}</span>
                  <small>value score</small>
                </div>
              </div>
              <div className="standout-content">
                <div className="standout-kicker">
                  <span>
                    <Sparkles size={14} /> Today&apos;s standout
                  </span>
                  <span>{getScoreLabel(scoreDeal(topDeal, strategy).total)}</span>
                </div>
                <h2>{topDeal.address}</h2>
                <p>
                  {topDeal.city}, AZ · {topDeal.neighborhood}
                </p>
                <div className="standout-metrics">
                  <div>
                    <span>Asking</span>
                    <strong>{formatCurrency(topDeal.price)}</strong>
                  </div>
                  <div>
                    <span>Cash flow</span>
                    <strong className="positive">
                      +{formatCurrency(topDeal.monthlyCashFlow)}/mo
                    </strong>
                  </div>
                  <div>
                    <span>Cap rate</span>
                    <strong>{topDeal.capRate}%</strong>
                  </div>
                </div>
                <button
                  className="text-link"
                  type="button"
                  onClick={() => setSelectedDeal(topDeal)}
                >
                  See why it ranks #1 <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="finder-section" id="deals">
          <div className="container">
            <div className="section-heading">
              <div>
                <span className="section-kicker">Deal finder</span>
                <h2>Ranked for your strategy</h2>
                <p>
                  Change your priority and the shortlist re-ranks instantly.
                </p>
              </div>
              <button
                className="method-button"
                type="button"
                onClick={() => setMethodologyOpen(true)}
              >
                <Info size={17} />
                Score methodology
              </button>
            </div>

            <div className="strategy-picker" role="group" aria-label="Strategy">
              {strategies.map((option) => (
                <button
                  key={option.id}
                  className={strategy === option.id ? 'active' : ''}
                  type="button"
                  onClick={() => setStrategy(option.id)}
                >
                  <span>{option.label}</span>
                  <small>{option.description}</small>
                  {strategy === option.id && (
                    <span className="selected-check">
                      <Check size={13} />
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="mobile-toolbar">
              <button
                className="filter-trigger"
                type="button"
                onClick={() => setFiltersOpen(true)}
              >
                <SlidersHorizontal size={17} />
                Filters
                {activeFilterCount > 0 && (
                  <span>{activeFilterCount}</span>
                )}
              </button>
              <span>{visibleDeals.length} matches</span>
            </div>

            <div className="finder-layout">
              <aside className={`filter-panel ${filtersOpen ? 'open' : ''}`}>
                <div className="mobile-filter-head">
                  <h3>Filters</h3>
                  <button
                    type="button"
                    aria-label="Close filters"
                    onClick={() => setFiltersOpen(false)}
                  >
                    <X size={21} />
                  </button>
                </div>
                <div className="filter-heading">
                  <div>
                    <SlidersHorizontal size={17} />
                    <h3>Refine</h3>
                    {activeFilterCount > 0 && (
                      <span>{activeFilterCount}</span>
                    )}
                  </div>
                  <button type="button" onClick={resetFilters}>
                    Reset
                  </button>
                </div>

                <div className="filter-group">
                  <label htmlFor="city">Market</label>
                  <div className="select-wrap">
                    <MapPin size={16} />
                    <select
                      id="city"
                      value={city}
                      onChange={(event) => setCity(event.target.value)}
                    >
                      {cities.map((option) => (
                        <option key={option}>{option}</option>
                      ))}
                    </select>
                    <ChevronDown size={15} />
                  </div>
                </div>

                <div className="filter-group">
                  <div className="label-row">
                    <label htmlFor="price">Maximum price</label>
                    <strong>{formatCurrency(maxPrice, true)}</strong>
                  </div>
                  <input
                    id="price"
                    className="range-input"
                    type="range"
                    min="200000"
                    max="500000"
                    step="25000"
                    value={maxPrice}
                    onChange={(event) => setMaxPrice(Number(event.target.value))}
                    style={{
                      background: `linear-gradient(to right, #e4773d 0%, #e4773d ${
                        ((maxPrice - 200000) / 300000) * 100
                      }%, #e5e1d9 ${
                        ((maxPrice - 200000) / 300000) * 100
                      }%, #e5e1d9 100%)`,
                    }}
                  />
                  <div className="range-labels">
                    <span>$200K</span>
                    <span>$500K</span>
                  </div>
                </div>

                <div className="filter-group">
                  <label>Property type</label>
                  <div className="type-options">
                    {propertyTypes.map((type) => (
                      <button
                        key={type}
                        className={propertyType === type ? 'active' : ''}
                        type="button"
                        onClick={() => setPropertyType(type)}
                      >
                        {type}
                        {propertyType === type && <Check size={14} />}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="filter-group">
                  <div className="label-row">
                    <label htmlFor="score">Minimum value score</label>
                    <strong>{minScore}+</strong>
                  </div>
                  <input
                    id="score"
                    className="range-input"
                    type="range"
                    min="40"
                    max="85"
                    step="5"
                    value={minScore}
                    onChange={(event) => setMinScore(Number(event.target.value))}
                    style={{
                      background: `linear-gradient(to right, #e4773d 0%, #e4773d ${
                        ((minScore - 40) / 45) * 100
                      }%, #e5e1d9 ${
                        ((minScore - 40) / 45) * 100
                      }%, #e5e1d9 100%)`,
                    }}
                  />
                  <div className="range-labels">
                    <span>Any</span>
                    <span>Top tier</span>
                  </div>
                </div>

                <div className="filter-note">
                  <ShieldCheck size={19} />
                  <p>
                    <strong>Built for comparison.</strong>
                    Scores use the same assumptions across every deal.
                  </p>
                </div>

                <button
                  className="apply-filters"
                  type="button"
                  onClick={() => setFiltersOpen(false)}
                >
                  Show {visibleDeals.length} deals
                </button>
              </aside>

              {filtersOpen && (
                <button
                  className="filter-backdrop"
                  type="button"
                  aria-label="Close filters"
                  onClick={() => setFiltersOpen(false)}
                />
              )}

              <div className="results-panel">
                <div className="results-toolbar">
                  <div>
                    <strong>{visibleDeals.length} opportunities</strong>
                    <span>
                      {savedOnly
                        ? 'Your saved shortlist'
                        : `Across ${cities.length - 1} Arizona markets`}
                    </span>
                  </div>
                  <div className="results-actions">
                    <label className="sort-control">
                      <span>Sort</span>
                      <select
                        aria-label="Sort deals"
                        value={sort}
                        onChange={(event) =>
                          setSort(event.target.value as SortOption)
                        }
                      >
                        <option value="score">Best value</option>
                        <option value="price">Lowest price</option>
                        <option value="cap-rate">Highest cap rate</option>
                        <option value="discount">Biggest discount</option>
                      </select>
                      <ChevronDown size={14} />
                    </label>
                    <div className="view-toggle" aria-label="View">
                      <button
                        className={view === 'list' ? 'active' : ''}
                        type="button"
                        aria-label="List view"
                        onClick={() => setView('list')}
                      >
                        <LayoutList size={17} />
                      </button>
                      <button
                        className={view === 'grid' ? 'active' : ''}
                        type="button"
                        aria-label="Grid view"
                        onClick={() => setView('grid')}
                      >
                        <Grid2X2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>

                {visibleDeals.length > 0 ? (
                  <div className={`deal-list ${view}`}>
                    {visibleDeals.map((deal, index) => {
                      const score = scoreDeal(deal, strategy)
                      const saved = savedIds.includes(deal.id)
                      return (
                        <article
                          className="deal-card"
                          key={deal.id}
                          tabIndex={0}
                          onClick={() => setSelectedDeal(deal)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') setSelectedDeal(deal)
                          }}
                        >
                          <div className="deal-image">
                            <img src={deal.image} alt={deal.imageAlt} />
                            <span className="rank-badge">#{index + 1}</span>
                            <button
                              className={`save-icon ${saved ? 'saved' : ''}`}
                              type="button"
                              aria-label={
                                saved ? 'Remove from saved' : 'Save deal'
                              }
                              onClick={(event) => {
                                event.stopPropagation()
                                toggleSaved(deal.id)
                              }}
                            >
                              <Bookmark
                                size={18}
                                fill={saved ? 'currentColor' : 'none'}
                              />
                            </button>
                          </div>

                          <div className="deal-info">
                            <div className="deal-tags">
                              {deal.tags.map((tag) => (
                                <span key={tag}>{tag}</span>
                              ))}
                            </div>
                            <h3>{deal.address}</h3>
                            <p className="deal-location">
                              <MapPin size={14} />
                              {deal.city}, AZ {deal.zip} · {deal.neighborhood}
                            </p>
                            <div className="property-facts">
                              <span>
                                <BedDouble size={15} /> {deal.beds} beds
                              </span>
                              <span>
                                <Bath size={15} /> {deal.baths} baths
                              </span>
                              <span>
                                <Square size={14} />{' '}
                                {deal.sqft.toLocaleString()} ft²
                              </span>
                            </div>
                            <div className="deal-metrics">
                              <div>
                                <span>Cap rate</span>
                                <strong>{deal.capRate}%</strong>
                              </div>
                              <div>
                                <span>Cash flow</span>
                                <strong className="positive">
                                  +{formatCurrency(deal.monthlyCashFlow)}/mo
                                </strong>
                              </div>
                              <div>
                                <span>Below value</span>
                                <strong>
                                  {Math.round(getDiscountPercent(deal))}%
                                </strong>
                              </div>
                            </div>
                          </div>

                          <div className="deal-summary">
                            <div className="score-badge">
                              <div
                                className="mini-score-ring"
                                style={{
                                  background: `conic-gradient(#e4773d ${score.total}%, #eee9df 0)`,
                                }}
                              >
                                <span>{score.total}</span>
                              </div>
                              <div>
                                <small>Value score</small>
                                <strong>{getScoreLabel(score.total)}</strong>
                              </div>
                            </div>
                            <div className="deal-price">
                              <span>Asking price</span>
                              <strong>{formatCurrency(deal.price)}</strong>
                              <small>
                                {formatCurrency(
                                  deal.marketValue - deal.price,
                                  true,
                                )}{' '}
                                below estimated value
                              </small>
                            </div>
                            <button className="details-button" type="button">
                              View analysis <ArrowRight size={15} />
                            </button>
                          </div>
                        </article>
                      )
                    })}
                  </div>
                ) : (
                  <div className="empty-state">
                    <span>
                      <Search size={24} />
                    </span>
                    <h3>No deals match those filters</h3>
                    <p>
                      Widen your price or score range to see more Arizona
                      opportunities.
                    </p>
                    <button type="button" onClick={resetFilters}>
                      <RotateCcw size={16} /> Reset filters
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer>
        <div className="container footer-inner">
          <div className="footer-brand">
            <span className="brand-mark">
              <House size={17} />
            </span>
            <strong>Arizona Deal Scout</strong>
          </div>
          <p>
            MVP uses illustrative listing data and underwriting assumptions.
            Verify all figures before making an investment decision.
          </p>
          <span>Built for the Grand Canyon State.</span>
        </div>
      </footer>

      {selectedDeal && (
        <DealDrawer
          deal={selectedDeal}
          strategy={strategy}
          isSaved={savedIds.includes(selectedDeal.id)}
          onClose={() => setSelectedDeal(null)}
          onToggleSaved={() => toggleSaved(selectedDeal.id)}
        />
      )}

      {methodologyOpen && (
        <MethodologyModal
          strategy={strategy}
          onClose={() => setMethodologyOpen(false)}
        />
      )}
    </div>
  )
}

function DealDrawer({
  deal,
  strategy,
  isSaved,
  onClose,
  onToggleSaved,
}: {
  deal: Deal
  strategy: Strategy
  isSaved: boolean
  onClose: () => void
  onToggleSaved: () => void
}) {
  const score = scoreDeal(deal, strategy)

  return (
    <div className="modal-layer" role="dialog" aria-modal="true">
      <button
        className="modal-backdrop"
        type="button"
        aria-label="Close property details"
        onClick={onClose}
      />
      <aside className="deal-drawer">
        <button className="drawer-close" type="button" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="drawer-hero">
          <img src={deal.image} alt={deal.imageAlt} />
          <div className="drawer-overlay" />
          <span className="drawer-demo">Illustrative listing</span>
          <div className="drawer-title">
            <div className="deal-tags">
              {deal.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
            <h2>{deal.address}</h2>
            <p>
              <MapPin size={14} /> {deal.city}, AZ {deal.zip} ·{' '}
              {deal.neighborhood}
            </p>
          </div>
        </div>

        <div className="drawer-body">
          <div className="drawer-score-row">
            <div
              className="large-score-ring"
              style={{
                background: `conic-gradient(#e4773d ${score.total}%, #eee8dc 0)`,
              }}
            >
              <div>
                <strong>{score.total}</strong>
                <span>/ 100</span>
              </div>
            </div>
            <div>
              <span className="drawer-kicker">Deal score</span>
              <h3>{getScoreLabel(score.total)}</h3>
              <p>
                Ranked using the{' '}
                {strategies.find((item) => item.id === strategy)?.label.toLowerCase()}{' '}
                strategy.
              </p>
            </div>
          </div>

          <div className="underwriting-grid">
            <div>
              <CircleDollarSign size={18} />
              <span>Purchase price</span>
              <strong>{formatCurrency(deal.price)}</strong>
            </div>
            <div>
              <TrendingUp size={18} />
              <span>Est. market value</span>
              <strong>{formatCurrency(deal.marketValue)}</strong>
            </div>
            <div>
              <Building2 size={18} />
              <span>Est. rent</span>
              <strong>{formatCurrency(deal.monthlyRent)}/mo</strong>
            </div>
            <div>
              <Clock3 size={18} />
              <span>Days on market</span>
              <strong>{deal.daysOnMarket} days</strong>
            </div>
          </div>

          <section className="drawer-section">
            <div className="drawer-section-heading">
              <h3>What drives the score</h3>
              <span>Relative to this demo set</span>
            </div>
            <div className="score-breakdown">
              {scoreFactors.map((factor) => (
                <div className="score-factor" key={factor.key}>
                  <div>
                    <span>{factor.label}</span>
                    <strong>{score[factor.key]}</strong>
                  </div>
                  <div className="score-track">
                    <span style={{ width: `${score[factor.key]}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="drawer-section why-section">
            <h3>Why it stands out</h3>
            <p>{deal.summary}</p>
            <div className="highlight-row">
              <span>
                <TrendingUp size={16} />
                {deal.annualGrowth}% projected market growth
              </span>
              <span>
                <CircleDollarSign size={16} />
                {formatCurrency(deal.rehabEstimate, true)} est. rehab
              </span>
            </div>
          </section>

          <div className="drawer-disclaimer">
            <Info size={16} />
            <p>
              {deal.source}. Estimates are illustrative and are not financial
              advice. Run full due diligence before purchase.
            </p>
          </div>
        </div>

        <div className="drawer-footer">
          <div>
            <span>Potential equity</span>
            <strong>
              {formatCurrency(deal.marketValue - deal.price - deal.rehabEstimate)}
            </strong>
          </div>
          <button
            className={isSaved ? 'saved' : ''}
            type="button"
            onClick={onToggleSaved}
          >
            <Bookmark size={17} fill={isSaved ? 'currentColor' : 'none'} />
            {isSaved ? 'Saved to shortlist' : 'Save to shortlist'}
          </button>
        </div>
      </aside>
    </div>
  )
}

function MethodologyModal({
  strategy,
  onClose,
}: {
  strategy: Strategy
  onClose: () => void
}) {
  const activeStrategy = strategies.find((item) => item.id === strategy)

  return (
    <div className="modal-layer centered" role="dialog" aria-modal="true">
      <button
        className="modal-backdrop"
        type="button"
        aria-label="Close methodology"
        onClick={onClose}
      />
      <section className="method-modal">
        <button className="drawer-close" type="button" onClick={onClose}>
          <X size={20} />
        </button>
        <span className="method-icon">
          <Sparkles size={20} />
        </span>
        <span className="section-kicker">Transparent by design</span>
        <h2>One score. Five value signals.</h2>
        <p>
          Every property is scored from 0–100 against the same Arizona demo
          set. Your selected strategy changes the weight of each signal—not the
          underlying property data.
        </p>
        <div className="method-factors">
          {[
            ['Price advantage', 'Discount to estimated market value', '24%'],
            ['Cap rate', 'Unlevered annual return', '24%'],
            ['Cash flow', 'Estimated income after financing', '22%'],
            ['Affordability', 'Lower capital required to enter', '18%'],
            ['Market strength', 'Projected local appreciation', '12%'],
          ].map(([title, description, weight], index) => (
            <div key={title}>
              <span>0{index + 1}</span>
              <p>
                <strong>{title}</strong>
                <small>{description}</small>
              </p>
              <b>{weight}</b>
            </div>
          ))}
        </div>
        <div className="active-method">
          <Check size={17} />
          <p>
            <strong>Current strategy: {activeStrategy?.label}</strong>
            {activeStrategy?.description}
          </p>
        </div>
        <button className="method-done" type="button" onClick={onClose}>
          Got it
        </button>
      </section>
    </div>
  )
}

export default App
