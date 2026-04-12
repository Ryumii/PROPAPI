"""TASK-013: 土砂災害警戒区域データ ETL (東京23区).

Data source : 国土数値情報 A33 — 土砂災害警戒区域
Format      : GeoJSON or Shapefile  (EPSG:4326 or JGD2011)
Target table: hazard_landslide

Usage:
    python -m etl.scripts.load_landslide --input-dir ./etl/data/landslide
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from etl.common.geo import resolve_attr
from etl.common.loader import build_cli, run_etl

logger = logging.getLogger(__name__)

TABLE = "hazard_landslide"

INSERT_SQL = (
    "INSERT INTO hazard_landslide "
    "(geom, zone_type, source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)), "
    " :zone_type, :source_id, :prefecture, :city)"
)

# 区域区分: 1 = 警戒区域 (Yellow), 2 = 特別警戒区域 (Red)
ZONE_TYPE_MAP: dict[str, str] = {
    "1": "警戒区域",
    "2": "特別警戒区域",
    "警戒区域": "警戒区域",
    "特別警戒区域": "特別警戒区域",
}

ATTR = {
    "zone_type": ["A33_001", "区域区分", "zone_type", "ZoneType", "種別"],
    "city": ["市区町村名", "city", "A33_002", "市区町村", "City"],
}


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single landslide hazard feature to a DB row dict."""
    raw_zone = resolve_attr(props, ATTR["zone_type"])
    if raw_zone is None:
        return None  # skip — zone_type is required

    zone_type = ZONE_TYPE_MAP.get(str(raw_zone).strip(), str(raw_zone).strip())
    if zone_type not in ("警戒区域", "特別警戒区域"):
        # Unknown zone type — still load, but log
        logging.getLogger(__name__).warning("Unknown zone_type: %s", zone_type)

    return {
        "geom_json": geom_json,
        "zone_type": zone_type,
        "source_id": source_id,
        "prefecture": prefecture,
        "city": resolve_attr(props, ATTR["city"]),
    }


def main() -> None:
    parser = build_cli("Load landslide hazard zone data (国土数値情報 A33)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name="国土数値情報 土砂災害警戒区域データ (A33)",
        data_source_provider="国土交通省 国土政策局",
        data_source_url="https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A33-v1_4.html",
        input_dir=args.input_dir,
        prefecture=args.prefecture,
        source_epsg=args.source_epsg,
        clear_existing=not args.no_clear,
        batch_size=args.batch_size,
    )

    logger.info("Done — %d loaded, %d skipped", result.loaded, result.skipped)
    sys.exit(0 if result.loaded > 0 or result.quality.total_features == 0 else 1)


if __name__ == "__main__":
    main()
