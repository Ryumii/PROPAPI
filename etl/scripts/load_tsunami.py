"""TASK-014: 津波浸水想定データ ETL (東京23区沿岸部).

Data source : 国土数値情報 A40 — 津波浸水想定
Format      : GeoJSON or Shapefile  (EPSG:4326 or JGD2011)
Target table: hazard_tsunami

Usage:
    python -m etl.scripts.load_tsunami --input-dir ./etl/data/tsunami
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from etl.common.geo import resolve_attr, safe_float
from etl.common.loader import build_cli, run_etl

logger = logging.getLogger(__name__)

TABLE = "hazard_tsunami"

INSERT_SQL = (
    "INSERT INTO hazard_tsunami "
    "(geom, depth_m, source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)), "
    " :depth_m, :source_id, :prefecture, :city)"
)

ATTR = {
    "depth_m": [
        "A40_001", "浸水深", "depth_m", "DepthM",
        "最大浸水深", "浸水深_m", "想定浸水深",
    ],
    "city": ["市区町村名", "city", "A40_002", "市区町村", "City"],
}


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single tsunami inundation feature to a DB row dict."""
    depth_m = safe_float(resolve_attr(props, ATTR["depth_m"]))

    return {
        "geom_json": geom_json,
        "depth_m": depth_m,
        "source_id": source_id,
        "prefecture": prefecture,
        "city": resolve_attr(props, ATTR["city"]),
    }


def main() -> None:
    parser = build_cli("Load tsunami inundation data (国土数値情報 A40)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name="国土数値情報 津波浸水想定データ (A40)",
        data_source_provider="国土交通省 国土政策局",
        data_source_url="https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A40-v4_0.html",
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
