'use client';

import React from 'react';
import { DealCategory, ArizonaRegion, ValueTier, DealFilterOptions } from '@/types/deal';
import { Search, SlidersHorizontal, MapPin, Tag, Award, ArrowDownUp } from 'lucide-react';

interface FilterBarProps {
  filters: DealFilterOptions;
  onChangeFilters: (newFilters: Partial<DealFilterOptions>) => void;
  onResetFilters: () => void;
}

const CATEGORIES: { label: string; value: DealCategory | 'all' }[] = [
  { label: 'All Categories', value: 'all' },
  { label: '🏡 Real Estate', value: 'real-estate' },
  { label: '🚗 Vehicles & 4x4', value: 'vehicles' },
  { label: '🏜️ Resorts & Travel', value: 'travel-resorts' },
  { label: '🍽️ Dining & Experiences', value: 'experiences-dining' },
  { label: '⚡ Tech & Surplus', value: 'electronics-goods' },
];

const REGIONS: { label: string; value: ArizonaRegion | 'all' }[] = [
  { label: 'All Arizona Regions', value: 'all' },
  { label: 'Phoenix Metro', value: 'Phoenix Metro' },
  { label: 'Scottsdale & East Valley', value: 'Scottsdale & East Valley' },
  { label: 'Tucson & Southern AZ', value: 'Tucson & Southern AZ' },
  { label: 'Flagstaff & Northern AZ', value: 'Flagstaff & Northern AZ' },
  { label: 'Sedona & Verde Valley', value: 'Sedona & Verde Valley' },
  { label: 'Yuma & Western AZ', value: 'Yuma & Western AZ' },
];

const VALUE_TIERS: { label: string; value: ValueTier | 'all' }[] = [
  { label: 'All Tiers', value: 'all' },
  { label: '🔥 Exceptional (85-100)', value: 'Exceptional' },
  { label: '✨ Great (75-84)', value: 'Great' },
  { label: '👍 Good (60-74)', value: 'Good' },
];

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChangeFilters,
  onResetFilters,
}) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 md:p-5 mb-8 shadow-xl">
      {/* Search Bar & Primary Sort */}
      <div className="flex flex-col md:flex-row gap-3 items-center mb-4">
        <div className="relative flex-1 w-full">
          <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search Arizona deals by keyword (e.g., Scottsdale, Tesla, Foreclosure, Sedona)..."
            value={filters.search || ''}
            onChange={(e) => onChangeFilters({ search: e.target.value })}
            className="w-full pl-11 pr-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition"
          />
        </div>

        {/* Sort selector */}
        <div className="flex items-center space-x-2 w-full md:w-auto">
          <ArrowDownUp className="w-4 h-4 text-amber-500 shrink-0" />
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider shrink-0">Sort:</span>
          <select
            value={filters.sortBy || 'score'}
            onChange={(e) => onChangeFilters({ sortBy: e.target.value as any })}
            className="w-full md:w-48 py-2.5 px-3 bg-slate-800 border border-slate-700 rounded-xl text-slate-100 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="score">🏆 Best Value Score</option>
            <option value="savings_desc">💰 Biggest $ Savings</option>
            <option value="savings_pct">📉 Highest % Off</option>
            <option value="price_asc">💵 Lowest Price First</option>
            <option value="price_desc">💎 Highest Price First</option>
            <option value="newest">⏱️ Newly Added</option>
          </select>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none mb-4">
        {CATEGORIES.map((cat) => {
          const isActive = (filters.category || 'all') === cat.value;
          return (
            <button
              key={cat.value}
              onClick={() => onChangeFilters({ category: cat.value })}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                isActive
                  ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20 font-bold'
                  : 'bg-slate-800/70 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
              }`}
            >
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Secondary dropdown filters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-slate-800/80">
        {/* Region */}
        <div className="flex items-center space-x-2 bg-slate-800/50 px-3 py-2 rounded-xl border border-slate-700/50">
          <MapPin className="w-4 h-4 text-teal-400 shrink-0" />
          <select
            value={filters.region || 'all'}
            onChange={(e) => onChangeFilters({ region: e.target.value as any })}
            className="bg-transparent text-slate-200 text-xs sm:text-sm w-full focus:outline-none"
          >
            {REGIONS.map((r) => (
              <option key={r.value} value={r.value} className="bg-slate-900 text-slate-200">
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {/* Value Tier */}
        <div className="flex items-center space-x-2 bg-slate-800/50 px-3 py-2 rounded-xl border border-slate-700/50">
          <Award className="w-4 h-4 text-orange-400 shrink-0" />
          <select
            value={filters.valueTier || 'all'}
            onChange={(e) => onChangeFilters({ valueTier: e.target.value as any })}
            className="bg-transparent text-slate-200 text-xs sm:text-sm w-full focus:outline-none"
          >
            {VALUE_TIERS.map((t) => (
              <option key={t.value} value={t.value} className="bg-slate-900 text-slate-200">
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* Reset Filters */}
        <div className="flex items-center justify-end">
          <button
            onClick={onResetFilters}
            className="text-xs text-slate-400 hover:text-amber-400 font-medium underline underline-offset-4 transition"
          >
            Reset All Filters
          </button>
        </div>
      </div>
    </div>
  );
};
