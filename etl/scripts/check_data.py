"""Prepare data directories and verify downloaded files for ETL."""

from __future__ import annotations

import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATASETS = {
    "flood": {
        "dir": DATA_DIR / "flood",
        "source": "A31 洪水浸水想定区域",
        "extensions": {".shp", ".dbf", ".shx"},
    },
    "landslide": {
        "dir": DATA_DIR / "landslide",
        "source": "A33 土砂災害警戒区域",
        "extensions": {".shp", ".dbf", ".shx"},
    },
    "tsunami": {
        "dir": DATA_DIR / "tsunami",
        "source": "A40 津波浸水想定",
        "extensions": {".shp", ".dbf", ".shx"},
    },
    "zoning": {
        "dir": DATA_DIR / "zoning",
        "source": "L03-b 用途地域",
        "extensions": {".shp", ".dbf", ".shx"},
    },
}


def main() -> None:
    print("=== REAPI ETL データ準備チェック ===\n")

    all_ready = True

    for name, cfg in DATASETS.items():
        d: Path = cfg["dir"]
        d.mkdir(parents=True, exist_ok=True)

        shp_files = list(d.glob("*.shp"))
        if shp_files:
            print(f"  ✓ {name:12s} ({cfg['source']})")
            for f in shp_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"      {f.name} ({size_mb:.1f} MB)")

            # Check companion files
            for shp in shp_files:
                for ext in cfg["extensions"] - {".shp"}:
                    companion = shp.with_suffix(ext)
                    if not companion.exists():
                        print(f"      ⚠ 不足: {companion.name}")
        else:
            print(f"  ✗ {name:12s} ({cfg['source']}) — データ未配置")
            print(f"      → {d}")
            all_ready = False

    print()
    if all_ready:
        print("全データセット準備完了。ETLローダーを実行できます。")
        print()
        print("実行例:")
        print("  python -m etl.scripts.load_flood --input-dir ./etl/data/flood")
        print("  python -m etl.scripts.load_landslide --input-dir ./etl/data/landslide")
        print("  python -m etl.scripts.load_tsunami --input-dir ./etl/data/tsunami")
        print("  python -m etl.scripts.load_zoning --input-dir ./etl/data/zoning")
    else:
        print("一部のデータが不足しています。")
        print("ダウンロード手順は etl/DATA_DOWNLOAD_GUIDE.md を参照してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()
