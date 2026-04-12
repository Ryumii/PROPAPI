import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "API ドキュメント | PropAPI",
  description:
    "PropAPI の REST API リファレンス。ハザードリスク・用途地域を住所から取得できます。",
};

export default function DocsPage() {
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <main className="min-h-screen bg-white">
      {/* header */}
      <header className="border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/" className="text-xl font-extrabold shrink-0">
            Prop<span className="text-blue-600">API</span>
          </Link>
          <h1 className="text-lg font-semibold text-gray-700">
            API ドキュメント
          </h1>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        {/* quick start */}
        <section className="rounded-xl border bg-gray-50 p-6 space-y-4">
          <h2 className="text-xl font-bold">クイックスタート</h2>
          <p className="text-sm text-gray-600">
            PropAPI を使えば、住所を指定するだけでハザードリスクと用途地域を取得できます。
          </p>

          <div className="bg-gray-900 text-gray-100 rounded-lg p-4 text-sm font-mono overflow-x-auto">
            <pre>{`curl -X POST ${apiBase}/v1/land/inspect \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{"address": "東京都渋谷区渋谷2-24-12"}'`}</pre>
          </div>
        </section>

        {/* endpoints table */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold">エンドポイント一覧</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-2 pr-4 font-semibold">メソッド</th>
                  <th className="py-2 pr-4 font-semibold">パス</th>
                  <th className="py-2 font-semibold">説明</th>
                </tr>
              </thead>
              <tbody className="text-gray-600">
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4">
                    <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">
                      POST
                    </span>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs">
                    /v1/land/inspect
                  </td>
                  <td className="py-2">
                    住所または緯度経度からハザード＋用途地域を一括取得
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4">
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-semibold">
                      GET
                    </span>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs">/v1/hazard</td>
                  <td className="py-2">ハザード情報のみ取得</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4">
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-semibold">
                      GET
                    </span>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs">/v1/zoning</td>
                  <td className="py-2">用途地域情報のみ取得</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="py-2 pr-4">
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-semibold">
                      GET
                    </span>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs">/v1/health</td>
                  <td className="py-2">ヘルスチェック</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* error codes */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold">エラーコード</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="py-2 pr-4 font-semibold">HTTP</th>
                  <th className="py-2 pr-4 font-semibold">コード</th>
                  <th className="py-2 font-semibold">説明</th>
                </tr>
              </thead>
              <tbody className="text-gray-600">
                {[
                  { http: 400, code: "INVALID_REQUEST", desc: "リクエストの形式が不正" },
                  { http: 400, code: "INVALID_ADDRESS", desc: "住所を解析できない" },
                  { http: 400, code: "INVALID_COORDINATES", desc: "座標が日本国内の範囲外" },
                  { http: 401, code: "UNAUTHORIZED", desc: "API Key が無効" },
                  { http: 403, code: "FORBIDDEN", desc: "アクセス権がない" },
                  { http: 404, code: "NOT_FOUND", desc: "該当住所のデータなし" },
                  { http: 429, code: "RATE_LIMITED", desc: "レートリミット超過" },
                  { http: 429, code: "QUOTA_EXCEEDED", desc: "月間上限超過" },
                  { http: 500, code: "INTERNAL_ERROR", desc: "サーバー内部エラー" },
                ].map((e) => (
                  <tr key={e.code} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-mono text-xs">{e.http}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{e.code}</td>
                    <td className="py-2">{e.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* interactive docs link */}
        <section className="rounded-xl border border-blue-100 bg-blue-50 p-6 text-center space-y-3">
          <h2 className="text-lg font-bold text-blue-800">
            インタラクティブ API ドキュメント
          </h2>
          <p className="text-sm text-blue-600">
            Swagger UI で全エンドポイントをブラウザから試行できます。
          </p>
          <a
            href={`${apiBase}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition"
          >
            Swagger UI を開く ↗
          </a>
        </section>

        {/* pricing */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold">料金プラン</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                name: "Free",
                price: "¥0",
                limit: "1,000 リクエスト/月",
                features: ["住所検索", "ハザード情報", "用途地域"],
              },
              {
                name: "Growth",
                price: "¥9,800/月",
                limit: "50,000 リクエスト/月",
                features: ["Free の全機能", "高速レスポンス", "メールサポート"],
              },
              {
                name: "Business",
                price: "¥49,800/月",
                limit: "500,000 リクエスト/月",
                features: [
                  "Growth の全機能",
                  "バッチ API",
                  "SLA 99.9%",
                  "専任サポート",
                ],
              },
            ].map((plan) => (
              <div
                key={plan.name}
                className="rounded-xl border bg-white p-5 space-y-3"
              >
                <h3 className="font-bold text-lg">{plan.name}</h3>
                <p className="text-2xl font-extrabold">{plan.price}</p>
                <p className="text-xs text-gray-500">{plan.limit}</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-1.5">
                      <span className="text-green-500">✓</span> {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <footer className="text-xs text-gray-400 pt-4 border-t border-gray-100">
          © {new Date().getFullYear()} PropAPI — 土地調査統合 API プラットフォーム
        </footer>
      </div>
    </main>
  );
}
