import SearchForm from "@/components/SearchForm";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-b from-white to-gray-50">
      <div className="text-center mb-10">
        <h1 className="text-5xl font-extrabold tracking-tight mb-3">
          Prop<span className="text-blue-600">API</span>
        </h1>
        <p className="text-xl text-gray-500">
          土地調査統合 API プラットフォーム
        </p>
        <p className="mt-2 text-sm text-gray-400">
          ハザードリスク・用途地域を一括検索
        </p>
      </div>

      <div className="w-full max-w-xl">
        <SearchForm />
      </div>

      <section className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-3xl text-center">
        <div>
          <h3 className="font-semibold text-lg mb-1">ハザードリスク</h3>
          <p className="text-sm text-gray-500">
            洪水・土砂・津波・液状化を一括判定
          </p>
        </div>
        <div>
          <h3 className="font-semibold text-lg mb-1">用途地域</h3>
          <p className="text-sm text-gray-500">
            建ぺい率・容積率・防火地域を取得
          </p>
        </div>
        <div>
          <h3 className="font-semibold text-lg mb-1">API 連携</h3>
          <p className="text-sm text-gray-500">
            REST API / SDK でシステム統合
          </p>
        </div>
      </section>

      <footer className="mt-24 text-xs text-gray-400">
        データ出典: 国土数値情報（国土交通省）/ アドレス・ベース・レジストリ（デジタル庁）
      </footer>
    </main>
  );
}
