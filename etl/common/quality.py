"""Data quality checks for ETL pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from etl.config import JAPAN_BBOX

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Accumulated quality metrics for a single ETL run."""

    table_name: str
    total_features: int = 0
    loaded_count: int = 0
    skipped_null_geom: int = 0
    skipped_out_of_bounds: int = 0
    skipped_invalid: int = 0
    min_lng: float = field(default=180.0)
    min_lat: float = field(default=90.0)
    max_lng: float = field(default=-180.0)
    max_lat: float = field(default=-90.0)

    # ── accumulators ──

    def record_feature(self) -> None:
        self.total_features += 1

    def record_loaded(self, geom: object | None = None) -> None:
        self.loaded_count += 1
        if geom is not None:
            self._update_bbox(geom)

    def record_skip_null(self) -> None:
        self.skipped_null_geom += 1

    def record_skip_bounds(self) -> None:
        self.skipped_out_of_bounds += 1

    def record_skip_invalid(self) -> None:
        self.skipped_invalid += 1

    def _update_bbox(self, geom: object) -> None:
        try:
            bounds = geom.bounds  # type: ignore[attr-defined]
            self.min_lng = min(self.min_lng, bounds[0])
            self.min_lat = min(self.min_lat, bounds[1])
            self.max_lng = max(self.max_lng, bounds[2])
            self.max_lat = max(self.max_lat, bounds[3])
        except Exception:  # noqa: BLE001
            pass

    # ── checks ──

    @property
    def skip_total(self) -> int:
        return self.skipped_null_geom + self.skipped_out_of_bounds + self.skipped_invalid

    @property
    def success_rate(self) -> float:
        if self.total_features == 0:
            return 0.0
        return self.loaded_count / self.total_features

    def bbox_within_japan(self) -> bool:
        """Check if loaded data falls within Japan's bounding box."""
        if self.loaded_count == 0:
            return True
        return (
            JAPAN_BBOX[0] <= self.min_lng
            and JAPAN_BBOX[1] <= self.min_lat
            and self.max_lng <= JAPAN_BBOX[2]
            and self.max_lat <= JAPAN_BBOX[3]
        )

    # ── reporting ──

    def log_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("Quality Report: %s", self.table_name)
        logger.info("-" * 60)
        logger.info("  Total features read : %d", self.total_features)
        logger.info("  Loaded successfully : %d", self.loaded_count)
        logger.info("  Skipped (null geom) : %d", self.skipped_null_geom)
        logger.info("  Skipped (bounds)    : %d", self.skipped_out_of_bounds)
        logger.info("  Skipped (invalid)   : %d", self.skipped_invalid)
        logger.info("  Success rate        : %.1f%%", self.success_rate * 100)
        if self.loaded_count > 0:
            logger.info(
                "  Bounding box        : (%.4f, %.4f) — (%.4f, %.4f)",
                self.min_lng,
                self.min_lat,
                self.max_lng,
                self.max_lat,
            )
            if not self.bbox_within_japan():
                logger.warning("  ⚠ Bounding box extends outside Japan!")
        logger.info("=" * 60)


def check_in_bounds(
    geom: object,
    bbox: tuple[float, float, float, float] = JAPAN_BBOX,
) -> bool:
    """Return True if the geometry centroid is within *bbox*."""
    try:
        c = geom.centroid  # type: ignore[attr-defined]
        return bbox[0] <= c.x <= bbox[2] and bbox[1] <= c.y <= bbox[3]
    except Exception:  # noqa: BLE001
        return False
