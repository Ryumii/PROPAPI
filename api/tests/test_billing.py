"""Tests for billing / usage tracking service — unit level."""

from app.services.billing import QUOTA_ALERT_THRESHOLD


class TestBillingConstants:
    def test_threshold_is_80_pct(self) -> None:
        assert QUOTA_ALERT_THRESHOLD == 0.80

    def test_threshold_calculation(self) -> None:
        limit = 1000
        threshold = limit * QUOTA_ALERT_THRESHOLD
        assert threshold == 800
