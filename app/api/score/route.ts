import { NextRequest, NextResponse } from 'next/server';
import { calculateValueScore } from '@/lib/scoring';
import { DealCategory } from '@/types/deal';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const category = (body.category as DealCategory) || 'electronics-goods';
    const price = Number(body.price);
    const originalPrice = Number(body.originalPrice);
    const marketAveragePrice = body.marketAveragePrice ? Number(body.marketAveragePrice) : undefined;
    const conditionRating = body.conditionRating ? Number(body.conditionRating) : 4.5;
    const estimatedResaleValue = body.estimatedResaleValue ? Number(body.estimatedResaleValue) : undefined;
    const daysOnMarketOrExpiresInDays = body.daysOnMarketOrExpiresInDays ? Number(body.daysOnMarketOrExpiresInDays) : 5;
    const verified = body.verified !== undefined ? Boolean(body.verified) : true;

    if (isNaN(price) || isNaN(originalPrice) || price <= 0 || originalPrice <= 0) {
      return NextResponse.json(
        { success: false, error: 'Price and Original Price must be valid positive numbers' },
        { status: 400 }
      );
    }

    const score = calculateValueScore({
      category,
      price,
      originalPrice,
      marketAveragePrice,
      conditionRating,
      estimatedResaleValue,
      daysOnMarketOrExpiresInDays,
      verified,
    });

    return NextResponse.json({
      success: true,
      evaluation: score,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || 'Scoring evaluation failed' },
      { status: 500 }
    );
  }
}
