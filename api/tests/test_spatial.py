"""Tests for spatial query service — unit tests with mocked DB."""

from app.services.spatial import (
    FloodResult,
    LandslideResult,
    LiquefactionMapInfo,
    SpatialQueryResult,
    TsunamiResult,
    ZoningResult,
    _point_wkt,
    build_liquefaction_map_url,
)


class TestPointWkt:
    def test_format(self) -> None:
        wkt = _point_wkt(35.6595, 139.7004)
        assert wkt == "SRID=4326;POINT(139.7004 35.6595)"

    def test_precision(self) -> None:
        wkt = _point_wkt(35.0, 139.0)
        assert "139.0" in wkt
        assert "35.0" in wkt


class TestDataclassDefaults:
    def test_flood_result_defaults(self) -> None:
        r = FloodResult()
        assert r.depth_rank == 0
        assert r.source_name == "国土交通省 洪水浸水想定区域図"

    def test_landslide_result_defaults(self) -> None:
        r = LandslideResult()
        assert r.zone_type is None

    def test_tsunami_result_defaults(self) -> None:
        r = TsunamiResult()
        assert r.depth_m is None

    def test_liquefaction_map_info_defaults(self) -> None:
        r = LiquefactionMapInfo()
        assert r.map_url == ""
        assert "J-SHIS" in r.source_name

    def test_liquefaction_map_url_builder(self) -> None:
        url = build_liquefaction_map_url(35.6595, 139.7004)
        assert "lat=35.6595" in url
        assert "lon=139.7004" in url
        assert "j-shis.bosai.go.jp" in url

    def test_zoning_result_defaults(self) -> None:
        r = ZoningResult()
        assert r.use_district == ""
        assert r.source_name == "国土数値情報 用途地域データ"

    def test_spatial_query_result_all_none(self) -> None:
        r = SpatialQueryResult()
        assert r.flood is None
        assert r.landslide is None
        assert r.tsunami is None
        assert r.liquefaction is None
        assert r.zoning is None
