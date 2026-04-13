"""TASK-012: 洪水浸水想定データ ETL.

Supports two data formats:
  - A31b : 洪水浸水想定区域 (2024〜) — per-mesh SHP, ranks 1-6
  - A31  : 洪水浸水想定区域 (legacy) — per-bureau SHP, ranks 0-5

A31b structure:
  etl/data/flood/A31b-24_10_5339_SHP/
      20_想定最大規模/A31b-20-24_10_5339.shp  ← primary (recommended)
      10_計画規模/A31b-10-24_10_5339.shp

Target table: hazard_flood

Usage:
    python -m etl.scripts.load_flood --input-dir ./etl/data/flood
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

from etl.common.geo import resolve_attr, safe_int
from etl.common.loader import build_cli, run_etl
from etl.config import (
    A31B_DEPTH_RANGE,
    A31B_TO_NORMALISED_RANK,
    FLOOD_DEPTH_RANGE,
)

logger = logging.getLogger(__name__)

TABLE = "hazard_flood"

INSERT_SQL = (
    "INSERT INTO hazard_flood "
    "(geom, depth_rank, depth_range, return_period, river_name, "
    " source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326))), "
    " :depth_rank, :depth_range, :return_period, :river_name, "
    " :source_id, :prefecture, :city)"
)

# ── A31 (legacy) attribute candidates ────────────────────────
ATTR_A31 = {
    "depth_rank": ["A31_001", "浸水深ランク", "depth_rank", "DepthRank", "浸水ランク"],
    "depth_range": ["A31_002", "浸水深", "depth_range", "DepthRange"],
    "return_period": ["A31_003", "想定最大規模_計画規模", "return_period", "計画規模"],
    "river_name": ["A31_004", "河川名", "river_name", "RiverName", "対象河川"],
    "city": ["市区町村名", "city", "A31_005", "市区町村", "City"],
}

# ── A31b attribute candidates ────────────────────────────────
# A31b has a single field per category: A31b_101 (計画規模), A31b_201 (想定最大)
_A31B_RANK_FIELDS = [
    "A31b_201", "A31b_101", "A31b_301", "A31b_411", "A31b_421",
]


def _detect_a31b(props: dict[str, Any]) -> bool:
    """Check if properties contain A31b-style attribute names."""
    return any(k.startswith("A31b_") for k in props)


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single flood feature to a DB row dict.

    Auto-detects A31b vs A31 format.
    """
    if _detect_a31b(props):
        return _transform_a31b(geom_json, props, source_id, prefecture)
    return _transform_a31(geom_json, props, source_id, prefecture)


def _transform_a31b(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Transform A31b feature (2024 format)."""
    raw_rank = resolve_attr(props, _A31B_RANK_FIELDS)
    rank = safe_int(raw_rank)
    if rank is None or rank < 1:
        return None  # no valid depth rank

    # Normalise A31b rank (1-6) → scoring rank (0-5)
    depth_rank = A31B_TO_NORMALISED_RANK.get(rank, min(rank, 5))
    depth_range = A31B_DEPTH_RANGE.get(rank, "不明")

    return {
        "geom_json": geom_json,
        "depth_rank": depth_rank,
        "depth_range": depth_range,
        "return_period": None,  # A31b stores categories in separate folders
        "river_name": None,     # A31b does not include river name per feature
        "source_id": source_id,
        "prefecture": prefecture,
        "city": None,           # A31b does not include city per feature
    }


def _transform_a31(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Transform legacy A31 feature."""
    depth_rank = safe_int(resolve_attr(props, ATTR_A31["depth_rank"]), default=0)
    if depth_rank is None:
        depth_rank = 0
    depth_rank = max(0, min(5, depth_rank))

    depth_range = resolve_attr(props, ATTR_A31["depth_range"])
    if depth_range is None:
        depth_range = FLOOD_DEPTH_RANGE.get(depth_rank, "不明")

    return {
        "geom_json": geom_json,
        "depth_rank": depth_rank,
        "depth_range": str(depth_range),
        "return_period": safe_int(resolve_attr(props, ATTR_A31["return_period"])),
        "river_name": resolve_attr(props, ATTR_A31["river_name"]),
        "source_id": source_id,
        "prefecture": prefecture,
        "city": resolve_attr(props, ATTR_A31["city"]),
    }


def detect_format(input_dir: Path) -> str:
    """Detect A31b vs A31 based on filenames."""
    if any(input_dir.rglob("A31b-*.shp")):
        return "a31b"
    return "a31"


def main() -> None:
    parser = build_cli("Load flood inundation data (A31b / A31)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    fmt = detect_format(args.input_dir)
    logger.info("Detected format: %s", fmt)

    if fmt == "a31b":
        # A31b: use only 想定最大規模 (20_*) files by default
        file_patterns = ("A31b-20-*.shp",)
        source_name = "国土数値情報 洪水浸水想定区域データ (A31b 想定最大規模)"
        source_url = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31b.html"
        source_epsg = args.source_epsg if args.source_epsg != 4326 else 6668
    else:
        file_patterns = ("*.geojson", "*.shp")
        source_name = "国土数値情報 洪水浸水想定区域データ (A31)"
        source_url = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v3_1.html"
        source_epsg = args.source_epsg

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name=source_name,
        data_source_provider="国土交通省",
        data_source_url=source_url,
        input_dir=args.input_dir,
        prefecture=args.prefecture,
        source_epsg=source_epsg,
        clear_existing=not args.no_clear,
        batch_size=args.batch_size,
        file_patterns=file_patterns,
    )

    logger.info("Done — %d loaded, %d skipped", result.loaded, result.skipped)
    sys.exit(0 if result.loaded > 0 or result.quality.total_features == 0 else 1)


if __name__ == "__main__":
    main()
    sys.exit(0 if result.loaded > 0 or result.quality.total_features == 0 else 1)


if __name__ == "__main__":
    main()
