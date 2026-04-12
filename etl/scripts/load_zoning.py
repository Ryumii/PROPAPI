"""TASK-015: 用途地域データ ETL.

Supports two data formats:
  - A55  : 都市計画決定GISデータ (令和6年〜)  — per-municipality SHP
  - L03-b: 国土数値情報 用途地域 (legacy)     — per-prefecture SHP

A55 structure:
  etl/data/zoning/A55-24_13000_SHP/A55-24_13000_SHP/A55-24_XXXXX_SHP/
      XXXXX_youto.shp   — 用途地域 (primary)
      XXXXX_bouka.shp   — 防火地域
      XXXXX_koudoti.shp  — 高度地区

Target table: zoning_district

Usage:
    python -m etl.scripts.load_zoning --input-dir ./etl/data/zoning
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from etl.common.geo import resolve_attr, safe_int
from etl.common.loader import build_cli, run_etl
from etl.config import (
    A55_FIRE_CODE_MAP,
    FIRE_PREVENTION_MAP,
    USE_DISTRICT_MAP,
)

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

# ── Attribute name candidates (L03-b legacy) ────────────────
ATTR_L03B = {
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

# ── Attribute name candidates (A55 format) ───────────────────
ATTR_A55 = {
    "use_code": ["YoutoCode", "YoutoName"],
    "coverage_pct": ["BCR"],
    "floor_ratio_pct": ["FAR"],
    "city": ["Cityname"],
    "prefecture": ["Pref"],
    "citycode": ["Citycode"],
}


def _normalise_use_code(raw: Any) -> tuple[str, str] | None:
    """Convert raw use code/name → (zero-padded code, district name) or None."""
    if raw is None:
        return None
    raw_str = str(raw).strip()

    # Numeric code (A55 provides int, L03-b provides str)
    try:
        code = str(int(raw_str)).zfill(2)
        district = USE_DISTRICT_MAP.get(code)
        if district:
            return code, district
    except (ValueError, TypeError):
        pass

    # Already a full name
    if raw_str in USE_DISTRICT_MAP.values():
        for code, name in USE_DISTRICT_MAP.items():
            if name == raw_str:
                return code, name
        return None  # unreachable

    return None


def _normalise_fire_code(raw: Any) -> tuple[str, str] | None:
    """Convert raw fire code → (normalised code, name) or None."""
    if raw is None:
        return None
    raw_str = str(raw).strip()

    # A55 format: AreaCode 24/25
    try:
        a55_code = int(raw_str)
        norm = A55_FIRE_CODE_MAP.get(a55_code)
        if norm:
            return norm, FIRE_PREVENTION_MAP[norm]
    except (ValueError, TypeError):
        pass

    # L03-b format: "01"/"02"
    code = raw_str.zfill(2)
    if code in FIRE_PREVENTION_MAP:
        return code, FIRE_PREVENTION_MAP[code]

    return None


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single zoning feature to a DB row dict.

    Auto-detects A55 vs L03-b attributes.
    """
    # Detect format: A55 has "YoutoCode", L03-b has "L03b_*"
    is_a55 = "YoutoCode" in props or "YoutoName" in props
    attr = ATTR_A55 if is_a55 else ATTR_L03B

    raw_use_code = resolve_attr(props, attr["use_code"])
    result = _normalise_use_code(raw_use_code)
    if result is None:
        return None
    use_code, use_district = result

    # Coverage / FAR
    coverage_pct = safe_int(resolve_attr(props, attr["coverage_pct"]))
    floor_ratio_pct = safe_int(resolve_attr(props, attr["floor_ratio_pct"]))

    # Fire prevention
    fire_result = None
    if is_a55:
        # A55 stores fire prevention in separate bouka file;
        # if merged props include AreaCode, use it
        fire_raw = resolve_attr(props, ["AreaCode", "AreaType"])
        fire_result = _normalise_fire_code(fire_raw)
    else:
        fire_raw = resolve_attr(props, attr["fire_code"])
        if fire_raw:
            fire_code_str = str(fire_raw).strip().zfill(2)
            fire_result = (fire_code_str, FIRE_PREVENTION_MAP.get(fire_code_str))

    fire_code = fire_result[0] if fire_result else None
    fire_prevention = fire_result[1] if fire_result else None

    # Height / scenic district
    if is_a55:
        height_district = resolve_attr(props, ["DistType", "DistCode"])
        scenic_district = None
    else:
        height_district = resolve_attr(props, attr.get("height_district", []))
        scenic_district = resolve_attr(props, attr.get("scenic_district", []))

    city = resolve_attr(props, attr["city"])

    return {
        "geom_json": geom_json,
        "use_district": use_district,
        "use_code": use_code,
        "coverage_pct": coverage_pct,
        "floor_ratio_pct": floor_ratio_pct,
        "fire_prevention": fire_prevention,
        "fire_code": fire_code,
        "height_district": height_district,
        "scenic_district": scenic_district,
        "source_id": source_id,
        "prefecture": prefecture,
        "city": city,
    }


def find_a55_youto_files(input_dir: Path) -> list[Path]:
    """Recursively find all *_youto.shp files under an A55 directory tree."""
    return sorted(input_dir.rglob("*_youto.shp"))


def detect_format(input_dir: Path) -> str:
    """Detect A55 vs L03-b based on directory contents."""
    if any(input_dir.rglob("*_youto.shp")):
        return "a55"
    return "l03b"


def main() -> None:
    parser = build_cli("Load zoning district data (A55 / L03-b)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    fmt = detect_format(args.input_dir)
    logger.info("Detected format: %s", fmt)

    if fmt == "a55":
        # A55: use recursive glob for *_youto.shp
        file_patterns = ("*_youto.shp",)
        source_name = "都市計画決定GISデータ (A55)"
        source_url = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A55.html"
        # A55 is always JGD2011
        source_epsg = args.source_epsg if args.source_epsg != 4326 else 6668
    else:
        file_patterns = ("*.geojson", "*.shp")
        source_name = "国土数値情報 用途地域データ (L03-b)"
        source_url = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b-v3_1.html"
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
