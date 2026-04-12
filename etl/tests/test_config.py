"""Tests for etl.config — mapping constants and configuration."""

from __future__ import annotations

from etl.config import (
    FIRE_PREVENTION_MAP,
    FLOOD_DEPTH_RANGE,
    TOKYO_23_WARDS,
    USE_DISTRICT_MAP,
)


class TestTokyoWards:
    def test_count(self):
        assert len(TOKYO_23_WARDS) == 23

    def test_chiyoda(self):
        assert TOKYO_23_WARDS["13101"] == "千代田区"

    def test_edogawa(self):
        assert TOKYO_23_WARDS["13123"] == "江戸川区"

    def test_all_end_with_ku(self):
        for name in TOKYO_23_WARDS.values():
            assert name.endswith("区")


class TestUseDistrictMap:
    def test_count(self):
        """13 zoning types as defined by Building Standards Act."""
        assert len(USE_DISTRICT_MAP) == 13

    def test_codes_are_2char(self):
        for code in USE_DISTRICT_MAP:
            assert len(code) == 2

    def test_low_rise_residential(self):
        assert USE_DISTRICT_MAP["01"] == "第一種低層住居専用地域"

    def test_exclusive_industrial(self):
        assert USE_DISTRICT_MAP["13"] == "工業専用地域"


class TestFirePreventionMap:
    def test_two_types(self):
        assert len(FIRE_PREVENTION_MAP) == 2
        assert "01" in FIRE_PREVENTION_MAP
        assert "02" in FIRE_PREVENTION_MAP


class TestFloodDepthRange:
    def test_six_levels(self):
        assert len(FLOOD_DEPTH_RANGE) == 6

    def test_zero_is_none(self):
        assert FLOOD_DEPTH_RANGE[0] == "浸水なし"

    def test_five_is_max(self):
        assert FLOOD_DEPTH_RANGE[5] == "10m以上"
