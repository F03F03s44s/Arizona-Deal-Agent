import { NextRequest, NextResponse } from 'next/server';
import { ArizonaDealAgentEngine } from '@/lib/agent-engine';

const engine = new ArizonaDealAgentEngine();

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('query') || 'deals';

    const liveDeals = engine.generateLiveMarketDeals(query);

    return NextResponse.json({
      success: true,
      query,
      found: liveDeals.length,
      deals: liveDeals,
      marketStatus: 'Active real-time agent crawler connected to AZ hubs (Scottsdale, Phoenix, Tucson, Sedona, Mesa)',
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || 'Crawler search failed' },
      { status: 500 }
    );
  }
}
