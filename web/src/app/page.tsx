export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-4">REAPI</h1>
      <p className="text-lg text-gray-600 mb-8">
        土地調査統合 API プラットフォーム
      </p>
      <div className="w-full max-w-md">
        <input
          type="text"
          placeholder="住所を入力してください..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    </main>
  );
}
