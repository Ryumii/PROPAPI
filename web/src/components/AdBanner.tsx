"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Lazy-loaded ad banner using Intersection Observer.
 * Renders a placeholder slot that loads the ad script only
 * when the element scrolls into view.
 *
 * Currently renders a placeholder — replace the inner div
 * with actual Google Ad Manager / AdSense tags when ready.
 */

interface AdBannerProps {
  slotId?: string;
  className?: string;
}

export default function AdBanner({
  slotId = "propapi-ad-1",
  className = "",
}: AdBannerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={`w-full ${className}`}>
      {visible && (
        <div className="relative rounded-lg border border-gray-200 bg-gray-50 p-4 text-center min-h-[90px] flex items-center justify-center">
          <span className="absolute top-1 right-2 text-[10px] text-gray-300">
            広告
          </span>
          {/* Replace this placeholder with ad tag */}
          <div
            id={slotId}
            className="text-xs text-gray-400"
            data-ad-slot={slotId}
          >
            広告スペース（Google Ad Manager 連携後に表示）
          </div>
        </div>
      )}
    </div>
  );
}
