"""Risk score calculation service.

Converts raw spatial query results into 0-5 risk scores per hazard type,
then computes a weighted composite score.

Score scale:
  0 = none, 1 = very_low, 2 = low, 3 = medium, 4 = high, 5 = very_high

Weights are configurable via RISK_WEIGHTS.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.spatial import (
    FloodResult,
    LandslideResult,
    LiquefactionResult,
    SpatialQueryResult,
    TsunamiResult,
)

# ---------- configurable weights ----------------------------------------
# Can be overridden via settings / config file in the future.

RISK_WEIGHTS: dict[str, float] = {
    "flood": 0.30,
    "landslide": 0.25,
    "tsunami": 0.20,
    "liquefaction": 0.25,
}

LEVEL_LABELS: dict[int, str] = {
    0: "none",
    1: "very_low",
    2: "low",
    3: "medium",
    4: "high",
    5: "very_high",
}

COMPOSITE_DESCRIPTIONS: dict[str, str] = {
    "none": "リスクは検出されていません",
    "very_low": "総合的なリスクは非常に低いです",
    "low": "総合的なリスクは低めです",
    "medium": "総合的なリスクは中程度です",
    "high": "総合的なリスクは高めです",
    "very_high": "総合的なリスクは非常に高いです",
}


# ---------- per-hazard scoring ------------------------------------------


def score_flood(result: FloodResult | None) -> int:
    """Map depth_rank (0-5) directly to risk score."""
    if result is None:
        return 0
    return max(0, min(5, result.depth_rank))


def score_landslide(result: LandslideResult | None) -> int:
    if result is None:
        return 0
    if result.zone_type == "特別警戒区域":
        return 5
    if result.zone_type == "警戒区域":
        return 4
    return 3  # inside some zone


def score_tsunami(result: TsunamiResult | None) -> int:
    if result is None:
        return 0
    depth = result.depth_m
    if depth is None:
        return 2  # zone exists but depth unknown
    if depth >= 5.0:
        return 5
    if depth >= 3.0:
        return 4
    if depth >= 1.0:
        return 3
    if depth >= 0.3:
        return 2
    return 1


def score_liquefaction(result: LiquefactionResult | None) -> int:
    if result is None:
        return 0
    # Prefer risk_rank if already classified
    if result.risk_rank is not None:
        return max(0, min(5, result.risk_rank))
    # Otherwise derive from PL value
    pl = result.pl_value
    if pl is None:
        return 2  # zone exists but value unknown
    if pl >= 15:
        return 5
    if pl >= 10:
        return 4
    if pl >= 5:
        return 3
    if pl >= 2:
        return 2
    return 1


def _level_for_score(score: int) -> str:
    return LEVEL_LABELS.get(score, "none")


# ---------- composite scoring -------------------------------------------


@dataclass
class ScoringResult:
    flood_score: int
    landslide_score: int
    tsunami_score: int
    liquefaction_score: int
    composite_score: float
    composite_level: str
    composite_description: str


def calculate_scores(spatial: SpatialQueryResult) -> ScoringResult:
    """Derive per-hazard scores and weighted composite from spatial query results."""
    fs = score_flood(spatial.flood)
    ls = score_landslide(spatial.landslide)
    ts = score_tsunami(spatial.tsunami)
    lq = score_liquefaction(spatial.liquefaction)

    weighted = (
        fs * RISK_WEIGHTS["flood"]
        + ls * RISK_WEIGHTS["landslide"]
        + ts * RISK_WEIGHTS["tsunami"]
        + lq * RISK_WEIGHTS["liquefaction"]
    )
    composite = round(weighted, 1)

    # Map composite to level bucket
    if composite == 0:
        level = "none"
    elif composite <= 1:
        level = "very_low"
    elif composite <= 2:
        level = "low"
    elif composite <= 3:
        level = "medium"
    elif composite <= 4:
        level = "high"
    else:
        level = "very_high"

    return ScoringResult(
        flood_score=fs,
        landslide_score=ls,
        tsunami_score=ts,
        liquefaction_score=lq,
        composite_score=composite,
        composite_level=level,
        composite_description=COMPOSITE_DESCRIPTIONS[level],
    )
