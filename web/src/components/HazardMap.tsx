"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { BASE_STYLE, pinColorForLevel } from "@/lib/map-utils";
import type { LocationInfo, HazardResponse } from "@/lib/types";

interface HazardMapProps {
  location: LocationInfo;
  hazard: HazardResponse | null;
}

export default function HazardMap({ location, hazard }: HazardMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  const { lat, lng } = location;
  const level = hazard?.composite_score.level ?? "none";

  /* ── initialise map ── */
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [lng, lat],
      zoom: 15,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── update centre & marker when location changes ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    map.flyTo({ center: [lng, lat], zoom: 15 });

    // Remove old marker
    markerRef.current?.remove();

    // Add new marker
    const marker = new maplibregl.Marker({ color: pinColorForLevel(level) })
      .setLngLat([lng, lat])
      .setPopup(
        new maplibregl.Popup({ offset: 25 }).setHTML(
          `<div style="font-size:13px"><strong>${location.prefecture ?? ""}${location.city ?? ""}${location.town ?? ""}</strong></div>`,
        ),
      )
      .addTo(map);

    markerRef.current = marker;
  }, [lat, lng, level, location.prefecture, location.city, location.town]);

  return (
    <section className="space-y-2">
      <h2 className="text-lg font-bold">地図</h2>
      <div
        ref={containerRef}
        className="w-full h-[350px] sm:h-[450px] rounded-xl overflow-hidden border border-gray-200"
      />
      <p className="text-[10px] text-gray-400">
        地図: 国土地理院タイル。ハザードポリゴンオーバーレイは今後対応予定。
      </p>
    </section>
  );
}
