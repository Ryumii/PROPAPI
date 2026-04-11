# ChiScan — API 仕様書

**Version 1.0** | 2026年4月  
関連: [[ユーザーストーリー]] | [[システムアーキテクチャ]] | [[実装ロードマップ]]

---

## 1. 概要

- **Base URL**: `https://api.reapi.jp/v1`
- **プロトコル**: HTTPS のみ（HTTP はリダイレクト）
- **認証**: API Key（`X-API-Key` ヘッダー）
- **Content-Type**: `application/json`
- **文字コード**: UTF-8
- **バージョニング**: URL パスに含める（`/v1/`）

---

## 2. 認証

### 2.1 API Key

すべてのリクエストに `X-API-Key` ヘッダーが必要。

```http
GET /v1/hazard?address=東京都渋谷区渋谷2-24-12 HTTP/1.1
Host: api.reapi.jp
X-API-Key: cs_live_xxxxxxxxxxxxxxxxxxxx
```

### 2.2 API Key の形式

| 環境 | プレフィックス | 例 |
|---|---|---|
| Production | `cs_live_` | `cs_live_a1b2c3d4e5f6g7h8i9j0` |
| Sandbox | `cs_test_` | `cs_test_a1b2c3d4e5f6g7h8i9j0` |

### 2.3 レート制限

| プラン | 月間上限 | 秒間レート | バースト |
|---|---|---|---|
| Starter | 1,000 | 10 req/s | 20 |
| Growth | 50,000 | 50 req/s | 100 |
| Business | 500,000 | 200 req/s | 400 |
| Enterprise | カスタム | カスタム | カスタム |

**レート制限ヘッダー**:

```http
X-RateLimit-Limit: 50000
X-RateLimit-Remaining: 49235
X-RateLimit-Reset: 2026-05-01T00:00:00Z
```

---

## 3. エンドポイント

### 3.1 `POST /v1/land/inspect` — 土地調査統合

住所または緯度経度からハザードリスク・用途地域を一括取得する。

#### リクエスト

