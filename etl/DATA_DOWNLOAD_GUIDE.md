# 国土数値情報 データダウンロードガイド

## 前提条件

### 1. Docker Desktop のインストール
PostGIS データベースを使用するため、Docker Desktop が必要です。

```
https://www.docker.com/products/docker-desktop/
```

インストール後:
```bash
docker compose up -d db redis
```

### 2. 国土数値情報 ダウンロードサービスへの登録
国土数値情報のダウンロードサービス（https://nlftp.mlit.go.jp/）は
登録制に移行しています。以下のフォームから利用登録を行ってください:

https://docs.google.com/forms/d/e/1FAIpQLSdber88pqhaLov4qTE1M9LGn_TD4hfx0DWuxrXWNFOUX_KOjw/viewform

---

## ダウンロード対象データ

以下の4種類のデータを東京都（都道府県コード 13）分ダウンロードしてください。
**Shapefile形式** を選択してください（GMLも可ですが、SHPを推奨）。

### A31: 洪水浸水想定区域
- URL: `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v3_1.html`
- 地域区分: **関東地方整備局** （東京都を含む）
- 形式: Shapefile
- 保存先: `etl/data/flood/`

### A33: 土砂災害警戒区域
- URL: `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A33-v1_3.html`
- 都道府県: **東京都** (13)
- 形式: Shapefile
- 保存先: `etl/data/landslide/`

### A40: 津波浸水想定
- URL: `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A40-v4_0.html`
- 都道府県: **東京都** (13)
- 形式: Shapefile
- 保存先: `etl/data/tsunami/`
- 注: 東京都（特に23区内陸部）にはデータが無い可能性があります

### L03-b: 用途地域
- URL: `https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L03-b-v3_1.html`
- 都道府県: **東京都** (13)
- 形式: Shapefile
- 保存先: `etl/data/zoning/`

---

## ディレクトリ構成

ダウンロードしたZIPファイルを展開し、以下の構成にしてください:

```
etl/data/
├── flood/           ← A31 洪水浸水想定区域
│   ├── *.shp
│   ├── *.dbf
│   ├── *.shx
│   └── *.prj
├── landslide/       ← A33 土砂災害警戒区域
│   ├── *.shp
│   ├── *.dbf
│   ├── *.shx
│   └── *.prj
├── tsunami/         ← A40 津波浸水想定
│   ├── *.shp
│   ├── *.dbf
│   ├── *.shx
│   └── *.prj
└── zoning/          ← L03-b 用途地域
    ├── *.shp
    ├── *.dbf
    ├── *.shx
    └── *.prj
```

---

## データロード手順

### 1. Docker起動
```bash
docker compose up -d db redis
```

### 2. DBマイグレーション
```bash
cd api
alembic upgrade head
```

### 3. ETLローダー実行

```bash
# 洪水浸水想定区域
python -m etl.scripts.load_flood --input-dir ./etl/data/flood

# 土砂災害警戒区域
python -m etl.scripts.load_landslide --input-dir ./etl/data/landslide

# 津波浸水想定
python -m etl.scripts.load_tsunami --input-dir ./etl/data/tsunami

# 用途地域
python -m etl.scripts.load_zoning --input-dir ./etl/data/zoning
```

### 4. データ検証

```sql
-- 各テーブルのレコード数確認
SELECT 'hazard_flood' AS tbl, COUNT(*) FROM hazard_flood
UNION ALL
SELECT 'hazard_landslide', COUNT(*) FROM hazard_landslide
UNION ALL
SELECT 'hazard_tsunami', COUNT(*) FROM hazard_tsunami
UNION ALL
SELECT 'zoning_district', COUNT(*) FROM zoning_district;

-- 空間クエリテスト（東京タワー付近）
SELECT * FROM hazard_flood
WHERE ST_Contains(geom, ST_SetSRID(ST_Point(139.7454, 35.6586), 4326))
LIMIT 1;
```
