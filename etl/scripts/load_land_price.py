"""ETL: 公示地価データ (L01) ローダー.

国土数値情報 地価公示データ (L01) の GeoJSON/Shapefile を読み込んで
land_price テーブルにロードする。

データ形式: Point (WGS84)
主要属性:
  L01_007: 調査年
  L01_008: 公示価格 (円/m²)
  L01_009: 前年変動率 (%)
  L01_025: 所在地
  L01_026: 住居表示
  L01_027: 地積 (m²)
  L01_028: 利用現況
  L01_031: 建物構造
  L01_047: 周辺の土地利用状況
  L01_048: 最寄駅
  L01_050: 駅距離 (m)
  L01_051: 用途地域
  L01_057: 建ぺい率 (%)
  L01_058: 容積率 (%)

Usage:
    python -m etl.scripts.load_land_price --input-dir ./etl/data/price
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from etl.common.geo import resolve_attr, safe_int
from etl.common.loader import build_cli, run_etl

logger = logging.getLogger(__name__)

TABLE = "land_price"

INSERT_SQL = (
    "INSERT INTO land_price "
    "(geom, price_per_sqm, year, yoy_change_pct, land_use, "
    " address, address_short, area_sqm, structure, "
    " nearest_station, station_distance_m, "
    " zoning_name, building_coverage_pct, floor_area_ratio_pct, "
    " neighborhood_desc, source_id, prefecture, city) "
    "VALUES ("
    " ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), 4326), "
    " :price_per_sqm, :year, :yoy_change_pct, :land_use, "
    " :address, :address_short, :area_sqm, :structure, "
    " :nearest_station, :station_distance_m, "
    " :zoning_name, :building_coverage_pct, :floor_area_ratio_pct, "
    " :neighborhood_desc, :source_id, :prefecture, :city)"
)

# Prefecture code → name mapping (first 2 digits of L01_001/L01_004)
PREF_CODE_MAP = {
    "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県",
    "05": "秋田県", "06": "山形県", "07": "福島県", "08": "茨城県",
    "09": "栃木県", "10": "群馬県", "11": "埼玉県", "12": "千葉県",
    "13": "東京都", "14": "神奈川県", "15": "新潟県", "16": "富山県",
    "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県",
    "25": "滋賀県", "26": "京都府", "27": "大阪府", "28": "兵庫県",
    "29": "奈良県", "30": "和歌山県", "31": "鳥取県", "32": "島根県",
    "33": "岡山県", "34": "広島県", "35": "山口県", "36": "徳島県",
    "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県",
    "45": "宮崎県", "46": "鹿児島県", "47": "沖縄県",
}


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        val = float(v)
        return val if val != 0 else None
    except (ValueError, TypeError):
        return None


def _clean_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().replace("\u3000", " ")
    return s if s and s != "_" else None


def _extract_prefecture(props: dict[str, Any]) -> str:
    """Extract prefecture name from city code (L01_001 or L01_004)."""
    code = str(resolve_attr(props, ["L01_001", "L01_004"]) or "")
    pref_code = code[:2] if len(code) >= 2 else ""
    return PREF_CODE_MAP.get(pref_code, "")


def transform_feature(
    geom_json: str,
    props: dict[str, Any],
    source_id: int,
    prefecture: str,
) -> dict[str, Any] | None:
    """Map a single L01 feature to a DB row."""
    price = safe_int(resolve_attr(props, ["L01_008"]))
    if not price or price <= 0:
        return None

    year = safe_int(resolve_attr(props, ["L01_007"]))
    if not year:
        return None

    yoy = _safe_float(resolve_attr(props, ["L01_009"]))
    address = _clean_str(resolve_attr(props, ["L01_025"]))
    address_short = _clean_str(resolve_attr(props, ["L01_026"]))

    # Extract prefecture/city from address
    pref = _extract_prefecture(props)
    city = None
    if address and pref and address.startswith(pref):
        rest = address[len(pref):].strip()
        # City name is typically up to 市/区/町/村/郡
        for sep in ["市", "区", "町", "村"]:
            idx = rest.find(sep)
            if idx >= 0:
                city = rest[:idx + 1]
                break

    return {
        "geom_json": geom_json,
        "price_per_sqm": price,
        "year": year,
        "yoy_change_pct": yoy,
        "land_use": _clean_str(resolve_attr(props, ["L01_028"])),
        "address": address,
        "address_short": address_short,
        "area_sqm": safe_int(resolve_attr(props, ["L01_027"])),
        "structure": _clean_str(resolve_attr(props, ["L01_031"])),
        "nearest_station": _clean_str(resolve_attr(props, ["L01_048"])),
        "station_distance_m": safe_int(resolve_attr(props, ["L01_050"])),
        "zoning_name": _clean_str(resolve_attr(props, ["L01_051"])),
        "building_coverage_pct": safe_int(resolve_attr(props, ["L01_057"])),
        "floor_area_ratio_pct": safe_int(resolve_attr(props, ["L01_058"])),
        "neighborhood_desc": _clean_str(resolve_attr(props, ["L01_047"])),
        "source_id": source_id,
        "prefecture": pref or prefecture,
        "city": city,
    }


def main() -> None:
    parser = build_cli("Load land price data (L01 公示地価)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    # Land price is 全国 (nationwide) data — clear all rows, not per-prefecture.
    # run_etl's clear_existing uses WHERE prefecture=:pref which wouldn't clear everything.
    if not args.no_clear:
        from etl.common.db import get_session as get_sync_session
        from sqlalchemy import text as sa_text

        with get_sync_session() as session:
            result = session.execute(sa_text(f"DELETE FROM {TABLE}"))  # noqa: S608
            count = result.rowcount
            session.commit()
            logger.info("Cleared %d rows from %s (all prefectures)", count, TABLE)

    result = run_etl(
        table_name=TABLE,
        insert_sql=INSERT_SQL,
        transform_fn=transform_feature,
        data_source_name="国土数値情報 地価公示データ (L01)",
        data_source_provider="国土交通省",
        data_source_url="https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-v3_1.html",
        input_dir=args.input_dir,
        prefecture="全国",
        source_epsg=args.source_epsg,
        clear_existing=False,  # handled above
        batch_size=args.batch_size,
        file_patterns=("*.geojson",),
    )

    logger.info("Done — %d loaded, %d skipped", result.loaded, result.skipped)
    sys.exit(0 if result.loaded > 0 or result.quality.total_features == 0 else 1)


if __name__ == "__main__":
    main()
