'use client';

import React, { useState, useEffect } from 'react';
import { Deal } from '@/types/deal';
import { X, TrendingUp, Calculator, DollarSign, Percent, ArrowRight } from 'lucide-react';

interface RoiCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedDeal?: Deal | null;
  allDeals: Deal[];
}

export const RoiCalculatorModal: React.FC<RoiCalculatorModalProps> = ({
  isOpen,
  onClose,
  selectedDeal,
  allDeals,
}) => {
  const [dealId, setDealId] = useState<string>(selectedDeal?.id || (allDeals[0]?.id ?? ''));
  const [purchasePrice, setPurchasePrice] = useState<number>(selectedDeal?.price || 50000);
  const [resaleEstimate, setResaleEstimate] = useState<number>(selectedDeal?.valueScore.estimatedResaleValue || 65000);
  const [holdingCosts, setHoldingCosts] = useState<number>(1200);
  const [salesFeePct, setSalesFeePct] = useState<number>(6);

  useEffect(() => {
    if (selectedDeal) {
      setDealId(selectedDeal.id);
      setPurchasePrice(selectedDeal.price);
      setResaleEstimate(selectedDeal.valueScore.estimatedResaleValue || selectedDeal.originalPrice);
      // Sensible holding costs depending on category
      if (selectedDeal.category === 'real-estate') {
        setHoldingCosts(8500);
        setSalesFeePct(5);
      } else if (selectedDeal.category === 'vehicles') {
        setHoldingCosts(800);
        setSalesFeePct(3);
      } else {
        setHoldingCosts(150);
        setSalesFeePct(5);
      }
    }
  }, [selectedDeal]);

  if (!isOpen) return null;

  const activeDeal = allDeals.find((d) => d.id === dealId) || selectedDeal;

  const handleSelectDeal = (id: string) => {
    setDealId(id);
    const found = allDeals.find((d) => d.id === id);
    if (found) {
      setPurchasePrice(found.price);
      setResaleEstimate(found.valueScore.estimatedResaleValue || found.originalPrice);
      if (found.category === 'real-estate') {
        setHoldingCosts(8500);
        setSalesFeePct(5);
      } else if (found.category === 'vehicles') {
        setHoldingCosts(800);
        setSalesFeePct(3);
      } else {
        setHoldingCosts(150);
        setSalesFeePct(5);
      }
    }
  };

  const estimatedSalesFees = (resaleEstimate * salesFeePct) / 100;
  const netProceeds = resaleEstimate - estimatedSalesFees;
  const netProfit = netProceeds - purchasePrice - holdingCosts;
  const roiPercentage = purchasePrice > 0 ? (netProfit / (purchasePrice + holdingCosts)) * 100 : 0;
  const annualYield = (roiPercentage * 1.5).toFixed(1); // illustrative annualization

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded-lg">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Arizona Deal ROI & Resale Simulator</h2>
              <p className="text-xs text-slate-400">Calculate net profit, upside yield, and resale margins</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          {/* Deal Picker */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Select Deal or Load Custom
            </label>
            <select
              value={dealId}
              onChange={(e) => handleSelectDeal(e.target.value)}
              className="w-full py-2.5 px-3 bg-slate-800 border border-slate-700 rounded-xl text-slate-200 text-sm focus:ring-2 focus:ring-amber-500"
            >
              {allDeals.map((d) => (
                <option key={d.id} value={d.id}>
                  [{d.valueScore.compositeScore} PTS] {d.title} (${d.price.toLocaleString()})
                </option>
              ))}
            </select>
          </div>

          {/* Input Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Purchase / Deal Price ($)
              </label>
              <input
                type="number"
                value={purchasePrice}
                onChange={(e) => setPurchasePrice(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Estimated Target Resale / Fair Value ($)
              </label>
              <input
                type="number"
                value={resaleEstimate}
                onChange={(e) => setResaleEstimate(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Holding / Rehab / Transport Costs ($)
              </label>
              <input
                type="number"
                value={holdingCosts}
                onChange={(e) => setHoldingCosts(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Estimated Selling / Closing Fees (%)
              </label>
              <input
                type="number"
                value={salesFeePct}
                onChange={(e) => setSalesFeePct(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>
          </div>

          {/* Results Display Card */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span>Projected ROI & Value Breakdown</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-center">
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">Total Investment</div>
                <div className="text-base font-bold text-slate-200">
                  ${(purchasePrice + holdingCosts).toLocaleString()}
                </div>
              </div>

              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                <div className="text-[11px] text-slate-400">Estimated Net Profit</div>
                <div className={`text-base font-bold ${netProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  ${Math.round(netProfit).toLocaleString()}
                </div>
              </div>

              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 col-span-2 sm:col-span-1">
                <div className="text-[11px] text-slate-400">Expected ROI %</div>
                <div className={`text-base font-extrabold ${roiPercentage >= 0 ? 'text-amber-400' : 'text-rose-400'}`}>
                  {roiPercentage.toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-400 bg-slate-900/50 p-3 rounded-xl border border-slate-800/60 leading-relaxed">
              💡 <span className="font-semibold text-slate-300">Agent Recommendation: </span>
              {roiPercentage > 25
                ? 'High-confidence flip/resale candidate. Favorable price cushion against Arizona market dips.'
                : roiPercentage > 10
                ? 'Moderate-yield opportunity with steady local Arizona buyer demand.'
                : 'Lower margin on immediate resale; primarily recommended for personal use / owner-occupant savings.'}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-slate-900/90 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 text-sm font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-white transition"
          >
            Close Calculator
          </button>
        </div>
      </div>
    </div>
  );
};
