import { Deal, DealCategory, ArizonaRegion } from '@/types/deal';
import { calculateValueScore } from './scoring';

export interface DealCrawlerJob {
  source: string;
  category: DealCategory;
  city: string;
  region: ArizonaRegion;
}

export class ArizonaDealAgentEngine {
  /**
   * Scrapes / analyzes raw deal submissions or third-party feeds
   * and normalizes them into enriched Arizona deals with value scores.
   */
  public analyzeAndIngestDeal(raw: {
    title: string;
    description: string;
    category: DealCategory;
    source: string;
    sourceUrl?: string;
    price: number;
    originalPrice: number;
    city: string;
    region: ArizonaRegion;
    zipCode?: string;
    lat?: number;
    lng?: number;
    address?: string;
    tags?: string[];
    features?: Record<string, string | number | boolean>;
    conditionRating?: number;
    marketAveragePrice?: number;
    estimatedResaleValue?: number;
    daysOnMarketOrExpiresInDays?: number;
    images?: string[];
    verified?: boolean;
  }): Deal {
    const valueScore = calculateValueScore({
      category: raw.category,
      price: raw.price,
      originalPrice: raw.originalPrice,
      marketAveragePrice: raw.marketAveragePrice,
      conditionRating: raw.conditionRating ?? 4.8,
      estimatedResaleValue: raw.estimatedResaleValue,
      daysOnMarketOrExpiresInDays: raw.daysOnMarketOrExpiresInDays ?? 5,
      verified: raw.verified ?? true,
    });

    const deal: Deal = {
      id: `az-custom-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      title: raw.title,
      description: raw.description,
      category: raw.category,
      source: raw.source,
      sourceUrl: raw.sourceUrl,
      price: raw.price,
      originalPrice: raw.originalPrice,
      currency: 'USD',
      location: {
        city: raw.city,
        region: raw.region,
        zipCode: raw.zipCode,
        lat: raw.lat,
        lng: raw.lng,
        address: raw.address,
      },
      images: raw.images && raw.images.length > 0 ? raw.images : [
        'https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=800&q=80'
      ],
      tags: raw.tags || ['Arizona Deal', 'Agent Verified'],
      features: raw.features || {},
      postedAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      verified: raw.verified ?? true,
      valueScore,
    };

    return deal;
  }

  /**
   * Run live simulated search across Arizona marketplaces
   */
  public generateLiveMarketDeals(keyword: string): Deal[] {
    const normalized = keyword.toLowerCase();
    const mockDeals: Deal[] = [];

    if (normalized.includes('golf') || normalized.includes('resort')) {
      mockDeals.push(
        this.analyzeAndIngestDeal({
          title: 'Troon North Golf Club Scottsdale - 4 Player Twilight Pass',
          description: 'Pinnacle & Monument courses package with cart and $50 clubhouse dining credit.',
          category: 'travel-resorts',
          source: 'Scottsdale Golf Deals',
          price: 240,
          originalPrice: 560,
          city: 'Scottsdale',
          region: 'Scottsdale & East Valley',
          conditionRating: 4.9,
          tags: ['Troon North', 'Championship Golf', 'Twilight Rate'],
          images: ['https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=800&q=80']
        })
      );
    }

    if (normalized.includes('truck') || normalized.includes('jeep') || normalized.includes('offroad')) {
      mockDeals.push(
        this.analyzeAndIngestDeal({
          title: '2022 Jeep Wrangler Rubicon 392 V8 (Sedona Trail Edition)',
          description: 'Arizona single owner 392 V8 HEMI Jeep with winch, 35-inch Nitto tires, Sky One-Touch power top.',
          category: 'vehicles',
          source: 'Phoenix 4x4 Liquidators',
          price: 58000,
          originalPrice: 79000,
          marketAveragePrice: 72000,
          city: 'Phoenix',
          region: 'Phoenix Metro',
          conditionRating: 4.8,
          tags: ['HEMI 392', 'Rubicon', 'Sedona Spec', 'Under Wholesale'],
          images: ['https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=800&q=80']
        })
      );
    }

    return mockDeals;
  }
}
