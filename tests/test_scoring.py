from datetime import date

from deal_agent.models import Listing
from deal_agent.scoring import (
    rank_deals,
    score_listing,
    score_motivation,
    score_risk,
    score_value,
    score_yield,
)

TODAY = date(2026, 8, 15)


def make_listing(**overrides) -> Listing:
    base = dict(
        id="T-1",
        address="1 Test St",
        city="Phoenix",
        price=400_000,
        beds=3,
        baths=2.0,
        sqft=1600,
        year_built=2005,
        days_on_market=20,
    )
    base.update(overrides)
    return Listing(**base)


class TestComponents:
    def test_value_score_anchors(self):
        assert score_value(0.0) == 50.0
        assert score_value(0.20) == 100.0  # 20% below market maxes out
        assert score_value(-0.20) == 0.0
        assert score_value(None) == 50.0

    def test_yield_score_anchors(self):
        assert score_yield(0.03) == 0.0
        assert score_yield(0.09) == 100.0
        assert score_yield(0.06) == 50.0
        assert score_yield(None) == 50.0

    def test_motivation_increases_with_dom_and_cuts(self):
        fresh = score_motivation(0, None)
        stale = score_motivation(90, None)
        stale_cut = score_motivation(90, 0.05)
        assert fresh < stale < stale_cut
        assert score_motivation(500, 0.5) == 100.0  # capped

    def test_risk_prefers_newer_and_no_hoa(self):
        new = score_risk(2022, None, today=TODAY)
        old = score_risk(1965, None, today=TODAY)
        assert new > old
        assert score_risk(2022, 400, today=TODAY) < new

    def test_all_components_stay_in_bounds(self):
        for fn, args in [
            (score_value, (5.0,)),
            (score_value, (-5.0,)),
            (score_yield, (1.0,)),
            (score_motivation, (10_000, 1.0)),
            (score_risk, (1900, 10_000)),
        ]:
            result = fn(*args, today=TODAY) if fn is score_risk else fn(*args)
            assert 0.0 <= result <= 100.0


class TestScoreListing:
    def test_below_market_beats_identical_at_market(self):
        # Phoenix median is $282/sqft; same house, one priced 20% under the other.
        cheap = score_listing(make_listing(price=282 * 1600 * 0.8), today=TODAY)
        fair = score_listing(make_listing(price=282 * 1600), today=TODAY)
        assert cheap.deal_score > fair.deal_score
        assert cheap.discount_vs_market > 0.19

    def test_missing_sqft_is_neutral_low_confidence(self):
        deal = score_listing(make_listing(sqft=None), today=TODAY)
        assert deal.breakdown.value == 50.0
        assert deal.breakdown.yield_ == 50.0
        assert deal.price_per_sqft is None
        assert deal.est_monthly_rent is None
        assert deal.confidence == "medium"  # only sqft missing

    def test_confidence_drops_with_more_missing_fields(self):
        deal = score_listing(make_listing(sqft=None, year_built=None), today=TODAY)
        assert deal.confidence == "low"

    def test_price_cut_recorded(self):
        deal = score_listing(make_listing(original_price=440_000), today=TODAY)
        assert 0.089 < deal.price_cut_pct < 0.092
        assert any("cut" in r.lower() for r in deal.reasons)

    def test_unknown_city_uses_state_fallback(self):
        deal = score_listing(make_listing(city="Nowhereville"), today=TODAY)
        assert deal.market_median_ppsf == 265.0

    def test_reasons_mention_market_position(self):
        deal = score_listing(make_listing(price=282 * 1600 * 0.85), today=TODAY)
        assert any("below Phoenix median" in r for r in deal.reasons)


class TestRanking:
    def test_sorted_best_first_and_stable(self):
        listings = [
            make_listing(id="over", price=282 * 1600 * 1.25),
            make_listing(id="under", price=282 * 1600 * 0.78),
            make_listing(id="fair", price=282 * 1600),
        ]
        ranked = rank_deals(listings, today=TODAY)
        assert [d.listing.id for d in ranked] == ["under", "fair", "over"]
        scores = [d.deal_score for d in ranked]
        assert scores == sorted(scores, reverse=True)
