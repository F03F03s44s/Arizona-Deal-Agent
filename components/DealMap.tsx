'use client';

import React, { useState } from 'react';
import { Deal, ArizonaRegion } from '@/types/deal';
import { MapPin, Sparkles, Navigation } from 'lucide-react';

interface DealMapProps {
  deals: Deal[];
  selectedRegion?: ArizonaRegion | 'all';
  onSelectDeal?: (deal: Deal) => void;
  onFilterRegion?: (region: ArizonaRegion) => void;
}

interface RegionNode {
  region: ArizonaRegion;
  displayName: string;
  count: number;
  avgScore: number;
  highlightDeal?: Deal;
  topCity: string;
}

export const DealMap: React.FC<DealMapProps> = ({
  deals,
  selectedRegion,
  onSelectDeal,
  onFilterRegion,
}) => {
  // Aggregate data per region
  const regionStats: Record<string, { count: number; totalScore: number; topDeal?: Deal; topCity: string }> = {
    'Phoenix Metro': { count: 0, totalScore: 0, topCity: 'Phoenix' },
    'Scottsdale & East Valley': { count: 0, totalScore: 0, topCity: 'Scottsdale' },
    'Tucson & Southern AZ': { count: 0, totalScore: 0, topCity: 'Tucson' },
    'Flagstaff & Northern AZ': { count: 0, totalScore: 0, topCity: 'Flagstaff' },
    'Sedona & Verde Valley': { count: 0, totalScore: 0, topCity: 'Sedona' },
    'Yuma & Western AZ': { count: 0, totalScore: 0, topCity: 'Yuma' },
  };

  deals.forEach((d) => {
    if (regionStats[d.location.region]) {
      regionStats[d.location.region].count += 1;
      regionStats[d.location.region].totalScore += d.valueScore.compositeScore;
      if (
        !regionStats[d.location.region].topDeal ||
        d.valueScore.compositeScore > regionStats[d.location.region].topDeal!.valueScore.compositeScore
      ) {
        regionStats[d.location.region].topDeal = d;
      }
    }
  });

  const regionsList: RegionNode[] = Object.entries(regionStats).map(([reg, data]) => ({
    region: reg as ArizonaRegion,
    displayName: reg,
    count: data.count,
    avgScore: data.count > 0 ? Math.round(data.totalScore / data.count) : 0,
    highlightDeal: data.topDeal,
    topCity: data.topCity,
  }));

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Navigation className="w-5 h-5 text-amber-500" />
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Arizona Regional Value Radar
          </h3>
        </div>
        <span className="text-xs text-slate-400">Click region to filter ranked deals</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {regionsList.map((item) => {
          const isSelected = selectedRegion === item.region;
          return (
            <div
              key={item.region}
              onClick={() => onFilterRegion && onFilterRegion(item.region)}
              className={`cursor-pointer rounded-xl p-4 transition-all duration-200 border ${
                isSelected
                  ? 'bg-amber-500/10 border-amber-500 shadow-md shadow-amber-500/10'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-1.5 font-bold text-sm text-slate-100">
                  <MapPin className="w-4 h-4 text-teal-400" />
                  <span>{item.displayName}</span>
                </div>
                <span className="px-2 py-0.5 text-xs font-bold bg-slate-800 text-slate-300 rounded-md border border-slate-700">
                  {item.count} deals
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Avg Regional Score:</span>
                <span className="font-bold text-amber-400">
                  {item.avgScore > 0 ? `${item.avgScore} / 100` : 'Scanning...'}
                </span>
              </div>

              {item.highlightDeal && (
                <div className="mt-2.5 pt-2.5 border-t border-slate-800/80">
                  <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    Top Deal ({item.highlightDeal.valueScore.compositeScore} PTS)
                  </div>
                  <div className="text-xs font-medium text-slate-200 truncate hover:text-amber-300">
                    {item.highlightDeal.title}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
