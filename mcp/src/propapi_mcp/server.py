"""PropAPI MCP Server — expose land inspection tools via MCP protocol."""

from __future__ import annotations

import json
import os
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

API_BASE = os.environ.get("PROPAPI_BASE_URL", "https://api.propapi.jp")
API_KEY = os.environ.get("PROPAPI_API_KEY", "")

server = Server("propapi-mcp")

_http: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(
            base_url=API_BASE,
            headers={
                "X-API-Key": API_KEY,
                "User-Agent": "propapi-mcp/0.1.0",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _http


# ── Tool definitions ──────────────────────────────────────


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="land_inspect",
            description=(
                "土地のハザードリスク（洪水・土砂災害・津波・液状化）と用途地域情報を"
                "住所または緯度経度から取得します。日本国内の不動産調査に使用します。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "調査対象の住所（例: 東京都渋谷区渋谷2-24-12）",
                    },
                    "lat": {
                        "type": "number",
                        "description": "緯度（20.0〜46.0）。address を指定しない場合は lat/lng 必須",
                    },
                    "lng": {
                        "type": "number",
                        "description": "経度（122.0〜154.0）。address を指定しない場合は lat/lng 必須",
                    },
                    "include_hazard": {
                        "type": "boolean",
                        "description": "ハザード情報を含めるか（デフォルト: true）",
                        "default": True,
                    },
                    "include_zoning": {
                        "type": "boolean",
                        "description": "用途地域情報を含めるか（デフォルト: true）",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="hazard_check",
            description=(
                "指定した緯度経度のハザードリスク情報のみを取得します。"
                "洪水・土砂災害・津波・液状化の各リスクレベルとスコアを返します。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "緯度（20.0〜46.0）",
                    },
                    "lng": {
                        "type": "number",
                        "description": "経度（122.0〜154.0）",
                    },
                },
                "required": ["lat", "lng"],
            },
        ),
        Tool(
            name="zoning_check",
            description=(
                "指定した緯度経度の用途地域情報のみを取得します。"
                "用途地域名、建ぺい率、容積率、防火地域等を返します。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "緯度（20.0〜46.0）",
                    },
                    "lng": {
                        "type": "number",
                        "description": "経度（122.0〜154.0）",
                    },
                },
                "required": ["lat", "lng"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    client = _get_client()

    try:
        if name == "land_inspect":
            body: dict = {
                "options": {
                    "include_hazard": arguments.get("include_hazard", True),
                    "include_zoning": arguments.get("include_zoning", True),
                },
            }
            if "address" in arguments:
                body["address"] = arguments["address"]
            if "lat" in arguments and "lng" in arguments:
                body["lat"] = arguments["lat"]
                body["lng"] = arguments["lng"]

            resp = await client.post("/v1/land/inspect", json=body)
            resp.raise_for_status()
            data = resp.json()
            return [TextContent(type="text", text=_format_inspect(data))]

        elif name == "hazard_check":
            resp = await client.get(
                "/v1/hazard",
                params={"lat": arguments["lat"], "lng": arguments["lng"]},
            )
            resp.raise_for_status()
            data = resp.json()
            return [TextContent(type="text", text=_format_hazard(data))]

        elif name == "zoning_check":
            resp = await client.get(
                "/v1/zoning",
                params={"lat": arguments["lat"], "lng": arguments["lng"]},
            )
            resp.raise_for_status()
            data = resp.json()
            return [TextContent(type="text", text=_format_zoning(data))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [
            TextContent(
                type="text",
                text=f"API Error ({e.response.status_code}): {e.response.text}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# ── Formatters ────────────────────────────────────────────


def _format_inspect(data: dict) -> str:
    lines = [f"# 土地調査結果"]
    if addr := data.get("address_normalized"):
        lines.append(f"**住所**: {addr}")
    loc = data.get("location", {})
    lines.append(f"**位置**: {loc.get('lat')}, {loc.get('lng')}")
    if loc.get("prefecture"):
        lines.append(f"**所在地**: {loc.get('prefecture')} {loc.get('city', '')} {loc.get('town', '')}")

    if hazard := data.get("hazard"):
        lines.append("")
        lines.append(_format_hazard(hazard))

    if zoning := data.get("zoning"):
        lines.append("")
        lines.append(_format_zoning(zoning))

    meta = data.get("meta", {})
    lines.append(f"\n---\n処理時間: {meta.get('processing_time_ms', '?')}ms | 信頼度: {meta.get('confidence', '?')}")
    return "\n".join(lines)


def _format_hazard(data: dict) -> str:
    lines = ["## ハザードリスク"]
    for key, label in [("flood", "洪水"), ("landslide", "土砂災害"), ("tsunami", "津波"), ("liquefaction", "液状化")]:
        d = data.get(key, {})
        level = d.get("risk_level", "N/A")
        score = d.get("risk_score", "N/A")
        lines.append(f"- **{label}**: {level} (スコア: {score})")
    comp = data.get("composite_score", {})
    lines.append(f"\n**総合リスク**: {comp.get('level', 'N/A')} (スコア: {comp.get('score', 'N/A')})")
    if desc := comp.get("description"):
        lines.append(f"  {desc}")
    return "\n".join(lines)


def _format_zoning(data: dict) -> str:
    lines = ["## 用途地域"]
    lines.append(f"- **用途地域**: {data.get('use_district', 'N/A')}")
    if cov := data.get("building_coverage_pct"):
        lines.append(f"- **建ぺい率**: {cov}%")
    if far := data.get("floor_area_ratio_pct"):
        lines.append(f"- **容積率**: {far}%")
    if fp := data.get("fire_prevention"):
        lines.append(f"- **防火地域**: {fp}")
    if hd := data.get("height_district"):
        lines.append(f"- **高度地区**: {hd}")
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────


async def _run() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    import asyncio

    if not API_KEY:
        print("Error: PROPAPI_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
