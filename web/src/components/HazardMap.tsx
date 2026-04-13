"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { BASE_STYLE, pinColorForLevel } from "@/lib/map-utils";
import { fetchHazardGeoJSON } from "@/lib/api";
import type { LocationInfo, HazardResponse } from "@/lib/types";

interface HazardMapProps {
  location: LocationInfo;
  hazard: HazardResponse | null;
}

const LAYER_CONFIG = {
  flood: { label: "洪水浸水想定", color: "#fd8d3c", opacity: 0.45 },
  landslide: { label: "土砂災害警戒", color: "#bd0026", opacity: 0.45 },
  tsunami: { label: "津波浸水想定", color: "#0c4a6e", opacity: 0.45 },
} as const;

type LayerName = keyof typeof LAYER_CONFIG;
const ALL_LAYERS: LayerName[] = ["flood", "landslide", "tsunami"];

export default function HazardMap({ location, hazard }: HazardMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [visibleLayers, setVisibleLayers] = useState<Set<LayerName>>(
    new Set(ALL_LAYERS),
  );
  const [loading, setLoading] = useState(false);

  const { lat, lng } = location;
  const level = hazard?.composite_score.level ?? "none";

  const toggleLayer = useCallback((layer: LayerName) => {
    setVisibleLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layer)) {
        next.delete(layer);
      } else {
        next.add(layer);
      }
      return next;
    });
  }, []);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── load hazard GeoJSON when location changes ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    map.flyTo({ center: [lng, lat], zoom: 15 });

    // Update marker
    markerRef.current?.remove();
    const marker = new maplibregl.Marker({ color: pinColorForLevel(level) })
      .setLngLat([lng, lat])
      .setPopup(
        new maplibregl.Popup({ offset: 25 }).setHTML(
          `<div style="font-size:13px"><strong>${location.prefecture ?? ""}${location.city ?? ""}${location.town ?? ""}</strong></div>`,
        ),
      )
      .addTo(map);
    markerRef.current = marker;

    // Fetch and render hazard polygons
    const loadGeoJSON = async () => {
      setLoading(true);
      try {
        const fc = await fetchHazardGeoJSON(lat, lng);

        // Wait for map to be ready
        const onReady = () => {
          // Remove existing hazard layers & sources
          for (const layer of ALL_LAYERS) {
            const fillId = `hazard-${layer}-fill`;
            const outlineId = `hazard-${layer}-outline`;
            if (map.getLayer(fillId)) map.removeLayer(fillId);
            if (map.getLayer(outlineId)) map.removeLayer(outlineId);
            if (map.getSource(`hazard-${layer}`)) map.removeSource(`hazard-${layer}`);
          }

          // Split features by layer
          for (const layer of ALL_LAYERS) {
            const features = fc.features.filter(
              (f) => f.properties?.layer === layer,
            );
            if (features.length === 0) continue;

            const sourceId = `hazard-${layer}`;
            map.addSource(sourceId, {
              type: "geojson",
              data: { type: "FeatureCollection", features },
            });

            // Fill layer — use per-feature color if available
            map.addLayer({
              id: `hazard-${layer}-fill`,
              type: "fill",
              source: sourceId,
              paint: {
                "fill-color": ["coalesce", ["get", "color"], LAYER_CONFIG[layer].color],
                "fill-opacity": LAYER_CONFIG[layer].opacity,
              },
            });

            // Outline
            map.addLayer({
              id: `hazard-${layer}-outline`,
              type: "line",
              source: sourceId,
              paint: {
                "line-color": ["coalesce", ["get", "color"], LAYER_CONFIG[layer].color],
                "line-width": 1,
                "line-opacity": 0.7,
              },
            });
          }
        };

        if (map.isStyleLoaded()) {
          onReady();
        } else {
          map.once("load", onReady);
        }
      } catch {
        // Silently fail — map still works without overlays
      } finally {
        setLoading(false);
      }
    };

    loadGeoJSON();
  }, [lat, lng, level, location.prefecture, location.city, location.town]);

  /* ── toggle layer visibility ── */
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    for (const layer of ALL_LAYERS) {
      const visibility = visibleLayers.has(layer) ? "visible" : "none";
      const fillId = `hazard-${layer}-fill`;
      const outlineId = `hazard-${layer}-outline`;
      if (map.getLayer(fillId)) {
        map.setLayoutProperty(fillId, "visibility", visibility);
      }
      if (map.getLayer(outlineId)) {
        map.setLayoutProperty(outlineId, "visibility", visibility);
      }
    }
  }, [visibleLayers]);

  return (
    <section className="space-y-2">
      <h2 className="text-lg font-bold">ハザードマップ</h2>

      {/* Layer toggle controls */}
      <div className="flex flex-wrap gap-2 text-xs">
        {ALL_LAYERS.map((layer) => {
          const cfg = LAYER_CONFIG[layer];
          const active = visibleLayers.has(layer);
          return (
            <button
              key={layer}
              onClick={() => toggleLayer(layer)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border transition ${
                active
                  ? "bg-white border-gray-300 text-gray-800"
                  : "bg-gray-100 border-gray-200 text-gray-400 line-through"
              }`}
            >
              <span
                className="w-3 h-3 rounded-sm inline-block"
                style={{
                  backgroundColor: cfg.color,
                  opacity: active ? 0.8 : 0.3,
                }}
              />
              {cfg.label}
            </button>
          );
        })}
        {loading && (
          <span className="text-gray-400 flex items-center gap-1">
            <span className="animate-spin h-3 w-3 border-2 border-gray-400 border-t-transparent rounded-full" />
            読込中
          </span>
        )}
      </div>

      {/* Map container */}
      <div
        ref={containerRef}
        className="w-full h-[350px] sm:h-[450px] rounded-xl overflow-hidden border border-gray-200"
      />

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-gray-500">
        <span className="font-medium text-gray-600">凡例:</span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#ffffb2" }} />
          浸水 〜0.5m
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#fecc5c" }} />
          0.5-1m
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#fd8d3c" }} />
          1-2m
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#f03b20" }} />
          2-5m
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#bd0026" }} />
          5m+/特別警戒
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#fd8d3c", opacity: 0.7 }} />
          土砂警戒
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm inline-block" style={{ backgroundColor: "#0c4a6e" }} />
          津波
        </span>
      </div>

      <p className="text-[10px] text-gray-400">
        地図: 国土地理院タイル。ポリゴンは表示用に簡略化されています。
      </p>
    </section>
  );
}
