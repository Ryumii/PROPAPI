"""Tests for risk scoring service."""

from app.services.scoring import (
    ScoringResult,
    calculate_scores,
    score_flood,
    score_landslide,
    score_liquefaction,
    score_tsunami,
)
from app.services.spatial import (
    FloodResult,
    LandslideResult,
    LiquefactionResult,
    SpatialQueryResult,
    TsunamiResult,
)


class TestScoreFlood:
    def test_none_returns_zero(self) -> None:
        assert score_flood(None) == 0

    def test_depth_rank_mapped(self) -> None:
        assert score_flood(FloodResult(depth_rank=3, depth_range="1.0m〜3.0m")) == 3

    def test_clamped_high(self) -> None:
        assert score_flood(FloodResult(depth_rank=7, depth_range="")) == 5

    def test_clamped_low(self) -> None:
        assert score_flood(FloodResult(depth_rank=-1, depth_range="")) == 0


class TestScoreLandslide:
    def test_none_returns_zero(self) -> None:
        assert score_landslide(None) == 0

    def test_special_warning_zone(self) -> None:
        assert score_landslide(LandslideResult(zone_type="特別警戒区域")) == 5

    def test_warning_zone(self) -> None:
        assert score_landslide(LandslideResult(zone_type="警戒区域")) == 4

    def test_unknown_zone(self) -> None:
        assert score_landslide(LandslideResult(zone_type="その他")) == 3


class TestScoreTsunami:
    def test_none_returns_zero(self) -> None:
        assert score_tsunami(None) == 0

    def test_depth_5m_plus(self) -> None:
        assert score_tsunami(TsunamiResult(depth_m=6.0)) == 5

    def test_depth_3m(self) -> None:
        assert score_tsunami(TsunamiResult(depth_m=3.5)) == 4

    def test_depth_1m(self) -> None:
        assert score_tsunami(TsunamiResult(depth_m=1.5)) == 3

    def test_depth_03m(self) -> None:
        assert score_tsunami(TsunamiResult(depth_m=0.4)) == 2

    def test_depth_low(self) -> None:
        assert score_tsunami(TsunamiResult(depth_m=0.1)) == 1

    def test_depth_unknown(self) -> None:
        assert score_tsunami(TsunamiResult(depth_m=None)) == 2


class TestScoreLiquefaction:
    def test_none_returns_zero(self) -> None:
        assert score_liquefaction(None) == 0

    def test_risk_rank_used_when_present(self) -> None:
        assert score_liquefaction(LiquefactionResult(risk_rank=4, pl_value=1.0)) == 4

    def test_pl_high(self) -> None:
        assert score_liquefaction(LiquefactionResult(pl_value=20.0)) == 5

    def test_pl_medium(self) -> None:
        assert score_liquefaction(LiquefactionResult(pl_value=12.5)) == 4

    def test_pl_low(self) -> None:
        assert score_liquefaction(LiquefactionResult(pl_value=3.0)) == 2

    def test_pl_unknown(self) -> None:
        assert score_liquefaction(LiquefactionResult(pl_value=None)) == 2


class TestCalculateScores:
    def test_all_none_returns_zero(self) -> None:
        r = calculate_scores(SpatialQueryResult())
        assert r.composite_score == 0
        assert r.composite_level == "none"

    def test_mixed_scores(self) -> None:
        spatial = SpatialQueryResult(
            flood=FloodResult(depth_rank=2, depth_range="0.5m〜1.0m"),
            landslide=None,
            tsunami=None,
            liquefaction=LiquefactionResult(pl_value=12.5),
        )
        r = calculate_scores(spatial)
        # flood=2*0.30=0.6, landslide=0*0.25=0, tsunami=0*0.20=0, liquefaction=4*0.25=1.0
        assert r.flood_score == 2
        assert r.liquefaction_score == 4
        assert r.composite_score == 1.6
        assert r.composite_level == "low"

    def test_high_risk(self) -> None:
        spatial = SpatialQueryResult(
            flood=FloodResult(depth_rank=5, depth_range="5.0m〜"),
            landslide=LandslideResult(zone_type="特別警戒区域"),
            tsunami=TsunamiResult(depth_m=6.0),
            liquefaction=LiquefactionResult(risk_rank=5),
        )
        r = calculate_scores(spatial)
        assert r.composite_score == 5.0
        assert r.composite_level == "very_high"
        assert "非常に高い" in r.composite_description

    def test_result_is_dataclass(self) -> None:
        r = calculate_scores(SpatialQueryResult())
        assert isinstance(r, ScoringResult)
