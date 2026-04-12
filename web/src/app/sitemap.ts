import type { MetadataRoute } from "next";

import { TOKYO_WARDS } from "@/lib/wards";

export const dynamic = "force-static";

const BASE_URL = "https://propapi.jp";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: new Date(), changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE_URL}/search`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE_URL}/docs`, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE_URL}/terms`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${BASE_URL}/privacy`, changeFrequency: "yearly", priority: 0.3 },
  ];

  const areaPages: MetadataRoute.Sitemap = TOKYO_WARDS.map((w) => ({
    url: `${BASE_URL}/area/${w.prefectureSlug}/${w.citySlug}`,
    lastModified: new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [...staticPages, ...areaPages];
}
