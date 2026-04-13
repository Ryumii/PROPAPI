# PropAPI — Copilot Workspace Instructions

## ロードマップ更新ルール

タスクの実装・変更が完了したら、必ず `planning 1/実装ロードマップ.md` を更新すること:
- 完了したタスクのステータスを `✅` に変更
- 受入条件のチェックボックスを `[x]` に更新
- 進行中のタスクは `🔄進行中` に変更
- 実装した成果物パスが正しいか確認

## プロジェクト構成

- `api/` — FastAPI バックエンド (Python 3.12)
- `web/` — Next.js 15 フロントエンド (App Router, Tailwind CSS)
- `etl/` — ETL スクリプト (GeoJSON/Shapefile → PostGIS)
- `sdk/` — Python / TypeScript SDK
- `infra/` — Terraform (Azure)
- `docker/` — Dockerfile群

## デプロイ

- API: Docker → ACR (`crpropapid0c7e8ea.azurecr.io`) → Azure Container Apps
- Web: GitHub Pages (`propapi.jp`) — `git push origin master` で GitHub Actions が自動デプロイ
- DB: Azure Database for PostgreSQL (PostGIS)
