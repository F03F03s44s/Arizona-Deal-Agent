'use client';

import React from 'react';
import { DealStats } from '@/types/deal';
import { DollarSign, Percent, Flame, MapPin } from 'lucide-react';

interface StatsBarProps {
  stats: DealStats;
}

export const StatsBar: React.FC<StatsBarProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 my-6">
      {/* Total Potential Savings */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
        <div className="p-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg">
          <DollarSign className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Total AZ Savings</div>
          <div className="text-lg md:text-xl font-bold text-slate-100">
            ${stats.totalPotentialSavings.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Average Discount % */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
        <div className="p-3 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-lg">
          <Percent className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Avg Value Discount</div>
          <div className="text-lg md:text-xl font-bold text-amber-400">
            {stats.averageDiscountPct}% Below Mkt
          </div>
        </div>
      </div>

      {/* Top Hot Category */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
        <div className="p-3 bg-orange-500/10 text-orange-400 border border-orange-500/20 rounded-lg">
          <Flame className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Hot Category</div>
          <div className="text-sm md:text-base font-bold text-slate-100 capitalize">
            {stats.topCategory.replace('-', ' ')}
          </div>
        </div>
      </div>

      {/* Top Hot Region */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center space-x-3">
        <div className="p-3 bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded-lg">
          <MapPin className="w-5 h-5" />
        </div>
        <div>
          <div className="text-xs text-slate-400 font-medium">Top Deal Hub</div>
          <div className="text-sm md:text-base font-bold text-slate-100 truncate">
            {stats.topRegion}
          </div>
        </div>
      </div>
    </div>
  );
};
