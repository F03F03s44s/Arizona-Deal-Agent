import { NextRequest, NextResponse } from 'next/server';
import { ARIZONA_DEALS, getFilteredAndRankedDeals, computeDealStats } from '@/lib/deals';
import { ArizonaDealAgentEngine } from '@/lib/agent-engine';
import { DealCategory, ArizonaRegion, ValueTier, DealFilterOptions } from '@/types/deal';

const agentEngine = new ArizonaDealAgentEngine();

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    const category = searchParams.get('category') as DealCategory | 'all' | null;
    const region = searchParams.get('region') as ArizonaRegion | 'all' | null;
    const search = searchParams.get('search') || undefined;
    const minPrice = searchParams.get('minPrice') ? Number(searchParams.get('minPrice')) : undefined;
    const maxPrice = searchParams.get('maxPrice') ? Number(searchParams.get('maxPrice')) : undefined;
    const minScore = searchParams.get('minScore') ? Number(searchParams.get('minScore')) : undefined;
    const valueTier = searchParams.get('valueTier') as ValueTier | 'all' | null;
    const sortBy = (searchParams.get('sortBy') as DealFilterOptions['sortBy']) || 'score';

    const filters: DealFilterOptions = {
      category: category || 'all',
      region: region || 'all',
      search,
      minPrice,
      maxPrice,
      minScore,
      valueTier: valueTier || 'all',
      sortBy,
    };

    const deals = getFilteredAndRankedDeals(ARIZONA_DEALS, filters);
    const stats = computeDealStats(ARIZONA_DEALS);

    return NextResponse.json({
      success: true,
      count: deals.length,
      deals,
      stats,
      filtersApplied: filters,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || 'Failed to fetch deals' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    if (!body.title || !body.price || !body.originalPrice || !body.category || !body.region) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields: title, price, originalPrice, category, region' },
        { status: 400 }
      );
    }

    const newDeal = agentEngine.analyzeAndIngestDeal({
      title: body.title,
      description: body.description || 'Verified Arizona deal evaluated by AI Agent.',
      category: body.category,
      source: body.source || 'Community Deal Submission',
      sourceUrl: body.sourceUrl,
      price: Number(body.price),
      originalPrice: Number(body.originalPrice),
      city: body.city || 'Phoenix',
      region: body.region,
      zipCode: body.zipCode,
      tags: body.tags || ['User Submitted', 'AZ Bargain'],
      conditionRating: body.conditionRating ? Number(body.conditionRating) : 4.8,
      estimatedResaleValue: body.estimatedResaleValue ? Number(body.estimatedResaleValue) : undefined,
      marketAveragePrice: body.marketAveragePrice ? Number(body.marketAveragePrice) : undefined,
      images: body.image ? [body.image] : undefined,
    });

    // In a live system this writes to DB; for our MVP in-memory store
    ARIZONA_DEALS.unshift(newDeal);

    return NextResponse.json({
      success: true,
      deal: newDeal,
      message: 'Deal analyzed and ranked successfully!',
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || 'Failed to ingest deal' },
      { status: 500 }
    );
  }
}
