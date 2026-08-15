'use client';

import React, { useState } from 'react';
import { Deal, ValueTier } from '@/types/deal';
import {
  Sparkles,
  MapPin,
  TrendingUp,
  Clock,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Tag,
  BadgePercent,
  Layers,
} from 'lucide-react';

interface DealCardProps {
  deal: Deal;
  rank: number;
  onSelectForRoi?: (deal: Deal) => void;
}

export const DealCard: React.FC<DealCardProps> = ({ deal, rank, onSelectForRoi }) => {
  const [expanded, setExpanded] = useState(false);
  const { valueScore, location } = deal;

  const tierColors: Record<ValueTier, { bg: string; text: string; border: string }> = {
    Exceptional: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    Great: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' },
    Good: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30' },
    Fair: { bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/30' },
  };

  const currentTier = tierColors[valueScore.valueTier] || tierColors.Fair;

  return (
    <div className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl overflow-hidden transition-all duration-200 az-card-glow flex flex-col justify-between">
      <div>
        {/* Card Header image & Badges */}
        <div className="relative h-48 w-full bg-slate-950 overflow-hidden">
          <img
            src={deal.images[0] || 'https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=800&q=80'}
            alt={deal.title}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />

          {/* Rank Badge */}
          <div className="absolute top-3 left-3 flex items-center space-x-1.5 px-2.5 py-1 bg-slate-950/80 backdrop-blur-md rounded-lg border border-slate-700 text-xs font-bold text-white shadow">
            <span className="text-amber-400 font-extrabold">#{rank}</span>
            <span className="text-slate-400">RANK</span>
          </div>

          {/* Score Badge */}
          <div className="absolute top-3 right-3 flex items-center space-x-1.5 px-3 py-1 bg-slate-900/90 backdrop-blur-md rounded-xl border border-amber-500/40 shadow-lg">
            <Sparkles className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
            <span className="text-sm font-black text-amber-300">{valueScore.compositeScore}</span>
            <span className="text-[10px] uppercase font-bold text-slate-400">Value Score</span>
          </div>

          {/* Value Tier & Discount Pills bottom */}
          <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
            <div className={`px-2.5 py-0.5 rounded-md text-xs font-bold border ${currentTier.bg} ${currentTier.text} ${currentTier.border}`}>
              {valueScore.valueTier} Deal
            </div>
            <div className="px-2.5 py-0.5 rounded-md text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1">
              <BadgePercent className="w-3.5 h-3.5" />
              <span>{valueScore.savingsPercentage}% OFF</span>
            </div>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-5">
          {/* Location & Source */}
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <div className="flex items-center space-x-1 truncate max-w-[70%]">
              <MapPin className="w-3.5 h-3.5 text-teal-400 shrink-0" />
              <span className="truncate">{location.city}, {location.region}</span>
            </div>
            <span className="text-slate-500 font-medium truncate">{deal.source}</span>
          </div>

          {/* Title */}
          <h3 className="text-base font-bold text-slate-100 line-clamp-2 mb-2 group-hover:text-amber-400 transition">
            {deal.title}
          </h3>

          {/* Description */}
          <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">
            {deal.description}
          </p>

          {/* Pricing Row */}
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 mb-4 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Deal Price</div>
              <div className="text-lg font-black text-white">
                ${deal.price.toLocaleString()}
              </div>
            </div>

            <div className="text-right">
              <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">You Save</div>
              <div className="text-sm font-bold text-emerald-400">
                ${valueScore.savingsDollars.toLocaleString()}
              </div>
              <div className="text-[10px] text-slate-500 line-through">
                ${deal.originalPrice.toLocaleString()}
              </div>
            </div>
          </div>

          {/* AI Score Breakdown & Reasoning */}
          <div className="space-y-2 mb-3">
            <div className="text-xs font-semibold text-slate-300 flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Agent Value Insights:</span>
            </div>
            <ul className="text-xs text-slate-400 space-y-1 pl-1">
              {valueScore.reasoning.map((r, i) => (
                <li key={i} className="flex items-start space-x-2">
                  <span className="text-amber-500 font-bold">•</span>
                  <span className="leading-tight">{r}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Expandable Details Drawer */}
          {expanded && (
            <div className="pt-3 mt-3 border-t border-slate-800 space-y-3 animate-fadeIn">
              {/* Detailed Scores Matrix */}
              <div className="grid grid-cols-3 gap-2 text-center bg-slate-950/40 p-2.5 rounded-xl border border-slate-800/60">
                <div>
                  <div className="text-[10px] text-slate-500">Discount</div>
                  <div className="text-xs font-bold text-slate-200">{valueScore.discountScore}/100</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">ROI Upside</div>
                  <div className="text-xs font-bold text-emerald-400">{valueScore.roiScore}/100</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Historical</div>
                  <div className="text-xs font-bold text-teal-400">{valueScore.historicalScore}/100</div>
                </div>
              </div>

              {/* Specific features / tags */}
              {deal.features && Object.keys(deal.features).length > 0 && (
                <div className="bg-slate-950/30 p-2.5 rounded-xl text-xs space-y-1">
                  <span className="font-semibold text-slate-300 text-[11px] uppercase tracking-wider block mb-1">
                    Property / Asset Features
                  </span>
                  <div className="grid grid-cols-2 gap-1 text-slate-400">
                    {Object.entries(deal.features).map(([k, v]) => (
                      <div key={k} className="truncate">
                        <span className="capitalize text-slate-500">{k}:</span> {String(v)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tags */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {deal.tags.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.5 text-[10px] font-medium bg-slate-800 text-slate-300 rounded-md border border-slate-700"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Card Footer Actions */}
      <div className="px-5 pb-5 pt-2 border-t border-slate-800/60 flex items-center justify-between gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-semibold text-slate-400 hover:text-slate-200 flex items-center space-x-1 py-1.5 px-2 rounded-lg hover:bg-slate-800 transition"
        >
          <span>{expanded ? 'Less Info' : 'Full Value Analysis'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        <div className="flex items-center space-x-2">
          {onSelectForRoi && (
            <button
              onClick={() => onSelectForRoi(deal)}
              title="Calculate potential profit and resale yield"
              className="p-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-teal-400 border border-slate-700 transition"
            >
              <TrendingUp className="w-4 h-4" />
            </button>
          )}

          <a
            href={deal.sourceUrl || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold transition"
          >
            <span>View Deal</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
};
