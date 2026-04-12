"""ETL pipeline configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Directories ──────────────────────────────────────────────
ETL_ROOT = Path(__file__).resolve().parent
DATA_DIR = ETL_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Database (sync psycopg2) ─────────────────────────────────
_raw_url = os.getenv(
    "DATABASE_URL_SYNC",
    os.getenv("DATABASE_URL", "postgresql://reapi:changeme_local_only@localhost:5432/reapi"),
)
# Ensure we always use a sync driver (strip asyncpg if present)
DATABASE_URL = _raw_url.replace("postgresql+asyncpg://", "postgresql://") if "+asyncpg" in _raw_url else _raw_url

# ── Batch processing ─────────────────────────────────────────
BATCH_SIZE = 1000

# ── Tokyo 23 wards (MVP scope) ───────────────────────────────
TOKYO_PREF_CODE = "13"
TOKYO_PREF_NAME = "東京都"
TOKYO_23_WARDS: dict[str, str] = {
    "13101": "千代田区",
    "13102": "中央区",
    "13103": "港区",
    "13104": "新宿区",
    "13105": "文京区",
    "13106": "台東区",
    "13107": "墨田区",
    "13108": "江東区",
    "13109": "品川区",
    "13110": "目黒区",
    "13111": "大田区",
    "13112": "世田谷区",
    "13113": "渋谷区",
    "13114": "中野区",
    "13115": "杉並区",
    "13116": "豊島区",
    "13117": "北区",
    "13118": "荒川区",
    "13119": "板橋区",
    "13120": "練馬区",
    "13121": "足立区",
    "13122": "葛飾区",
    "13123": "江戸川区",
}

# ── Flood depth rank mapping ─────────────────────────────────
# A31 (legacy): ranks 0-5
FLOOD_DEPTH_RANGE: dict[int, str] = {
    0: "浸水なし",
    1: "0.5m未満",
    2: "0.5m以上3m未満",
    3: "3m以上5m未満",
    4: "5m以上10m未満",
    5: "10m以上",
}

# A31b (2024〜): ranks 1-6
A31B_DEPTH_RANGE: dict[int, str] = {
    1: "0.5m未満",
    2: "0.5m以上3m未満",
    3: "3m以上5m未満",
    4: "5m以上10m未満",
    5: "10m以上20m未満",
    6: "20m以上",
}

# A31b rank → normalised rank (0-5 scale for scoring)
A31B_TO_NORMALISED_RANK: dict[int, int] = {
    1: 1,  # 0.5m未満
    2: 2,  # 0.5m以上3m未満
    3: 3,  # 3m以上5m未満
    4: 4,  # 5m以上10m未満
    5: 5,  # 10m以上20m未満
    6: 5,  # 20m以上 → clamp to 5
}

# ── Tsunami depth range string → numeric depth_m ─────────────
TSUNAMI_DEPTH_RANGE_MAP: dict[str, float] = {
    "～0.3m未満": 0.15,
    "0.3m以上 ～ 0.5m未満": 0.4,
    "0.3m以上～0.5m未満": 0.4,
    "0.5m以上 ～ 1m未満": 0.75,
    "0.5m以上～1m未満": 0.75,
    "1m以上 ～ 3m未満": 2.0,
    "1m以上～3m未満": 2.0,
    "3m以上 ～ 5m未満": 4.0,
    "3m以上～5m未満": 4.0,
    "5m以上 ～ 10m未満": 7.5,
    "5m以上～10m未満": 7.5,
    "10m以上 ～ 20m未満": 15.0,
    "10m以上～20m未満": 15.0,
    "20m以上": 25.0,
}

# ── Landslide zone type mapping ──────────────────────────────
LANDSLIDE_ZONE_TYPE_MAP: dict[str, str] = {
    "1": "警戒区域",
    "2": "特別警戒区域",
    "3": "基礎調査完了",
    "警戒区域": "警戒区域",
    "特別警戒区域": "特別警戒区域",
    "基礎調査完了": "基礎調査完了",
}

# ── Zoning use district codes ────────────────────────────────
USE_DISTRICT_MAP: dict[str, str] = {
    "01": "第一種低層住居専用地域",
    "02": "第二種低層住居専用地域",
    "03": "第一種中高層住居専用地域",
    "04": "第二種中高層住居専用地域",
    "05": "第一種住居地域",
    "06": "第二種住居地域",
    "07": "準住居地域",
    "08": "田園住居地域",
    "09": "近隣商業地域",
    "10": "商業地域",
    "11": "準工業地域",
    "12": "工業地域",
    "13": "工業専用地域",
}

# ── Fire prevention codes ────────────────────────────────────
FIRE_PREVENTION_MAP: dict[str, str] = {
    "01": "防火地域",
    "02": "準防火地域",
}

# A55 (都市計画決定GIS) fire prevention code → normalised code
A55_FIRE_CODE_MAP: dict[int, str] = {
    24: "01",  # 防火地域
    25: "02",  # 準防火地域
}

# ── Bounding box for Japan (lon_min, lat_min, lon_max, lat_max) ──
JAPAN_BBOX = (122.0, 20.0, 154.0, 46.0)
TOKYO_BBOX = (138.9, 35.5, 140.0, 35.9)
