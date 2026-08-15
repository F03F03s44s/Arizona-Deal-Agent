'use client';

import React from 'react';
import { Compass, Sparkles, TrendingUp, ShieldCheck } from 'lucide-react';

interface NavbarProps {
  onOpenSubmitModal: () => void;
  onOpenCalculator: () => void;
  dealCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenSubmitModal,
  onOpenCalculator,
  dealCount,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-slate-900/80 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 via-orange-600 to-amber-700 flex items-center justify-center shadow-lg shadow-orange-500/20">
            <Compass className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-black tracking-tight text-white">AZ Deal<span className="text-amber-500">Agent</span></span>
              <span className="px-2 py-0.5 text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full">
                MVP
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium hidden sm:block">
              Lowest most profitable & highest value Arizona deals
            </p>
          </div>
        </div>

        {/* Live Status badge & Actions */}
        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-400 text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>{dealCount} Live AZ Deals Tracked</span>
          </div>

          <button
            onClick={onOpenCalculator}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            <TrendingUp className="w-4 h-4 text-teal-400" />
            <span>ROI Calculator</span>
          </button>

          <button
            onClick={onOpenSubmitModal}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 text-xs sm:text-sm font-semibold rounded-lg bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-md shadow-orange-600/20 transition active:scale-95"
          >
            <Sparkles className="w-4 h-4" />
            <span>Evaluate Deal</span>
          </button>
        </div>
      </div>
    </header>
  );
};
