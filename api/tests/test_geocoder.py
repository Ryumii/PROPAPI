"""Tests for geocoder — coordinate passthrough & address normalization."""


from app.services.geocoder import GeocodingResult


class TestGeocodingResult:
    def test_dataclass_fields(self) -> None:
        r = GeocodingResult(lat=35.6595, lng=139.7004, confidence=0.97, method="address_match")
        assert r.lat == 35.6595
        assert r.lng == 139.7004
        assert r.confidence == 0.97
        assert r.method == "address_match"
        assert r.prefecture is None

    def test_with_location_info(self) -> None:
        r = GeocodingResult(
            lat=35.6595,
            lng=139.7004,
            confidence=0.97,
            method="address_match",
            prefecture="東京都",
            city="渋谷区",
            town="渋谷二丁目",
        )
        assert r.prefecture == "東京都"
        assert r.city == "渋谷区"
