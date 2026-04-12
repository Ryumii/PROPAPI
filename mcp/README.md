# PropAPI MCP Server

PropAPI の土地リスク調査 API を [Model Context Protocol](https://modelcontextprotocol.io/) で公開するサーバーです。  
Claude Desktop や MCP 対応 AI ツールから直接、土地のハザードリスクと用途地域情報を調査できます。

## セットアップ

### 1. インストール

```bash
cd mcp
pip install -e .
```

### 2. Claude Desktop に登録

`claude_desktop_config.json` に以下を追加:

```json
{
  "mcpServers": {
    "propapi": {
      "command": "propapi-mcp",
      "env": {
        "PROPAPI_API_KEY": "cs_live_..."
      }
    }
  }
}
```

### 3. 使い方

Claude Desktop で以下のように質問するだけで、自動的に API が呼ばれます:

- 「東京都渋谷区渋谷2-24-12 の災害リスクを調べて」
- 「緯度35.66、経度139.70のハザード情報を教えて」
- 「丸の内の用途地域と容積率を確認して」

## 提供ツール

| ツール名 | 説明 |
|---|---|
| `land_inspect` | ハザード + 用途地域の統合調査 |
| `hazard_check` | ハザードリスクのみ |
| `zoning_check` | 用途地域情報のみ |

## 環境変数

| 変数名 | 必須 | 説明 |
|---|---|---|
| `PROPAPI_API_KEY` | ✅ | PropAPI の API キー |
| `PROPAPI_BASE_URL` | - | API ベース URL（デフォルト: `https://api.propapi.jp`） |
