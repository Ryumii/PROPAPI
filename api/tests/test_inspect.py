"""Tests for POST /v1/land/inspect — schema validation & error handling."""

import pytest
from pydantic import ValidationError

from app.schemas.inspect import InspectRequest


class TestInspectRequestValidation:
    def test_address_only(self) -> None:
        req = InspectRequest(address="東京都渋谷区渋谷2-24-12")
        assert req.address is not None
        assert req.lat is None
        assert req.options.include_hazard is True

    def test_coordinates_only(self) -> None:
        req = InspectRequest(lat=35.6595, lng=139.7004)
        assert req.lat == 35.6595
        assert req.lng == 139.7004

    def test_both_address_and_coords(self) -> None:
        req = InspectRequest(address="東京都渋谷区渋谷2-24-12", lat=35.6595, lng=139.7004)
        assert req.address is not None
        assert req.lat is not None

    def test_missing_location_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            InspectRequest()
        assert "address" in str(exc_info.value) or "lat" in str(exc_info.value)

    def test_lat_only_without_lng_raises(self) -> None:
        with pytest.raises(ValidationError):
            InspectRequest(lat=35.6595)

    def test_coordinate_range_lat(self) -> None:
        with pytest.raises(ValidationError):
            InspectRequest(lat=10.0, lng=139.0)  # lat < 20

    def test_coordinate_range_lng(self) -> None:
        with pytest.raises(ValidationError):
            InspectRequest(lat=35.0, lng=100.0)  # lng < 122

    def test_options_hazard_only(self) -> None:
        req = InspectRequest(
            address="test",
            options={"include_hazard": True, "include_zoning": False},
        )
        assert req.options.include_hazard is True
        assert req.options.include_zoning is False

    def test_options_zoning_only(self) -> None:
        req = InspectRequest(
            address="test",
            options={"include_hazard": False, "include_zoning": True},
        )
        assert req.options.include_hazard is False
        assert req.options.include_zoning is True
