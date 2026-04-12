# PropAPI Python SDK

**PropAPI** — 日本の土地リスク調査 API の Python クライアント。

ハザードリスク（洪水・土砂災害・津波・液状化）と用途地域情報を住所または緯度経度から取得できます。

## インストール

```bash
pip install propapi
```

## クイックスタート

```python
from propapi import PropAPI

client = PropAPI(api_key="cs_live_...")

# 住所で調査
result = client.inspect(address="東京都渋谷区渋谷2-24-12")
print(f"洪水リスク: {result.hazard.flood.risk_level}")
print(f"用途地域: {result.zoning.use_district}")
print(f"総合スコア: {result.hazard.composite_score.score}")

# 緯度経度で調査
result = client.inspect(lat=35.6595, lng=139.7004)

# ハザードのみ
hazard = client.hazard(lat=35.6595, lng=139.7004)
print(f"洪水: {hazard.flood.risk_level}, 津波: {hazard.tsunami.risk_level}")

# 用途地域のみ
zoning = client.zoning(lat=35.6595, lng=139.7004)
print(f"{zoning.use_district} 建ぺい率{zoning.building_coverage_pct}%")
```

## 非同期クライアント

```python
import asyncio
from propapi import AsyncPropAPI

async def main():
    async with AsyncPropAPI(api_key="cs_live_...") as client:
        result = await client.inspect(address="東京都千代田区丸の内一丁目")
        print(result.hazard.composite_score.level)

asyncio.run(main())
```

## エラーハンドリング

```python
from propapi import PropAPI, PropAPIError, AuthenticationError, RateLimitError

client = PropAPI(api_key="cs_live_...")

try:
    result = client.inspect(address="東京都渋谷区渋谷2-24-12")
except AuthenticationError:
    print("API キーが無効です")
except RateLimitError as e:
    print(f"レート制限 — {e.retry_after}秒後にリトライ")
except PropAPIError as e:
    print(f"API エラー: {e.status_code} {e.message}")
```

## API リファレンス

| メソッド | エンドポイント | 説明 |
|---|---|---|
| `client.inspect(...)` | `POST /v1/land/inspect` | ハザード＋用途地域の統合調査 |
| `client.hazard(...)` | `GET /v1/hazard` | ハザード情報のみ |
| `client.zoning(...)` | `GET /v1/zoning` | 用途地域情報のみ |
| `client.health()` | `GET /v1/health` | ヘルスチェック |

## ライセンス

MIT
