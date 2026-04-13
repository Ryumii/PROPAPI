"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import SearchForm from "@/components/SearchForm";
import RiskSummary from "@/components/RiskSummary";
import ZoningInfo from "@/components/ZoningInfo";
import LandPriceInfo from "@/components/LandPriceInfo";
import DataSource from "@/components/DataSource";
import HazardMap from "@/components/HazardMap";
import ApiPromoBanner from "@/components/ApiPromoBanner";
import { inspect, inspectByCoords, parseCoordinates, ApiError } from "@/lib/api";
import type { InspectResponse } from "@/lib/types";

/* ── inner component (uses useSearchParams) ──────────── */

function SearchResultsInner() {
  const params = useSearchParams();
  const address = params.get("address") ?? "";

  const [data, setData] = useState<InspectResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async (addr: string) => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const coords = parseCoordinates(addr);
      const res = coords
        ? await inspectByCoords(coords.lat, coords.lng)
        : await inspect(addr);
      setData(res);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("サーバーとの通信に失敗しました。");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (address) fetchData(address);
  }, [address, fetchData]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* ── header / search bar ── */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-gray-100">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link href="/" className="text-xl font-extrabold shrink-0">
            Prop<span className="text-blue-600">API</span>
          </Link>
          <div className="flex-1">
            <SearchForm compact defaultValue={address} />
          </div>
        </div>
      </header>

      {/* ── main content ── */}
      <main className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* address label */}
        {address && (
          <div className="text-sm text-gray-500">
            {parseCoordinates(address) ? "検索座標: " : "検索住所: "}
            <span className="font-medium text-gray-800">
              {data?.address_normalized ?? address}
            </span>
            {data?.location && (
              <span className="ml-2 text-xs text-gray-400">
                ({data.location.lat.toFixed(6)}, {data.location.lng.toFixed(6)})
              </span>
            )}
          </div>
        )}

        {/* loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
            <span className="ml-3 text-gray-500">分析中…</span>
          </div>
        )}

        {/* error */}
        {error && (
          <div className="rounded-xl bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
            <p className="font-semibold">エラー</p>
            <p>{error}</p>
          </div>
        )}

        {/* results */}
        {data && (
          <>
            {data.hazard && <RiskSummary hazard={data.hazard} />}
            {data.zoning && <ZoningInfo zoning={data.zoning} />}
            {data.land_price && <LandPriceInfo landPrice={data.land_price} />}
            <HazardMap location={data.location} hazard={data.hazard} />
            <DataSource meta={data.meta} />
            <ApiPromoBanner />
          </>
        )}

        {/* empty state */}
        {!loading && !error && !data && !address && (
          <p className="text-center text-gray-400 py-20">
            住所または座標を入力して検索してください。
          </p>
        )}
      </main>
    </div>
  );
}

/* ── page (wraps in Suspense for useSearchParams) ────── */

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
        </div>
      }
    >
      <SearchResultsInner />
    </Suspense>
  );
}
