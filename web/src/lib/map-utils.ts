/** Map style and layer helpers for MapLibre GL. */

/** Free tile source — GSI (国土地理院) standard map. */
export const GSI_TILE_URL =
  "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png";

export const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    gsi: {
      type: "raster",
      tiles: [GSI_TILE_URL],
      tileSize: 256,
      attribution:
        '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank">国土地理院</a>',
    },
  },
  layers: [
    {
      id: "gsi-tiles",
      type: "raster",
      source: "gsi",
      minzoom: 0,
      maxzoom: 18,
    },
  ],
};

/** Marker pin colour by composite risk level. */
export function pinColorForLevel(level: string): string {
  switch (level) {
    case "very_high":
      return "#dc2626";
    case "high":
      return "#ea580c";
    case "medium":
      return "#eab308";
    case "low":
      return "#84cc16";
    case "very_low":
      return "#22c55e";
    default:
      return "#6b7280";
  }
}
