"""TASK-016: 住所マスタデータロード (東京23区).

Data source : アドレス・ベース・レジストリ (デジタル庁)
Format      : CSV  (UTF-8, with header)
Target table: address_master

The registry distributes address data at multiple levels:
  - 町字 (town): 大字・町丁目 level with representative lat/lng
  - 街区 (block): block-number level
  - 住居表示 (building): building-number level

This loader reads CSV files with auto-detected column names.

Usage:
    python -m etl.scripts.load_address --input-dir ./etl/data/address
    python -m etl.scripts.load_address --input-dir ./etl/data/address --prefecture 東京都
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Any

from etl.common.db import (
    batch_execute,
    clear_table_for_prefecture,
    ensure_postgis,
    get_session,
    register_data_source,
)
from etl.common.quality import QualityReport
from etl.config import BATCH_SIZE, JAPAN_BBOX, TOKYO_PREF_NAME

logger = logging.getLogger(__name__)

TABLE = "address_master"

INSERT_SQL = (
    "INSERT INTO address_master "
    "(prefecture, city, town, block_number, building_number, "
    " normalized_addr, geom, source) "
    "VALUES ("
    " :prefecture, :city, :town, :block_number, :building_number, "
    " :normalized_addr, "
    " ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), "
    " :source)"
)

# Column name candidates for auto-detection across different CSV versions.
COL = {
    "prefecture": ["都道府県名", "pref_name", "prefecture"],
    "city": ["市区町村名", "city_name", "city"],
    "town": ["大字町丁目名", "town_name", "town", "大字・町字名称"],
    "block": ["街区符号", "block_number", "block", "丁目名"],
    "building": ["住居番号", "building_number", "building"],
    "lat": ["代表緯度", "代表点_緯度", "緯度", "lat", "latitude"],
    "lng": ["代表経度", "代表点_経度", "経度", "lng", "lon", "longitude"],
}


def _find_col(header: list[str], candidates: list[str]) -> str | None:
    """Find the first matching column name from *candidates*."""
    for c in candidates:
        if c in header:
            return c
    return None


def _build_normalized(
    prefecture: str,
    city: str,
    town: str,
    block: str | None,
    building: str | None,
) -> str:
    """Build the normalised address string for lookup matching."""
    parts = [prefecture, city, town]
    if block:
        parts.append(f"{block}番")
    if building:
        parts.append(f"{building}号")
    return "".join(parts)


def load_csv_file(
    session: Any,
    path: Path,
    source_id: int,
    prefecture_filter: str,
    report: QualityReport,
    batch_size: int,
) -> int:
    """Read one CSV file and insert matching rows. Returns count loaded."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            logger.error("No header found in %s", path)
            return 0

        header = list(reader.fieldnames)
        logger.info("CSV columns: %s", header[:10])

        # Resolve column names
        col_pref = _find_col(header, COL["prefecture"])
        col_city = _find_col(header, COL["city"])
        col_town = _find_col(header, COL["town"])
        col_block = _find_col(header, COL["block"])
        col_building = _find_col(header, COL["building"])
        col_lat = _find_col(header, COL["lat"])
        col_lng = _find_col(header, COL["lng"])

        if not all([col_pref, col_city, col_town, col_lat, col_lng]):
            logger.error(
                "Required columns not found. Need: prefecture, city, town, lat, lng. "
                "Found mappings: pref=%s city=%s town=%s lat=%s lng=%s",
                col_pref, col_city, col_town, col_lat, col_lng,
            )
            return 0

        rows: list[dict[str, Any]] = []
        for raw_row in reader:
            report.record_feature()

            pref = raw_row.get(col_pref, "").strip()  # type: ignore[arg-type]
            if pref != prefecture_filter:
                continue

            city = raw_row.get(col_city, "").strip()  # type: ignore[arg-type]
            town = raw_row.get(col_town, "").strip()  # type: ignore[arg-type]
            block = raw_row.get(col_block, "").strip() if col_block else None  # type: ignore[arg-type]
            building = raw_row.get(col_building, "").strip() if col_building else None  # type: ignore[arg-type]

            # Parse coordinates
            try:
                lat = float(raw_row[col_lat])  # type: ignore[index]
                lng = float(raw_row[col_lng])  # type: ignore[index]
            except (ValueError, TypeError, KeyError):
                report.record_skip_invalid()
                continue

            # Bounds check
            if not (JAPAN_BBOX[0] <= lng <= JAPAN_BBOX[2] and JAPAN_BBOX[1] <= lat <= JAPAN_BBOX[3]):
                report.record_skip_bounds()
                continue

            if not town:
                report.record_skip_invalid()
                continue

            # Normalize empty strings to None
            block = block or None
            building = building or None

            normalized = _build_normalized(pref, city, town, block, building)

            rows.append({
                "prefecture": pref,
                "city": city,
                "town": town,
                "block_number": block,
                "building_number": building,
                "normalized_addr": normalized,
                "lat": lat,
                "lng": lng,
                "source": "アドレス・ベース・レジストリ",
            })
            report.record_loaded()

        # Batch insert
        loaded = batch_execute(
            session,
            INSERT_SQL,
            rows,
            batch_size=batch_size,
            label=TABLE,
        )
        return loaded


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Load address master data from Address Base Registry CSV"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing CSV files",
    )
    parser.add_argument(
        "--prefecture",
        default=TOKYO_PREF_NAME,
        help="Prefecture to filter (default: 東京都)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Skip clearing existing prefecture data",
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
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    # Find CSV files
    csv_files = sorted(args.input_dir.glob("*.csv"))
    if not csv_files:
        logger.error("No CSV files found in %s", args.input_dir)
        sys.exit(1)
    logger.info("Found %d CSV file(s) to process", len(csv_files))

    report = QualityReport(table_name=TABLE)
    total_loaded = 0

    with get_session() as session:
        ensure_postgis(session)

        source_id = register_data_source(
            session,
            name="アドレス・ベース・レジストリ (東京23区)",
            provider="デジタル庁",
            url="https://catalog.registries.digital.go.jp/rc/dataset/",
            license_type="CC BY 4.0",
            coverage_area=args.prefecture,
        )

        if not args.no_clear:
            clear_table_for_prefecture(session, TABLE, args.prefecture)

        for csv_path in csv_files:
            logger.info("Processing %s …", csv_path.name)
            loaded = load_csv_file(
                session, csv_path, source_id, args.prefecture, report, args.batch_size,
            )
            total_loaded += loaded

    report.log_summary()
    logger.info("Done — %d addresses loaded", total_loaded)
    sys.exit(0 if total_loaded > 0 or report.total_features == 0 else 1)


if __name__ == "__main__":
    main()
