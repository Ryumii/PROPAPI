"""TASK-015: 用途地域データ ETL (東京23区).

Data source : 国土数値情報 L03-b — 用途地域
Format      : GeoJSON or Shapefile  (EPSG:4326 or JGD2011)
Target table: zoning_district

Usage:
    python -m etl.scripts.load_zoning --input-dir ./etl/data/zoning
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from etl.common.geo import resolve_attr, safe_int
from etl.common.loader import build_cli, run_etl
from etl.config import FIRE_PREVENTION_MAP, USE_DISTRICT_MAP

logger = logging.getLogger(__name__)

TABLE = "zoning_district"

INSERT_SQL = (
    "INSERT INTO zoning_district "
    "(geom, use_district, use_code, coverage_pct, floor_ratio_pct, "
    " fire_prevention, fire_code, height_district, scenic_district, "
    " source_id, prefecture, city) "
    "VALUES ("
    " ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326)), "
    " :use_district, :use_code, :coverage_pct, :floor_ratio_pct, "
    " :fire_prevention, :fire_code, :height_district, :scenic_district, "
    " :source_id, :prefecture, :city)"
)

ATTR = {
    "use_code": [
        "L03b_001", "用途地域コード", "use_code", "UseCode",
        "用途地域", "L03b_002",
    ],
    "coverage_pct": [
        "L03b_003", "建ぺい率", "coverage_pct", "建蔽率",
        "CoveragePct", "L03b_002",
    ],
    "floor_ratio_pct": [
        "L03b_004", "容積率", "floor_ratio_pct", "FloorRatio",
        "L03b_003",
    ],
    "fire_code": [
        "L03b_005", "防火地域コード", "fire_code", "FireCode",
        "防火地域", "L03b_004",
    ],
    "height_district": [
        "L03b_006", "高度地区", "height_district", "HeightDistrict",
    ],
    "scenic_district": [
        "L03b_007", "風致地区", "scenic_district", "ScenicDistrict",
    ],
    "city": ["市区町村名", "city", "City", "市区町村"],
}


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single zoning feature to a DB row dict."""
    raw_use_code = resolve_attr(props, ATTR["use_code"])
    if raw_use_code is None:
        return None  # use_code is required

    use_code = str(raw_use_code).strip().zfill(2)
    use_district = USE_DISTRICT_MAP.get(use_code)
    if use_district is None:
        # Might be the full name already
        if str(raw_use_code) in USE_DISTRICT_MAP.values():
            use_district = str(raw_use_code)
            # Reverse lookup code
            for code, name in USE_DISTRICT_MAP.items():
                if name == use_district:
                    use_code = code
                    break
        else:
            logger.warning("Unknown use_code: %s — skipping", raw_use_code)
            return None

    raw_fire_code = resolve_attr(props, ATTR["fire_code"])
    fire_code = str(raw_fire_code).strip().zfill(2) if raw_fire_code else None
    fire_prevention = FIRE_PREVENTION_MAP.get(fire_code, None) if fire_code else None

    return {
        "geom_json": geom_json,
        "use_district": use_district,
        "use_code": use_code,
        "coverage_pct": safe_int(resolve_attr(props, ATTR["coverage_pct"])),
        "floor_ratio_pct": safe_int(resolve_attr(props, ATTR["floor_ratio_pct"])),
        "fire_prevention": fire_prevention,
        "fire_code": fire_code,
        "height_district": resolve_attr(props, ATTR["height_district"]),
        "scenic_district": resolve_attr(props, ATTR["scenic_district"]),
        "source_id": source_id,
        "prefecture": prefecture,
        "city": resolve_attr(props, ATTR["city"]),
    }


def main() -> None:
    parser = build_cli("Load zoning district data (国土数値情報 L03-b)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name="国土数値情報 用途地域データ (L03-b)",
        data_source_provider="国土交通省 国土政策局",
        data_source_url="https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b-v3_1.html",
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
