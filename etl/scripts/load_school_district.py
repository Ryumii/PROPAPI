"""TASK-076: 公立小学校学区データ ETL.

Data source : 国土数値情報 A27 — 小学校区
Format      : GeoJSON / Shapefile (JGD2011)
Target table: school_district

A27 attributes (2023 version):
  A27_001: 市区町村コード (5桁)
  A27_002: 設置者名 (e.g. 新宿区立)
  A27_003: 学校コード
  A27_004: 学校名 (e.g. 戸塚第二小学校)
  A27_005: 所在地

Usage:
    python -m etl.scripts.load_school_district --input-dir ./etl/data/school_district
    python -m etl.scripts.load_school_district --input-dir ./etl/data/school_district --school-type junior_high
"""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path
from typing import Any

from etl.common.geo import resolve_attr
from etl.common.loader import build_cli, run_etl
from etl.config import PREF_CODE_MAP

logger = logging.getLogger(__name__)

TABLE = "school_district"

INSERT_SQL = (
    "INSERT INTO school_district "
    "(geom, school_type, school_name, school_code, administrator, address, "
    " source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_CollectionExtract(ST_MakeValid("
    "   ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)), 3)), "
    " :school_type, :school_name, :school_code, :administrator, :address, "
    " :source_id, :prefecture, :city)"
)

# A27 (elementary) attribute names
ATTR_A27 = {
    "city_code": ["A27_001", "市区町村コード", "CityCode"],
    "administrator": ["A27_002", "設置者名", "Administrator"],
    "school_code": ["A27_003", "学校コード", "SchoolCode"],
    "school_name": ["A27_004", "学校名", "SchoolName"],
    "address": ["A27_005", "所在地", "Address"],
}

# A32 (junior high) attribute names — same structure
ATTR_A32 = {
    "city_code": ["A32_001", "市区町村コード", "CityCode"],
    "administrator": ["A32_002", "設置者名", "Administrator"],
    "school_code": ["A32_003", "学校コード", "SchoolCode"],
    "school_name": ["A32_004", "学校名", "SchoolName"],
    "address": ["A32_005", "所在地", "Address"],
}

# School type label
_SCHOOL_TYPE_DEFAULT = "elementary"


def _get_attr_map(school_type: str) -> dict[str, list[str]]:
    """Return attribute map for the given school type."""
    if school_type == "junior_high":
        return ATTR_A32
    return ATTR_A27


# Global school_type set from CLI — used by transform_feature
_school_type: str = _SCHOOL_TYPE_DEFAULT


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single school district feature to a DB row dict."""
    attr = _get_attr_map(_school_type)

    school_name = resolve_attr(props, attr["school_name"])
    if not school_name:
        return None  # skip — school_name is required

    # Auto-detect prefecture from city code (first 2 digits)
    city_code = resolve_attr(props, attr["city_code"])
    detected_pref = prefecture  # fallback
    if city_code:
        pref_code = str(city_code).strip()[:2]
        detected_pref = PREF_CODE_MAP.get(pref_code, prefecture)

    # Extract city name from administrator (e.g. "新宿区立" → "新宿区")
    administrator = resolve_attr(props, attr["administrator"])
    city = None
    if administrator:
        # Remove 立 suffix to get city name
        city = administrator.rstrip("立") if administrator.endswith("立") else None

    return {
        "geom_json": geom_json,
        "school_type": _school_type,
        "school_name": str(school_name).strip(),
        "school_code": resolve_attr(props, attr["school_code"]),
        "administrator": administrator,
        "address": resolve_attr(props, attr["address"]),
        "source_id": source_id,
        "prefecture": detected_pref,
        "city": city,
    }


def _extract_zips(input_dir: Path) -> None:
    """Extract all .zip files in input_dir that haven't been extracted yet."""
    for zf in sorted(input_dir.glob("*.zip")):
        # Expected extracted file pattern: A27-23_XX.geojson or .shp
        stem = zf.stem  # e.g. A27-23_13_GML
        extract_dir = input_dir / stem
        if extract_dir.exists():
            continue
        logger.info("Extracting %s …", zf.name)
        with zipfile.ZipFile(zf, "r") as z:
            z.extractall(input_dir)


def main() -> None:
    global _school_type

    parser = build_cli("Load school district data (国土数値情報 A27/A32)")
    parser.add_argument(
        "--school-type",
        choices=["elementary", "junior_high"],
        default=_SCHOOL_TYPE_DEFAULT,
        help="School type: elementary (A27) or junior_high (A32)",
    )
    parser.add_argument(
        "--auto-extract",
        action="store_true",
        default=True,
        help="Automatically extract .zip files in input directory",
    )
    args = parser.parse_args()
    _school_type = args.school_type

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    # Auto-extract zips
    if args.auto_extract:
        _extract_zips(args.input_dir)

    # Data source info
    if _school_type == "junior_high":
        ds_name = "国土数値情報 中学校区データ (A32)"
        ds_url = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A32-v2_1.html"
    else:
        ds_name = "国土数値情報 小学校区データ (A27)"
        ds_url = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A27-v2_1.html"

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name=ds_name,
        data_source_provider="国土交通省 国土政策局",
        data_source_url=ds_url,
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
