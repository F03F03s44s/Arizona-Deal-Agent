'use client';

import React, { useState } from 'react';
import { DealCategory, ArizonaRegion, ValueScoreBreakdown } from '@/types/deal';
import { X, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

interface SubmitDealModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDealSubmitted: () => void;
}

export const SubmitDealModal: React.FC<SubmitDealModalProps> = ({
  isOpen,
  onClose,
  onDealSubmitted,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<DealCategory>('real-estate');
  const [region, setRegion] = useState<ArizonaRegion>('Phoenix Metro');
  const [city, setCity] = useState('Phoenix');
  const [price, setPrice] = useState<string>('');
  const [originalPrice, setOriginalPrice] = useState<string>('');
  const [source, setSource] = useState('Private Arizona Listing');
  const [image, setImage] = useState('');
  const [loading, setLoading] = useState(false);
  const [evaluatedScore, setEvaluatedScore] = useState<ValueScoreBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleEvaluateOnly = async () => {
    if (!price || !originalPrice) {
      setError('Please provide both Deal Price and Original Market Price to evaluate score.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          price: Number(price),
          originalPrice: Number(originalPrice),
        }),
      });
      const data = await res.json();
      if (data.success) {
        setEvaluatedScore(data.evaluation);
      } else {
        setError(data.error || 'Evaluation failed');
      }
    } catch (e: any) {
      setError(e.message || 'Error scoring deal');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !price || !originalPrice) {
      setError('Please fill in Title, Deal Price, and Original Price.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/deals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description,
          category,
          region,
          city,
          price: Number(price),
          originalPrice: Number(originalPrice),
          source,
          image: image || undefined,
        }),
      });

      const data = await res.json();
      if (data.success) {
        onDealSubmitted();
        onClose();
      } else {
        setError(data.error || 'Submission failed');
      }
    } catch (e: any) {
      setError(e.message || 'Error submitting deal');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Evaluate & Ingest New AZ Deal</h2>
              <p className="text-xs text-slate-400">Score any Arizona opportunity against current state comps</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Deal Title *</label>
            <input
              type="text"
              required
              placeholder="e.g. 3-Bed Scottsdale Condo Wholesale, 2021 Ford Bronco Badlands..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as DealCategory)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              >
                <option value="real-estate">Real Estate</option>
                <option value="vehicles">Vehicles</option>
                <option value="travel-resorts">Travel & Resorts</option>
                <option value="experiences-dining">Experiences & Dining</option>
                <option value="electronics-goods">Electronics & Goods</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">AZ Region</label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value as ArizonaRegion)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              >
                <option value="Phoenix Metro">Phoenix Metro</option>
                <option value="Scottsdale & East Valley">Scottsdale & East Valley</option>
                <option value="Tucson & Southern AZ">Tucson & Southern AZ</option>
                <option value="Flagstaff & Northern AZ">Flagstaff & Northern AZ</option>
                <option value="Sedona & Verde Valley">Sedona & Verde Valley</option>
                <option value="Yuma & Western AZ">Yuma & Western AZ</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Offer / Deal Price ($) *</label>
              <input
                type="number"
                required
                placeholder="299000"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Original / Retail Price ($) *</label>
              <input
                type="number"
                required
                placeholder="395000"
                value={originalPrice}
                onChange={(e) => setOriginalPrice(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">City</label>
              <input
                type="text"
                placeholder="Scottsdale, Mesa, Tucson..."
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Listing Source</label>
              <input
                type="text"
                placeholder="e.g. Off-market wholesaler, MLS"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Description / Condition</label>
            <textarea
              rows={2}
              placeholder="Highlight key value drivers, terms, equity, condition..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Image URL (Optional)</label>
            <input
              type="url"
              placeholder="https://..."
              value={image}
              onChange={(e) => setImage(e.target.value)}
              className="w-full px-3.5 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-sm"
            />
          </div>

          {/* Quick AI Evaluation Box */}
          {evaluatedScore && (
            <div className="bg-slate-950/80 border border-amber-500/30 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400">Value Score Preview:</span>
                <span className="text-base font-extrabold text-white">
                  {evaluatedScore.compositeScore}/100 ({evaluatedScore.valueTier})
                </span>
              </div>
              <div className="text-xs text-slate-400">
                Savings: <span className="text-emerald-400 font-bold">${evaluatedScore.savingsDollars.toLocaleString()} ({evaluatedScore.savingsPercentage}%)</span>
              </div>
              <ul className="text-xs text-slate-400 space-y-1">
                {evaluatedScore.reasoning.map((r, i) => (
                  <li key={i}>• {r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Modal Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleEvaluateOnly}
              disabled={loading}
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-500/30 transition"
            >
              Run AI Score Test
            </button>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg transition"
              >
                {loading ? 'Processing...' : 'Ingest & Rank Deal'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
