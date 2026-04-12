import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";

import { TOKYO_WARDS, findWard } from "@/lib/wards";
import SearchForm from "@/components/SearchForm";

/* ── SSG: generate all ward pages at build time ── */

export function generateStaticParams() {
  return TOKYO_WARDS.map((w) => ({
    prefecture: w.prefectureSlug,
    city: w.citySlug,
  }));
}

/* ── dynamic metadata ── */

type Props = { params: Promise<{ prefecture: string; city: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { prefecture, city } = await params;
  const ward = findWard(prefecture, city);
  if (!ward) return {};

  const title = `${ward.city}のハザードマップ・用途地域情報 | PropAPI`;
  const description = `${ward.prefecture}${ward.city}の洪水・土砂災害・津波・液状化リスクと用途地域を一括確認。PropAPIで無料検索。`;

  return {
    title,
    description,
    openGraph: { title, description },
  };
}

/* ── page component ── */

export default async function AreaPage({ params }: Props) {
  const { prefecture, city } = await params;
  const ward = findWard(prefecture, city);
  if (!ward) notFound();

  // Neighbouring wards (same prefecture, excluding self)
  const neighbours = TOKYO_WARDS.filter(
    (w) => w.prefectureSlug === ward.prefectureSlug && w.citySlug !== ward.citySlug,
  );

  return (
    <main className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* header */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-gray-100">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link href="/" className="text-xl font-extrabold shrink-0">
            Prop<span className="text-blue-600">API</span>
          </Link>
          <div className="flex-1">
            <SearchForm compact defaultValue={`${ward.prefecture}${ward.city}`} />
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
        {/* hero */}
        <section>
          <h1 className="text-3xl font-extrabold mb-2">
            {ward.city}のハザードマップ情報
          </h1>
          <p className="text-gray-500">
            {ward.prefecture}{ward.city}
            の自然災害リスク（洪水・土砂災害・津波・液状化）と都市計画情報（用途地域・建ぺい率・容積率）を確認できます。
          </p>
        </section>

        {/* hazard overview cards */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { icon: "🌊", label: "洪水リスク", desc: "浸水想定区域の確認" },
            { icon: "⛰️", label: "土砂災害", desc: "警戒区域・特別警戒区域" },
            { icon: "🌊", label: "津波リスク", desc: "浸水想定区域の確認" },
            { icon: "🏗️", label: "液状化", desc: "地盤リスクの確認" },
          ].map((h) => (
            <div
              key={h.label}
              className="rounded-xl border bg-white p-4 text-center"
            >
              <span className="text-2xl">{h.icon}</span>
              <p className="font-semibold text-sm mt-1">{h.label}</p>
              <p className="text-xs text-gray-400 mt-0.5">{h.desc}</p>
            </div>
          ))}
        </section>

        {/* CTA */}
        <section className="rounded-xl bg-blue-50 border border-blue-100 p-6 text-center">
          <h2 className="text-lg font-bold text-blue-800 mb-2">
            住所を入力してリスクを調べる
          </h2>
          <p className="text-sm text-blue-600 mb-4">
            {ward.city}
            内の具体的な住所を入力すると、その地点のハザード情報と用途地域を取得できます。
          </p>
          <div className="max-w-md mx-auto">
            <SearchForm
              defaultValue={`${ward.prefecture}${ward.city}`}
            />
          </div>
        </section>

        {/* about section for SEO */}
        <section className="prose prose-sm max-w-none text-gray-600">
          <h2 className="text-lg font-bold text-gray-800">
            {ward.city}について
          </h2>
          <p>
            {ward.prefecture}{ward.city}
            は多様な都市機能を持つエリアです。
            不動産の購入・開発を検討する際は、ハザードマップによる自然災害リスクの確認と、
            用途地域による建築規制（建ぺい率・容積率・防火地域指定等）の把握が重要です。
          </p>
          <p>
            PropAPI では、国土数値情報（国土交通省）やアドレス・ベース・レジストリ（デジタル庁）のオープンデータを活用し、
            {ward.city}
            内の任意の地点のリスク情報を無料で提供しています。
          </p>
        </section>

        {/* JSON-LD structured data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebPage",
              name: `${ward.city}のハザードマップ・用途地域情報`,
              description: `${ward.prefecture}${ward.city}の洪水・土砂災害・津波・液状化リスクと用途地域を一括確認。`,
              url: `https://propapi.jp/area/${ward.prefectureSlug}/${ward.citySlug}`,
              isPartOf: {
                "@type": "WebSite",
                name: "PropAPI",
                url: "https://propapi.jp",
              },
              about: {
                "@type": "City",
                name: ward.city,
                containedInPlace: {
                  "@type": "State",
                  name: ward.prefecture,
                },
              },
            }),
          }}
        />

        {/* internal links to other wards */}
        <section>
          <h2 className="text-lg font-bold mb-3">
            {ward.prefecture}の他のエリア
          </h2>
          <div className="flex flex-wrap gap-2">
            {neighbours.map((n) => (
              <Link
                key={n.citySlug}
                href={`/area/${n.prefectureSlug}/${n.citySlug}`}
                className="inline-block px-3 py-1.5 text-sm rounded-full border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition"
              >
                {n.city}
              </Link>
            ))}
          </div>
        </section>

        {/* footer */}
        <footer className="text-xs text-gray-400 pt-4 border-t border-gray-100">
          データ出典: 国土数値情報（国土交通省）/ アドレス・ベース・レジストリ（デジタル庁）/
          J-SHIS（防災科学技術研究所）
        </footer>
      </div>
    </main>
  );
}
