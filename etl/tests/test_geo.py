"""Tests for etl.common.geo — geometry reading, CRS transform, attribute helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import MultiPolygon, Point, Polygon, mapping

from etl.common.geo import (
    ensure_multi,
    geom_to_geojson,
    read_geojson,
    resolve_attr,
    safe_float,
    safe_int,
    transform_to_wgs84,
)

# ── transform_to_wgs84 ──────────────────────────────────────


class TestTransformToWgs84:
    def test_passthrough_4326(self):
        """EPSG:4326 input should be returned unchanged."""
        p = Point(139.7, 35.7)
        result = transform_to_wgs84(p, source_epsg=4326)
        assert abs(result.x - 139.7) < 1e-9
        assert abs(result.y - 35.7) < 1e-9

    def test_jgd2011_to_wgs84(self):
        """JGD2011 → WGS84 should be sub-metre difference."""
        p = Point(139.7, 35.7)
        result = transform_to_wgs84(p, source_epsg=6668)
        # JGD2011 ≈ WGS84, difference should be < 0.001 degrees
        assert abs(result.x - 139.7) < 0.001
        assert abs(result.y - 35.7) < 0.001


# ── ensure_multi ─────────────────────────────────────────────


class TestEnsureMulti:
    def test_polygon_to_multi(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        result = ensure_multi(poly)
        assert isinstance(result, MultiPolygon)
        assert len(result.geoms) == 1

    def test_multi_passthrough(self):
        mp = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
        result = ensure_multi(mp)
        assert result is mp

    def test_point_raises(self):
        with pytest.raises(ValueError, match="Unexpected geometry type"):
            ensure_multi(Point(0, 0))


# ── geom_to_geojson ─────────────────────────────────────────


class TestGeomToGeojson:
    def test_roundtrip(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        result = geom_to_geojson(poly)
        parsed = json.loads(result)
        assert parsed["type"] == "Polygon"
        assert len(parsed["coordinates"]) == 1


# ── read_geojson ─────────────────────────────────────────────


class TestReadGeojson:
    def test_reads_features(self, tmp_path: Path):
        poly = Polygon([(139.7, 35.6), (139.8, 35.6), (139.8, 35.7), (139.7, 35.7)])
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": mapping(poly),
                    "properties": {"name": "test", "depth_rank": 3},
                },
            ],
        }
        fpath = tmp_path / "test.geojson"
        fpath.write_text(json.dumps(fc), encoding="utf-8")

        features = list(read_geojson(fpath))
        assert len(features) == 1
        geom, props = features[0]
        assert geom.geom_type == "Polygon"
        assert props["name"] == "test"
        assert props["depth_rank"] == 3

    def test_skips_null_geometry(self, tmp_path: Path):
        fc = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": None, "properties": {}},
            ],
        }
        fpath = tmp_path / "null.geojson"
        fpath.write_text(json.dumps(fc), encoding="utf-8")

        features = list(read_geojson(fpath))
        assert len(features) == 0


# ── resolve_attr ─────────────────────────────────────────────


class TestResolveAttr:
    def test_first_match(self):
        props = {"A31_001": 3, "depth_rank": 5}
        assert resolve_attr(props, ["A31_001", "depth_rank"]) == 3

    def test_fallback(self):
        props = {"depth_rank": 5}
        assert resolve_attr(props, ["A31_001", "depth_rank"]) == 5

    def test_default_none(self):
        props = {"other": 1}
        assert resolve_attr(props, ["A31_001", "depth_rank"]) is None

    def test_custom_default(self):
        props = {}
        assert resolve_attr(props, ["x"], default=42) == 42

    def test_skips_none_values(self):
        props = {"A31_001": None, "depth_rank": 3}
        assert resolve_attr(props, ["A31_001", "depth_rank"]) == 3


# ── safe_int / safe_float ────────────────────────────────────


class TestSafeConversions:
    def test_safe_int_valid(self):
        assert safe_int("3") == 3
        assert safe_int(3) == 3
        assert safe_int(3.7) == 3

    def test_safe_int_invalid(self):
        assert safe_int("abc") is None
        assert safe_int(None) is None
        assert safe_int("abc", default=0) == 0

    def test_safe_float_valid(self):
        assert safe_float("3.14") == pytest.approx(3.14)
        assert safe_float(3) == pytest.approx(3.0)

    def test_safe_float_invalid(self):
        assert safe_float("abc") is None
        assert safe_float(None) is None
        assert safe_float(None, default=0.0) == pytest.approx(0.0)
