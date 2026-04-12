"""TASK-014: 津波浸水想定データ ETL.

Data source : 国土数値情報 A40 — 津波浸水想定
Format      : GeoJSON or Shapefile (CP932 or UTF-8, JGD2011 or WGS84)
Target table: hazard_tsunami

A40 attributes (2023 version):
  A40_001: 都道府県名
  A40_002: 都道府県コード
  A40_003: 浸水深レンジ文字列 ("～0.3m未満", "0.3m以上 ～ 0.5m未満", ...)

Usage:
    python -m etl.scripts.load_tsunami --input-dir ./etl/data/tsunami
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

from etl.common.geo import resolve_attr, safe_float
from etl.common.loader import build_cli, run_etl
from etl.config import TSUNAMI_DEPTH_RANGE_MAP

logger = logging.getLogger(__name__)

TABLE = "hazard_tsunami"

INSERT_SQL = (
    "INSERT INTO hazard_tsunami "
    "(geom, depth_m, source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)), "
    " :depth_m, :source_id, :prefecture, :city)"
)

# Attribute candidates for depth — supports both old and new versions
ATTR = {
    "depth_m": [
        "浸水深", "depth_m", "DepthM",
        "最大浸水深", "浸水深_m", "想定浸水深",
    ],
    "depth_range": ["A40_003"],
    "prefecture": ["A40_001"],
    "city": ["市区町村名", "city", "市区町村", "City"],
}


def _parse_depth_range(range_str: str) -> float | None:
    """Parse a Japanese depth range string to a representative depth in metres.

    Uses the config lookup table first, then falls back to regex extraction.
    """
    s = range_str.strip()

    # Exact match from config
    if s in TSUNAMI_DEPTH_RANGE_MAP:
        return TSUNAMI_DEPTH_RANGE_MAP[s]

    # Regex fallback: extract numbers and use midpoint
    nums = re.findall(r"([\d.]+)\s*m", s)
    if len(nums) >= 2:
        return (float(nums[0]) + float(nums[1])) / 2
    if len(nums) == 1:
        return float(nums[0])

    return None


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single tsunami inundation feature to a DB row dict.

    Auto-detects new (A40_003 range string) vs old (A40_001 numeric) format.
    """
    # Try new format first: A40_003 = depth range string
    depth_range_str = resolve_attr(props, ATTR["depth_range"])
    if depth_range_str is not None and isinstance(depth_range_str, str) and "m" in depth_range_str:
        depth_m = _parse_depth_range(depth_range_str)
    else:
        # Legacy format: direct numeric depth
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
