import type { InspectMeta } from "@/lib/types";

const METHOD_LABELS: Record<string, string> = {
  address_match: "住所マスタ一致",
  town_fallback: "町丁目フォールバック",
  external_geocoder: "外部ジオコーダ",
};

export default function DataSource({ meta }: { meta: InspectMeta }) {
  return (
    <section className="text-xs text-gray-400 space-y-1 pt-4 border-t border-gray-100">
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        <span>
          ジオコーディング:{" "}
          {METHOD_LABELS[meta.geocoding_method] ?? meta.geocoding_method}
        </span>
        <span>信頼度: {(meta.confidence * 100).toFixed(0)}%</span>
        <span>処理時間: {meta.processing_time_ms} ms</span>
        <span>API v{meta.api_version}</span>
      </div>
      {meta.data_updated_at && (
        <p>データ更新日: {meta.data_updated_at}</p>
      )}
      <p className="mt-2 text-[10px] leading-relaxed text-gray-300">
        出典: 国土数値情報（国土交通省）/ アドレス・ベース・レジストリ（デジタル庁）/
        J-SHIS（防災科学技術研究所）。本情報は参考情報であり、正確性を保証するものではありません。
        重要な判断には必ず各自治体の公開資料をご確認ください。
      </p>
    </section>
  );
}
