'use client';

import React, { useState, useEffect } from 'react';
import { Deal, DealFilterOptions, DealStats, ArizonaRegion } from '@/types/deal';
import { Navbar } from '@/components/Navbar';
import { StatsBar } from '@/components/StatsBar';
import { FilterBar } from '@/components/FilterBar';
import { DealCard } from '@/components/DealCard';
import { DealMap } from '@/components/DealMap';
import { RoiCalculatorModal } from '@/components/RoiCalculatorModal';
import { SubmitDealModal } from '@/components/SubmitDealModal';
import { Sparkles, RefreshCw, AlertTriangle, Zap } from 'lucide-react';

export default function Home() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [stats, setStats] = useState<DealStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters State
  const [filters, setFilters] = useState<DealFilterOptions>({
    category: 'all',
    region: 'all',
    valueTier: 'all',
    sortBy: 'score',
    search: '',
  });

  // Modals state
  const [isCalculatorOpen, setIsCalculatorOpen] = useState(false);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [selectedDealForRoi, setSelectedDealForRoi] = useState<Deal | null>(null);

  const fetchDeals = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.category && filters.category !== 'all') params.set('category', filters.category);
      if (filters.region && filters.region !== 'all') params.set('region', filters.region);
      if (filters.valueTier && filters.valueTier !== 'all') params.set('valueTier', filters.valueTier);
      if (filters.search) params.set('search', filters.search);
      if (filters.sortBy) params.set('sortBy', filters.sortBy);

      const res = await fetch(`/api/deals?${params.toString()}`);
      const data = await res.json();

      if (data.success) {
        setDeals(data.deals);
        setStats(data.stats);
      } else {
        setError(data.error || 'Failed to fetch deals');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with AZ Deal Agent');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [filters]);

  const handleUpdateFilters = (newFilters: Partial<DealFilterOptions>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  const handleResetFilters = () => {
    setFilters({
      category: 'all',
      region: 'all',
      valueTier: 'all',
      sortBy: 'score',
      search: '',
    });
  };

  const handleOpenRoiWithDeal = (deal: Deal) => {
    setSelectedDealForRoi(deal);
    setIsCalculatorOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between">
      <div>
        {/* Navbar */}
        <Navbar
          dealCount={stats?.totalDeals || deals.length}
          onOpenSubmitModal={() => setIsSubmitModalOpen(true)}
          onOpenCalculator={() => {
            setSelectedDealForRoi(deals[0] || null);
            setIsCalculatorOpen(true);
          }}
        />

        {/* Hero Section */}
        <div className="relative overflow-hidden border-b border-slate-800/80 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-950 py-12 sm:py-16">
          <div className="absolute inset-0 bg-[radial-gradient(#c86d3b_1px,transparent_1px)] [background-size:24px_24px] opacity-10 pointer-events-none" />
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold mb-4">
              <Zap className="w-3.5 h-3.5" />
              <span>Autonomous Arizona Value Intelligence Agent</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white mb-4">
              Find Arizona’s <span className="az-gradient-text">Highest Value</span> & Lowest Cost Deals
            </h1>

            <p className="max-w-2xl mx-auto text-sm sm:text-base text-slate-300 mb-8 leading-relaxed">
              Real-time multi-category ranking engine scanning Arizona Real Estate, Vehicles, Luxury Resorts, Dining, and Surplus Tech. Scored on discount depth, ROI margin, historical comps, and quality.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                onClick={() => {
                  setSelectedDealForRoi(deals[0] || null);
                  setIsCalculatorOpen(true);
                }}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-bold text-sm shadow-lg shadow-orange-600/25 transition transform active:scale-95"
              >
                Launch Value Simulator
              </button>

              <button
                onClick={() => setIsSubmitModalOpen(true)}
                className="px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-sm transition"
              >
                Analyze Custom AZ Listing
              </button>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Key Stats Bar */}
          {stats && <StatsBar stats={stats} />}

          {/* Regional Radar */}
          <DealMap
            deals={deals}
            selectedRegion={filters.region}
            onFilterRegion={(reg: ArizonaRegion) => handleUpdateFilters({ region: reg === filters.region ? 'all' : reg })}
          />

          {/* Filters & Sorting */}
          <FilterBar
            filters={filters}
            onChangeFilters={handleUpdateFilters}
            onResetFilters={handleResetFilters}
          />

          {/* Error notice */}
          {error && (
            <div className="my-6 p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center space-x-3 text-rose-400 text-sm">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Deals Grid Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              <h2 className="text-xl font-black text-white">
                Ranked Best Value Deals ({deals.length})
              </h2>
            </div>
            
            <button
              onClick={fetchDeals}
              disabled={loading}
              className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-200 font-medium py-1.5 px-3 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh AI Comps</span>
            </button>
          </div>

          {/* Deals Cards Grid */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 py-12">
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <div key={n} className="bg-slate-900/60 border border-slate-800 rounded-2xl h-96 animate-pulse p-4 space-y-4">
                  <div className="h-44 bg-slate-800 rounded-xl" />
                  <div className="h-4 bg-slate-800 rounded w-3/4" />
                  <div className="h-3 bg-slate-800 rounded w-1/2" />
                  <div className="h-12 bg-slate-800 rounded-xl" />
                </div>
              ))}
            </div>
          ) : deals.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center my-8">
              <div className="w-12 h-12 mx-auto mb-3 text-slate-500">🌵</div>
              <h3 className="text-base font-bold text-slate-200 mb-1">No Arizona deals match the current filters</h3>
              <p className="text-xs text-slate-400 mb-4">Try clearing some filter criteria or keyword searches.</p>
              <button
                onClick={handleResetFilters}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs rounded-xl transition"
              >
                Reset All Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {deals.map((deal, idx) => (
                <DealCard
                  key={deal.id}
                  deal={deal}
                  rank={idx + 1}
                  onSelectForRoi={handleOpenRoiWithDeal}
                />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 space-y-3 sm:space-y-0">
          <div>
            © 2026 Arizona Deal Agent MVP. Scored against regional Arizona market indexes.
          </div>
          <div className="flex space-x-4">
            <span className="hover:text-slate-400 cursor-pointer">Scoring Algorithm</span>
            <span className="hover:text-slate-400 cursor-pointer">Regional Coverage</span>
            <span className="hover:text-slate-400 cursor-pointer">API Docs</span>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <RoiCalculatorModal
        isOpen={isCalculatorOpen}
        onClose={() => setIsCalculatorOpen(false)}
        selectedDeal={selectedDealForRoi}
        allDeals={deals}
      />

      <SubmitDealModal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        onDealSubmitted={() => {
          fetchDeals();
        }}
      />
    </div>
  );
}
