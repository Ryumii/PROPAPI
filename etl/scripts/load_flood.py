"""TASK-012: 洪水浸水想定データ ETL (東京23区).

Data source : 国土数値情報 A31 — 洪水浸水想定区域
Format      : GeoJSON or Shapefile  (EPSG:4326 or JGD2011)
Target table: hazard_flood

Usage:
    python -m etl.scripts.load_flood --input-dir ./etl/data/flood
    python -m etl.scripts.load_flood --input-dir ./etl/data/flood --source-epsg 6668
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from etl.common.geo import resolve_attr, safe_int
from etl.common.loader import build_cli, run_etl
from etl.config import FLOOD_DEPTH_RANGE

logger = logging.getLogger(__name__)

TABLE = "hazard_flood"

INSERT_SQL = (
    "INSERT INTO hazard_flood "
    "(geom, depth_rank, depth_range, return_period, river_name, "
    " source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)), "
    " :depth_rank, :depth_range, :return_period, :river_name, "
    " :source_id, :prefecture, :city)"
)

# Attribute name candidates across different data versions.
# The loader tries each name in order and picks the first match.
ATTR = {
    "depth_rank": ["A31_001", "浸水深ランク", "depth_rank", "DepthRank", "浸水ランク"],
    "depth_range": ["A31_002", "浸水深", "depth_range", "DepthRange"],
    "return_period": ["A31_003", "想定最大規模_計画規模", "return_period", "計画規模"],
    "river_name": ["A31_004", "河川名", "river_name", "RiverName", "対象河川"],
    "city": ["市区町村名", "city", "A31_005", "市区町村", "City"],
}


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single flood feature to a DB row dict."""
    depth_rank = safe_int(resolve_attr(props, ATTR["depth_rank"]), default=0)
    if depth_rank is None:
        depth_rank = 0

    # Clamp to 0-5
    depth_rank = max(0, min(5, depth_rank))

    depth_range = resolve_attr(props, ATTR["depth_range"])
    if depth_range is None:
        depth_range = FLOOD_DEPTH_RANGE.get(depth_rank, "不明")

    return {
        "geom_json": geom_json,
        "depth_rank": depth_rank,
        "depth_range": str(depth_range),
        "return_period": safe_int(resolve_attr(props, ATTR["return_period"])),
        "river_name": resolve_attr(props, ATTR["river_name"]),
        "source_id": source_id,
        "prefecture": prefecture,
        "city": resolve_attr(props, ATTR["city"]),
    }


def main() -> None:
    parser = build_cli("Load flood inundation data (国土数値情報 A31)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name="国土数値情報 洪水浸水想定区域データ (A31)",
        data_source_provider="国土交通省 国土政策局",
        data_source_url="https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v3_1.html",
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
