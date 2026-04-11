# REAPI — 土地調査統合 API プラットフォーム

住所・緯度経度を入力するだけで、ハザードリスク・都市計画規制・用途地域を一括返却する日本初の土地調査統合 API。

## プロジェクト構成

```text
reapi/
├── api/          # FastAPI バックエンド（Python 3.12）
├── web/          # Next.js 15 フロントエンド
├── etl/          # データ ETL パイプライン（Airflow DAG + スクリプト）
├── sdk/          # クライアント SDK（Python / TypeScript）
├── infra/        # Terraform（Azure）
└── docker/       # Dockerfile 群
```

## クイックスタート

### 前提条件

- Docker & Docker Compose v2
- Python 3.12+
- Node.js 20+

### ローカル開発環境の起動

```bash
docker compose up -d

# API: http://localhost:8000
# Web: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### バックエンド開発

```bash
cd api
pip install -e ".[dev]"
pytest tests/ -v
```

### フロントエンド開発

```bash
cd web
npm ci
npm run dev
```

## 環境変数

`.env` ファイルをプロジェクトルートに作成してください（`.env.example` を参照）。

## ドキュメント

詳細なプランニングドキュメントは `planning/` フォルダ（Obsidian vault）を参照。

## ライセンス

Proprietary — All rights reserved.