```json
{
  "address": "東京都渋谷区渋谷2-24-12",
  "lat": 35.6595,
  "lng": 139.7004,
  "options": {
    "include_hazard": true,
    "include_zoning": true
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `address` | string | △ | 日本語住所。`lat`/`lng` と少なくとも一方が必要 |
| `lat` | number | △ | 緯度（WGS84）。`address` と少なくとも一方が必要 |
| `lng` | number | △ | 経度（WGS84）。`lat` と必ずセット |
| `options.include_hazard` | boolean | × | ハザード情報を含めるか（デフォルト: true） |
| `options.include_zoning` | boolean | × | 用途地域を含めるか（デフォルト: true） |

#### レスポンス（200 OK）

```json
{
  "request_id": "req_abc123def456",
  "address_normalized": "東京都渋谷区渋谷二丁目24番12号",
  "location": {
    "lat": 35.6595,
    "lng": 139.7004,
    "prefecture": "東京都",
    "city": "渋谷区",
    "town": "渋谷二丁目"
  },
  "hazard": {
    "flood": {
      "risk_level": "low",
      "risk_score": 2,
      "depth_m": 0.5,
      "depth_range": "0.0m〜0.5m",
      "return_period_years": 1000,
      "source": "国土交通省 洪水浸水想定区域図",
      "source_updated_at": "2024-06-01"
    },
    "landslide": {
      "risk_level": "none",
      "risk_score": 0,
      "zone_type": null,
      "source": "国土交通省 土砂災害警戒区域",
      "source_updated_at": "2024-03-01"
    },
    "tsunami": {
      "risk_level": "none",
      "risk_score": 0,
      "depth_m": null,
      "source": "内閣府 津波浸水想定",
      "source_updated_at": "2023-09-01"
    },
    "liquefaction": {
      "risk_level": "medium",
      "risk_score": 3,
      "pl_value": 12.5,
      "source": "東京都 液状化予測図",
      "source_updated_at": "2022-04-01"
    },
    "composite_score": {
      "score": 2.1,
      "level": "low",
      "description": "総合的なリスクは低めです"
    }
  },
  "zoning": {
    "use_district": "商業地域",
    "use_district_code": "09",
    "building_coverage_pct": 80,
    "floor_area_ratio_pct": 600,
    "fire_prevention": "防火地域",
    "fire_prevention_code": "01",
    "height_district": "第三種高度地区",
    "scenic_district": null,
    "source": "国土数値情報 用途地域データ",
    "source_updated_at": "2024-01-01"
  },
  "meta": {
    "data_updated_at": "2025-09-01",
    "confidence": 0.97,
    "geocoding_method": "address_match",
    "processing_time_ms": 142,
    "api_version": "1.0.0"
  }
}
```

#### リスクレベル定義

| risk_level | risk_score | 意味 |
|---|---|---|
| `none` | 0 | リスクなし（区域外） |
| `very_low` | 1 | 極めて低い |
| `low` | 2 | 低い |
| `medium` | 3 | 中程度 |
| `high` | 4 | 高い |
| `very_high` | 5 | 非常に高い |

#### 用途地域コード

| コード | 用途地域 |
|---|---|
| 01 | 第一種低層住居専用地域 |
| 02 | 第二種低層住居専用地域 |
| 03 | 第一種中高層住居専用地域 |
| 04 | 第二種中高層住居専用地域 |
| 05 | 第一種住居地域 |
| 06 | 第二種住居地域 |
| 07 | 準住居地域 |
| 08 | 田園住居地域 |
| 09 | 近隣商業地域 |
| 10 | 商業地域 |
| 11 | 準工業地域 |
| 12 | 工業地域 |
| 13 | 工業専用地域 |

---

### 3.2 `GET /v1/hazard` — ハザード情報のみ

#### リクエスト

```http
GET /v1/hazard?address=東京都渋谷区渋谷2-24-12 HTTP/1.1
```

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `address` | string | △ | 日本語住所 |
| `lat` | number | △ | 緯度 |
| `lng` | number | △ | 経度 |
| `types` | string | × | カンマ区切りで絞り込み（例: `flood,tsunami`） |

#### レスポンス（200 OK）

`POST /v1/land/inspect` の `hazard` セクションと同一構造。`zoning` は含まれない。

---

### 3.3 `GET /v1/zoning` — 用途地域のみ

#### リクエスト

```http
GET /v1/zoning?address=東京都渋谷区渋谷2-24-12 HTTP/1.1
```

#### レスポンス（200 OK）

`POST /v1/land/inspect` の `zoning` セクションと同一構造。`hazard` は含まれない。

---

### 3.4 `POST /v1/batch` — バッチ処理（Phase 2）

#### リクエスト

```json
{
  "items": [
    { "id": "item_001", "address": "東京都渋谷区渋谷2-24-12" },
    { "id": "item_002", "lat": 35.6812, "lng": 139.7671 },
    { "id": "item_003", "address": "大阪市北区梅田1-1-1" }
  ],
  "webhook_url": "https://example.com/webhook/chiscan",
  "options": {
    "include_hazard": true,
    "include_zoning": true
  }
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `items` | array | ✅ | 最大 1,000 件 |
| `items[].id` | string | ✅ | クライアント側の識別子 |
| `webhook_url` | string | × | 完了時の通知先 |

#### レスポンス（202 Accepted）

```json
{
  "job_id": "job_xyz789",
  "status": "processing",
  "total_items": 3,
  "estimated_completion_seconds": 15,
  "status_url": "https://api.reapi.jp/v1/batch/job_xyz789"
}
```

#### ジョブステータス確認: `GET /v1/batch/{job_id}`

```json
{
  "job_id": "job_xyz789",
  "status": "completed",
  "total_items": 3,
  "completed_items": 3,
  "failed_items": 0,
  "results": [
    { "id": "item_001", "status": "success", "data": { /* land/inspect と同じ */ } },
    { "id": "item_002", "status": "success", "data": { /* ... */ } },
    { "id": "item_003", "status": "success", "data": { /* ... */ } }
  ],
  "created_at": "2026-04-11T10:00:00Z",
  "completed_at": "2026-04-11T10:00:12Z"
}
```

---

### 3.5 `GET /v1/change-log` — データ更新履歴（Phase 2）

```http
GET /v1/change-log?address=東京都渋谷区渋谷2-24-12&since=2025-01-01 HTTP/1.1
```

#### レスポンス

```json
{
  "address_normalized": "東京都渋谷区渋谷二丁目24番12号",
  "changes": [
    {
      "changed_at": "2025-09-01",
      "category": "hazard.flood",
      "field": "depth_m",
      "old_value": "0.3",
      "new_value": "0.5",
      "source": "国土交通省 洪水浸水想定区域図 2025年改定"
    }
  ]
}
```

---

## 4. エラーレスポンス

### 4.1 共通エラー形式

```json
{
  "error": {
    "code": "INVALID_ADDRESS",
    "message": "指定された住所が見つかりませんでした",
    "details": "住所を確認してください。緯度経度での検索もお試しください。",
    "request_id": "req_abc123def456"
  }
}
```

### 4.2 エラーコード一覧

| HTTP Status | code | 意味 |
|---|---|---|
| 400 | `INVALID_REQUEST` | リクエストが不正 |
| 400 | `INVALID_ADDRESS` | 住所のパースに失敗 |
| 400 | `INVALID_COORDINATES` | 緯度経度が日本国外 |
| 400 | `MISSING_LOCATION` | 住所も緯度経度も未指定 |
| 401 | `UNAUTHORIZED` | API Key が未指定 |
| 403 | `FORBIDDEN` | API Key が無効または権限不足 |
| 404 | `NOT_FOUND` | 該当データなし（カバレッジ外） |
| 429 | `RATE_LIMITED` | レート制限超過 |
| 429 | `QUOTA_EXCEEDED` | 月間上限超過 |
| 500 | `INTERNAL_ERROR` | サーバー内部エラー |
| 503 | `SERVICE_UNAVAILABLE` | メンテナンス中 |

---

## 5. Webhook（Phase 2）

バッチ処理完了時にPOST通知を送信。

```json
{
  "event": "batch.completed",
  "job_id": "job_xyz789",
  "status": "completed",
  "total_items": 1000,
  "completed_items": 998,
  "failed_items": 2,
  "timestamp": "2026-04-11T10:05:00Z"
}
```

Webhook には HMAC-SHA256 署名を付与:

```http
X-ChiScan-Signature: sha256=xxxxxxxxxxxxxxxx
```

---

## 6. SDK（計画）

| 言語 | パッケージ名 | Phase |
|---|---|---|
| Python | `chiscan-python` | MVP |
| JavaScript/TypeScript | `@chiscan/sdk` | MVP |
| Ruby | `chiscan-ruby` | Phase 2 |
| Go | `chiscan-go` | Phase 2 |

### Python SDK 使用例

```python
from chiscan import ChiScan

client = ChiScan(api_key="cs_live_xxx")

# 住所で検索
result = client.inspect(address="東京都渋谷区渋谷2-24-12")
print(result.hazard.flood.risk_level)  # "low"
print(result.zoning.use_district)      # "商業地域"

# 緯度経度で検索
result = client.inspect(lat=35.6595, lng=139.7004)

# ハザードのみ
hazard = client.hazard(address="東京都渋谷区渋谷2-24-12")

# バッチ
job = client.batch([
    {"id": "1", "address": "東京都渋谷区渋谷2-24-12"},
    {"id": "2", "address": "大阪市北区梅田1-1-1"},
])
results = job.wait()  # 完了まで待機
```

---

## 7. ヘルスチェック

### `GET /v1/health`

認証不要。サービスの稼働状態を返す。

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "database": "connected",
  "cache": "connected"
}
```

---

## 変更履歴

| 日付 | API Version | 変更内容 |
|---|---|---|
| 2026-04-11 | 1.0.0 | 初版 |

---

*© 2026 ChiScan — Confidential & Proprietary*
