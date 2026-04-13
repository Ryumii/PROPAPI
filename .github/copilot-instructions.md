# PropAPI — Copilot Workspace Instructions

## ロードマップ更新ルール

タスクの実装・変更が完了したら、必ず `planning 1/実装ロードマップ.md` を更新すること:
- 完了したタスクのステータスを `✅` に変更
- 受入条件のチェックボックスを `[x]` に更新
- 進行中のタスクは `🔄進行中` に変更
- 実装した成果物パスが正しいか確認

## プロジェクト構成（マルチリポ）

### このリポ (Ryumii/PROPAPI) — API プラットフォーム
- `api/` — FastAPI バックエンド (Python 3.12)
- `etl/` — ETL スクリプト (GeoJSON/Shapefile → PostGIS)
- `sdk/` — Python / TypeScript SDK
- `infra/` — Terraform (Azure)
- `docker/` — Dockerfile群

### 別リポ (Ryumii/propapi-web) — コーポレートサイト
- Next.js 15 (App Router, Tailwind CSS)
- GitHub Pages (`propapi.jp`) にデプロイ
- PropAPI を外部 API として呼び出す（他ユーザーと同じ）

## デプロイ

- API: Docker → ACR (`crpropapid0c7e8ea.azurecr.io`) → Azure Container Apps
- Web: `Ryumii/propapi-web` の `main` push → GitHub Actions → GitHub Pages (`propapi.jp`)
- DB: Azure Database for PostgreSQL (PostGIS)
