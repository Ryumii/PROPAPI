import type { ZoningResponse } from "@/lib/types";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null) return null;
  return (
    <div className="flex justify-between gap-4 py-2 border-b border-gray-100 last:border-0">
      <span className="text-gray-500 text-sm">{label}</span>
      <span className="font-medium text-sm text-right">{value}</span>
    </div>
  );
}

export default function ZoningInfo({ zoning }: { zoning: ZoningResponse }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-bold">用途地域</h2>

      <div className="rounded-xl border bg-white p-4 space-y-0">
        <div className="flex items-center gap-3 pb-3 border-b border-gray-100 mb-1">
          <span className="text-2xl">🏙️</span>
          <span className="text-xl font-bold text-blue-700">
            {zoning.use_district}
          </span>
          <span className="text-xs text-gray-400 bg-gray-100 rounded px-2 py-0.5">
            コード: {zoning.use_district_code}
          </span>
        </div>

        <Row
          label="建ぺい率"
          value={
            zoning.building_coverage_pct != null
              ? `${zoning.building_coverage_pct}%`
              : null
          }
        />
        <Row
          label="容積率"
          value={
            zoning.floor_area_ratio_pct != null
              ? `${zoning.floor_area_ratio_pct}%`
              : null
          }
        />
        <Row label="防火指定" value={zoning.fire_prevention} />
        <Row label="高度地区" value={zoning.height_district} />
        <Row label="風致地区" value={zoning.scenic_district} />
        <Row label="出典" value={zoning.source} />
      </div>
    </section>
  );
}
