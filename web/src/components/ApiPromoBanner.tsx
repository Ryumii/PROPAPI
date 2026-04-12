import Link from "next/link";

export default function ApiPromoBanner() {
  return (
    <section className="rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 p-5 flex flex-col sm:flex-row items-center gap-4">
      <div className="flex-1 text-center sm:text-left">
        <h3 className="font-bold text-blue-800">
          API でシステム連携しませんか？
        </h3>
        <p className="text-sm text-blue-600 mt-1">
          不動産査定・物件情報サイトに PropAPI
          のハザード・用途地域データを組み込めます。月間 1,000
          リクエストまで無料。
        </p>
      </div>
      <Link
        href="/docs"
        className="shrink-0 inline-flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition"
      >
        API ドキュメント
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </Link>
    </section>
  );
}
