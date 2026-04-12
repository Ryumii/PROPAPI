"""Tests for etl.common.quality — QualityReport and bounds checking."""

from __future__ import annotations

from shapely.geometry import Point, Polygon

from etl.common.quality import QualityReport, check_in_bounds

# ── check_in_bounds ──────────────────────────────────────────


class TestCheckInBounds:
    def test_tokyo_point_in_japan(self):
        p = Point(139.7, 35.7)
        assert check_in_bounds(p) is True

    def test_outside_japan(self):
        p = Point(-73.9, 40.7)  # New York
        assert check_in_bounds(p) is False

    def test_edge_case_okinawa(self):
        p = Point(127.7, 26.3)  # Okinawa
        assert check_in_bounds(p) is True

    def test_custom_bbox(self):
        p = Point(139.7, 35.7)
        assert check_in_bounds(p, bbox=(139.0, 35.0, 140.0, 36.0)) is True
        assert check_in_bounds(p, bbox=(140.0, 35.0, 141.0, 36.0)) is False


# ── QualityReport ────────────────────────────────────────────


class TestQualityReport:
    def test_initial_state(self):
        r = QualityReport(table_name="test_table")
        assert r.total_features == 0
        assert r.loaded_count == 0
        assert r.skip_total == 0
        assert r.success_rate == 0.0

    def test_accumulation(self):
        r = QualityReport(table_name="test_table")
        r.record_feature()
        r.record_feature()
        r.record_feature()
        r.record_loaded()
        r.record_loaded()
        r.record_skip_null()
        assert r.total_features == 3
        assert r.loaded_count == 2
        assert r.skipped_null_geom == 1
        assert r.skip_total == 1
        assert r.success_rate == pytest.approx(2 / 3)

    def test_bbox_tracking(self):
        r = QualityReport(table_name="test_table")
        poly = Polygon([(139.0, 35.0), (140.0, 35.0), (140.0, 36.0), (139.0, 36.0)])
        r.record_loaded(poly)
        assert r.min_lng == pytest.approx(139.0)
        assert r.min_lat == pytest.approx(35.0)
        assert r.max_lng == pytest.approx(140.0)
        assert r.max_lat == pytest.approx(36.0)
        assert r.bbox_within_japan() is True

    def test_bbox_outside_japan(self):
        r = QualityReport(table_name="test_table")
        poly = Polygon([(-74, 40), (-73, 40), (-73, 41), (-74, 41)])
        r.record_loaded(poly)
        assert r.bbox_within_japan() is False

    def test_empty_report_passes_bbox_check(self):
        r = QualityReport(table_name="test_table")
        assert r.bbox_within_japan() is True


import pytest  # noqa: E402
