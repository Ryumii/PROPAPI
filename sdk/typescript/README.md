# PropAPI TypeScript/JavaScript SDK

**PropAPI** — 日本の土地リスク調査 API の TypeScript/JavaScript クライアント。

## インストール

```bash
npm install propapi
```

## クイックスタート

```typescript
import { PropAPI } from "propapi";

const client = new PropAPI({ apiKey: "cs_live_..." });

// 住所で調査
const result = await client.inspect({ address: "東京都渋谷区渋谷2-24-12" });
console.log(`洪水リスク: ${result.hazard?.flood.risk_level}`);
console.log(`用途地域: ${result.zoning?.use_district}`);

// 緯度経度で調査
const result2 = await client.inspect({ lat: 35.6595, lng: 139.7004 });

// ハザードのみ
const hazard = await client.hazard({ lat: 35.6595, lng: 139.7004 });

// 用途地域のみ
const zoning = await client.zoning({ lat: 35.6595, lng: 139.7004 });
```

## エラーハンドリング

```typescript
import { PropAPI, AuthenticationError, RateLimitError, PropAPIError } from "propapi";

try {
  const result = await client.inspect({ address: "東京都渋谷区渋谷2-24-12" });
} catch (e) {
  if (e instanceof AuthenticationError) {
    console.error("API キーが無効です");
  } else if (e instanceof RateLimitError) {
    console.error(`レート制限 — ${e.retryAfter}秒後にリトライ`);
  } else if (e instanceof PropAPIError) {
    console.error(`API エラー: ${e.statusCode} ${e.message}`);
  }
}
```

## API

| メソッド | エンドポイント | 説明 |
|---|---|---|
| `client.inspect(params)` | `POST /v1/land/inspect` | ハザード＋用途地域の統合調査 |
| `client.hazard(params)` | `GET /v1/hazard` | ハザード情報のみ |
| `client.zoning(params)` | `GET /v1/zoning` | 用途地域情報のみ |
| `client.health()` | `GET /v1/health` | ヘルスチェック |

## ライセンス

MIT
