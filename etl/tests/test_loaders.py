"""Tests for ETL loader transform functions (pure logic, no DB)."""

from __future__ import annotations

import json

import pytest
from shapely.geometry import Polygon, mapping

from etl.scripts.load_flood import transform_feature as flood_transform
from etl.scripts.load_landslide import transform_feature as landslide_transform
from etl.scripts.load_tsunami import transform_feature as tsunami_transform
from etl.scripts.load_zoning import transform_feature as zoning_transform


def _make_geojson() -> str:
    """Generate a dummy polygon GeoJSON string."""
    poly = Polygon([(139.7, 35.6), (139.8, 35.6), (139.8, 35.7), (139.7, 35.7)])
    return json.dumps(mapping(poly))


GEOM = _make_geojson()


# ── Flood transform ──────────────────────────────────────────


class TestFloodTransform:
    def test_basic(self):
        props = {"A31_001": "3", "A31_002": "3m以上5m未満", "A31_004": "荒川"}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 3
        assert row["depth_range"] == "3m以上5m未満"
        assert row["river_name"] == "荒川"
        assert row["prefecture"] == "東京都"

    def test_depth_rank_clamped(self):
        props = {"A31_001": "99"}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 5  # clamped to max

    def test_depth_rank_default_zero(self):
        props = {}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 0

    def test_depth_range_auto_from_rank(self):
        props = {"A31_001": "2"}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_range"] == "0.5m以上3m未満"

    def test_japanese_attr_names(self):
        props = {"浸水深ランク": 4, "浸水深": "5m以上10m未満", "河川名": "隅田川"}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 4
        assert row["river_name"] == "隅田川"


# ── Landslide transform ─────────────────────────────────────


class TestLandslideTransform:
    def test_warning_zone_code(self):
        props = {"A33_001": "1"}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["zone_type"] == "警戒区域"

    def test_special_warning_zone_code(self):
        props = {"A33_001": "2"}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["zone_type"] == "特別警戒区域"

    def test_japanese_name_passthrough(self):
        props = {"区域区分": "特別警戒区域"}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["zone_type"] == "特別警戒区域"

    def test_missing_zone_type_skipped(self):
        props = {}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is None


# ── Tsunami transform ───────────────────────────────────────


class TestTsunamiTransform:
    def test_with_depth(self):
        props = {"A40_001": "3.5"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(3.5)

    def test_missing_depth(self):
        props = {}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] is None

    def test_japanese_attr(self):
        props = {"浸水深": "1.2"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(1.2)


# ── Zoning transform ────────────────────────────────────────


class TestZoningTransform:
    def test_basic(self):
        props = {
            "L03b_001": "05",
            "L03b_003": "60",
            "L03b_004": "200",
            "L03b_005": "01",
        }
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["use_code"] == "05"
        assert row["use_district"] == "第一種住居地域"
        assert row["coverage_pct"] == 60
        assert row["floor_ratio_pct"] == 200
        assert row["fire_prevention"] == "防火地域"
        assert row["fire_code"] == "01"

    def test_missing_use_code_skipped(self):
        props = {}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is None

    def test_unknown_use_code_skipped(self):
        props = {"L03b_001": "99"}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is None

    def test_japanese_name_input(self):
        """If the attribute already contains the full name, resolve it."""
        props = {"用途地域コード": "商業地域"}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["use_district"] == "商業地域"
        assert row["use_code"] == "10"

    def test_zero_padded_code(self):
        props = {"L03b_001": "1"}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["use_code"] == "01"
        assert row["use_district"] == "第一種低層住居専用地域"
