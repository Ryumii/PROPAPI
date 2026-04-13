import type { LandPriceResponse, NearbyLandPrice } from "@/lib/types";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null) return null;
  return (
    <div className="flex justify-between gap-4 py-2 border-b border-gray-100 last:border-0">
      <span className="text-gray-500 text-sm">{label}</span>
      <span className="font-medium text-sm text-right">{value}</span>
    </div>
  );
}

function formatPrice(price: number): string {
  if (price >= 10000) {
    return `${(price / 10000).toFixed(1)}万円/m²`;
  }
  return `${price.toLocaleString()}円/m²`;
}

function NearestCard({ point }: { point: NearbyLandPrice }) {
  return (
    <div className="rounded-xl border bg-white p-4 space-y-0">
      <div className="flex items-center gap-3 pb-3 border-b border-gray-100 mb-1">
        <span className="text-2xl">💰</span>
        <div>
          <span className="text-xl font-bold text-emerald-700">
            {formatPrice(point.price_per_sqm)}
          </span>
          <span className="ml-2 text-xs text-gray-400">
            ({point.price_per_sqm.toLocaleString()}円/m²)
          </span>
        </div>
        {point.yoy_change_pct != null && (
          <span
            className={`text-sm font-semibold px-2 py-0.5 rounded-full ${
              point.yoy_change_pct > 0
                ? "text-red-600 bg-red-50"
                : point.yoy_change_pct < 0
                  ? "text-blue-600 bg-blue-50"
                  : "text-gray-500 bg-gray-100"
            }`}
          >
            {point.yoy_change_pct > 0 ? "+" : ""}
            {point.yoy_change_pct.toFixed(1)}%
          </span>
        )}
      </div>

      <Row label="所在地" value={point.address} />
      <Row label="利用現況" value={point.land_use} />
      <Row label="地積" value={point.area_sqm ? `${point.area_sqm} m²` : null} />
      <Row label="建物構造" value={point.structure} />
      <Row
        label="最寄駅"
        value={
          point.nearest_station
            ? `${point.nearest_station}${point.station_distance_m ? ` (${point.station_distance_m}m)` : ""}`
            : null
        }
      />
      <Row label="検索地点からの距離" value={`${point.distance_m}m`} />
      <Row label="調査年" value={`${point.year}年`} />
    </div>
  );
}

function NearbyRow({ point, index }: { point: NearbyLandPrice; index: number }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0 text-sm">
      <span className="text-gray-400 w-5 text-right">{index + 1}</span>
      <div className="flex-1 min-w-0">
        <span className="font-medium text-gray-800">
          {formatPrice(point.price_per_sqm)}
        </span>
        {point.yoy_change_pct != null && (
          <span
            className={`ml-1 text-xs ${
              point.yoy_change_pct > 0
                ? "text-red-500"
                : point.yoy_change_pct < 0
                  ? "text-blue-500"
                  : "text-gray-400"
            }`}
          >
            ({point.yoy_change_pct > 0 ? "+" : ""}
            {point.yoy_change_pct.toFixed(1)}%)
          </span>
        )}
      </div>
      <span className="text-gray-500 text-xs truncate max-w-[120px]">
        {point.land_use ?? "—"}
      </span>
      <span className="text-gray-400 text-xs w-16 text-right">
        {point.distance_m}m
      </span>
    </div>
  );
}

export default function LandPriceInfo({
  landPrice,
}: {
  landPrice: LandPriceResponse;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-bold">公示地価</h2>

      {landPrice.nearest ? (
        <NearestCard point={landPrice.nearest} />
      ) : (
        <div className="rounded-xl border bg-white p-4 text-gray-400 text-sm">
          半径2km以内に公示地価の地点が見つかりませんでした。
        </div>
      )}

      {landPrice.nearby.length > 1 && (
        <div className="rounded-xl border bg-white p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-2">
            近隣の公示地価（{landPrice.nearby.length}件）
          </h3>
          {landPrice.nearby.map((p, i) => (
            <NearbyRow key={i} point={p} index={i} />
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400">出典: {landPrice.source}</p>
    </section>
  );
}
