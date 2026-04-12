"""Shared ETL loader framework.

Each data-type script provides a transform callback and metadata;
``run_etl`` handles the common pipeline: read → transform → insert → report.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from etl.common.db import (
    batch_execute,
    clear_table_for_prefecture,
    ensure_postgis,
    get_session,
    register_data_source,
)
from etl.common.geo import (
    ensure_multi,
    find_files,
    geom_to_geojson,
    read_features,
    transform_to_wgs84,
)
from etl.common.quality import QualityReport, check_in_bounds
from etl.config import BATCH_SIZE, TOKYO_PREF_NAME

logger = logging.getLogger(__name__)

# Type alias for the per-row transform callback.
# Receives (geom_geojson_str, properties, source_id, prefecture) → dict | None
TransformFn = Callable[[str, dict[str, Any], int, str], dict[str, Any] | None]


@dataclass
class ETLResult:
    """Summary returned by ``run_etl``."""

    loaded: int
    skipped: int
    quality: QualityReport


def build_cli(description: str) -> argparse.ArgumentParser:
    """Construct an argparse parser with common ETL flags."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing input files (.geojson or .shp)",
    )
    parser.add_argument(
        "--prefecture",
        default=TOKYO_PREF_NAME,
        help="Prefecture name for data scope (default: 東京都)",
    )
    parser.add_argument(
        "--source-epsg",
        type=int,
        default=4326,
        help="Source CRS EPSG code (default: 4326, use 6668 for JGD2011)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Skip clearing existing data for the prefecture before loading",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for DB inserts (default: {BATCH_SIZE})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def run_etl(
    *,
    table_name: str,
    insert_sql: str,
    transform_fn: TransformFn,
    data_source_name: str,
    data_source_provider: str,
    data_source_url: str | None = None,
    input_dir: Path,
    prefecture: str = TOKYO_PREF_NAME,
    source_epsg: int = 4326,
    clear_existing: bool = True,
    batch_size: int = BATCH_SIZE,
    file_patterns: tuple[str, ...] = ("*.geojson", "*.shp"),
) -> ETLResult:
    """Execute a full ETL pipeline.

    1. Find input files
    2. Register data source
    3. Optionally clear existing prefecture data
    4. Read → transform → batch insert
    5. Report quality metrics
    """
    report = QualityReport(table_name=table_name)

    # ── discover files ──
    files = find_files(input_dir, file_patterns)
    if not files:
        logger.error("No matching files found in %s", input_dir)
        sys.exit(1)
    logger.info("Found %d file(s) to process", len(files))

    with get_session() as session:
        ensure_postgis(session)

        # ── register data source ──
        source_id = register_data_source(
            session,
            name=data_source_name,
            provider=data_source_provider,
            url=data_source_url,
            coverage_area=prefecture,
        )

        # ── clear old data ──
        if clear_existing:
            clear_table_for_prefecture(session, table_name, prefecture)

        # ── read & transform ──
        rows: list[dict[str, Any]] = []
        for fpath in files:
            logger.info("Processing %s …", fpath.name)
            for geom, props in read_features(fpath):
                report.record_feature()

                # CRS transform
                if source_epsg != 4326:
                    geom = transform_to_wgs84(geom, source_epsg=source_epsg)

                # Bounds check
                if not check_in_bounds(geom):
                    report.record_skip_bounds()
                    continue

                # Ensure MULTI geometry
                try:
                    geom = ensure_multi(geom)
                except ValueError:
                    report.record_skip_invalid()
                    continue

                geom_json = geom_to_geojson(geom)

                # Per-dataset transform
                row = transform_fn(geom_json, props, source_id, prefecture)
                if row is None:
                    report.record_skip_invalid()
                    continue

                report.record_loaded(geom)
                rows.append(row)

        # ── batch insert ──
        logger.info("Inserting %d rows into %s …", len(rows), table_name)
        loaded = batch_execute(
            session,
            insert_sql,
            rows,
            batch_size=batch_size,
            label=table_name,
        )

    report.log_summary()
    return ETLResult(loaded=loaded, skipped=report.skip_total, quality=report)
