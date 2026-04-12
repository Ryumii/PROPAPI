"""Tests for ETL loader transform functions (pure logic, no DB)."""

from __future__ import annotations

import json

import pytest
from shapely.geometry import Polygon, mapping

from etl.scripts.load_flood import transform_feature as flood_transform
from etl.scripts.load_landslide import transform_feature as landslide_transform
from etl.scripts.load_tsunami import (
    _parse_depth_range,
    transform_feature as tsunami_transform,
)
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


class TestFloodTransformA31b:
    """Tests for A31b (2024) flood data format."""

    def test_a31b_rank_1(self):
        props = {"A31b_201": 1}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 1
        assert row["depth_range"] == "0.5m未満"
        assert row["river_name"] is None
        assert row["city"] is None

    def test_a31b_rank_6_clamped_to_5(self):
        """A31b rank 6 (20m以上) maps to scoring rank 5."""
        props = {"A31b_201": 6}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 5
        assert row["depth_range"] == "20m以上"

    def test_a31b_rank_3(self):
        props = {"A31b_201": 3}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 3
        assert row["depth_range"] == "3m以上5m未満"

    def test_a31b_keikaku_kibou(self):
        """A31b_101 (計画規模) is also detected."""
        props = {"A31b_101": 2}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_rank"] == 2
        assert row["depth_range"] == "0.5m以上3m未満"

    def test_a31b_zero_rank_skipped(self):
        """A31b rank 0 or below is invalid — skip."""
        props = {"A31b_201": 0}
        row = flood_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is None


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

    def test_basic_survey_zone_code_3(self):
        """A33_001=3 (基礎調査完了) — new in 2024 data."""
        props = {"A33_001": "3"}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["zone_type"] == "基礎調査完了"

    def test_japanese_name_passthrough(self):
        props = {"区域区分": "特別警戒区域"}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["zone_type"] == "特別警戒区域"

    def test_missing_zone_type_skipped(self):
        props = {}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is None

    def test_city_from_a33_006(self):
        """A33_006 contains location (所在地)."""
        props = {"A33_001": 1, "A33_006": "町田市真光寺2"}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["city"] == "町田市真光寺2"

    def test_numeric_zone_type(self):
        """A33 data provides integer zone type (not string)."""
        props = {"A33_001": 2}
        row = landslide_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["zone_type"] == "特別警戒区域"


# ── Tsunami transform ───────────────────────────────────────


class TestTsunamiTransform:
    def test_basic_legacy(self):
        """Legacy format: direct numeric depth."""
        props = {"浸水深": "3.5"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(3.5)

    def test_missing_depth(self):
        props = {}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] is None

    def test_city(self):
        props = {"浸水深": "1.0", "市区町村名": "江東区"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["city"] == "江東区"

    def test_a40_depth_range_string(self):
        """A40_003 depth range string — new format."""
        props = {"A40_001": "東京都", "A40_003": "0.3m以上 ～ 0.5m未満"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(0.4, abs=0.01)

    def test_a40_depth_range_no_space(self):
        """A40_003 without spaces around tilde."""
        props = {"A40_001": "東京都", "A40_003": "1m以上～3m未満"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(2.0, abs=0.01)

    def test_a40_depth_range_20m_over(self):
        props = {"A40_001": "東京都", "A40_003": "20m以上"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(25.0, abs=0.01)

    def test_a40_depth_range_under_03(self):
        props = {"A40_001": "東京都", "A40_003": "～0.3m未満"}
        row = tsunami_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["depth_m"] == pytest.approx(0.15, abs=0.01)


class TestParseDepthRange:
    def test_exact_match(self):
        assert _parse_depth_range("0.3m以上 ～ 0.5m未満") == pytest.approx(0.4)

    def test_regex_fallback(self):
        """Unknown range still extracts numbers."""
        assert _parse_depth_range("2m以上～4m未満") == pytest.approx(3.0)

    def test_none_for_garbage(self):
        assert _parse_depth_range("不明") is None


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


# ── Zoning transform (A55 format) ───────────────────────────


class TestZoningTransformA55:
    """Tests for A55 (都市計画決定GIS) attribute mapping."""

    def test_a55_youto_basic(self):
        """A55 youto attributes: numeric YoutoCode, string BCR/FAR."""
        props = {
            "YoutoCode": 10,
            "YoutoName": "商業地域",
            "BCR": "80",
            "FAR": "500",
            "Pref": "東京都",
            "Citycode": "13101",
            "Cityname": "千代田区",
        }
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["use_code"] == "10"
        assert row["use_district"] == "商業地域"
        assert row["coverage_pct"] == 80
        assert row["floor_ratio_pct"] == 500
        assert row["city"] == "千代田区"

    def test_a55_single_digit_code(self):
        """A55 YoutoCode is int (5 not '05'), must be zero-padded."""
        props = {"YoutoCode": 5, "YoutoName": "第１種住居地域"}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["use_code"] == "05"
        assert row["use_district"] == "第一種住居地域"

    def test_a55_fire_code_24(self):
        """A55 AreaCode 24 maps to normalised fire code '01' (防火地域)."""
        props = {
            "YoutoCode": 10,
            "YoutoName": "商業地域",
            "AreaCode": 24,
            "AreaType": "防火地域",
        }
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["fire_code"] == "01"
        assert row["fire_prevention"] == "防火地域"

    def test_a55_fire_code_25(self):
        """A55 AreaCode 25 maps to normalised fire code '02' (準防火地域)."""
        props = {
            "YoutoCode": 5,
            "AreaCode": 25,
        }
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["fire_code"] == "02"
        assert row["fire_prevention"] == "準防火地域"

    def test_a55_no_fire_info(self):
        """A55 youto record without fire prevention data."""
        props = {"YoutoCode": 1}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is not None
        assert row["fire_code"] is None
        assert row["fire_prevention"] is None

    def test_a55_missing_youto_code_skipped(self):
        """A55 record without YoutoCode is skipped."""
        props = {"Cityname": "千代田区"}
        row = zoning_transform(GEOM, props, source_id=1, prefecture="東京都")
        assert row is None
