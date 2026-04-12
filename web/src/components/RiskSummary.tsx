"use client";

import { useState } from "react";
import type { HazardResponse } from "@/lib/types";

/* ── colour / label helpers ─────────────────────────── */

const LEVEL_META: Record<string, { color: string; bg: string; label: string }> =
  {
    none: { color: "text-gray-500", bg: "bg-gray-100", label: "リスクなし" },
    very_low: {
      color: "text-green-700",
      bg: "bg-green-50",
      label: "非常に低い",
    },
    low: { color: "text-lime-700", bg: "bg-lime-50", label: "低い" },
    medium: { color: "text-yellow-700", bg: "bg-yellow-50", label: "中程度" },
    high: { color: "text-orange-700", bg: "bg-orange-50", label: "高い" },
    very_high: { color: "text-red-700", bg: "bg-red-50", label: "非常に高い" },
    unavailable: {
      color: "text-gray-400",
      bg: "bg-gray-50",
      label: "データなし",
    },
  };

function meta(level: string) {
  return LEVEL_META[level] ?? LEVEL_META.none;
}

/* ── score bar (0-5) ────────────────────────────────── */

function ScoreBar({ score, max = 5 }: { score: number; max?: number }) {
  const pct = Math.min(100, (score / max) * 100);
  const hue = 120 - (score / max) * 120; // green→red
  return (
    <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${pct}%`, backgroundColor: `hsl(${hue},70%,50%)` }}
      />
    </div>
  );
}

/* ── composite score badge ──────────────────────────── */

function CompositeBadge({
  score,
  level,
  description,
}: {
  score: number;
  level: string;
  description: string;
}) {
  const m = meta(level);
  return (
    <div
      className={`rounded-2xl p-6 ${m.bg} flex flex-col sm:flex-row items-center gap-4`}
    >
      <div className="flex items-center gap-3">
        <span className={`text-4xl font-bold ${m.color}`}>
          {score.toFixed(1)}
        </span>
        <span className="text-gray-400 text-lg">/ 5.0</span>
      </div>
      <div className="flex-1 text-center sm:text-left">
        <span
          className={`inline-block px-3 py-0.5 rounded-full text-sm font-semibold ${m.color} ${m.bg} border border-current/20`}
        >
          {m.label}
        </span>
        <p className="mt-1 text-sm text-gray-600">{description}</p>
      </div>
    </div>
  );
}

/* ── single hazard card (expandable) ────────────────── */

interface HazardCardProps {
  title: string;
  icon: string;
  level: string;
  score: number | null;
  children: React.ReactNode;
}

function HazardCard({ title, icon, level, score, children }: HazardCardProps) {
  const [open, setOpen] = useState(false);
  const m = meta(level);

  return (
    <div className={`rounded-xl border ${m.bg} overflow-hidden`}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-black/5 transition"
      >
        <span className="text-2xl" role="img" aria-label={title}>
          {icon}
        </span>
        <span className="flex-1 font-semibold">{title}</span>

        {score !== null ? (
          <div className="flex items-center gap-2 min-w-[100px]">
            <ScoreBar score={score} />
            <span className={`text-sm font-medium ${m.color} w-6 text-right`}>
              {score}
            </span>
          </div>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}

        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 text-sm text-gray-700 border-t border-gray-200/60 space-y-1">
          {children}
        </div>
      )}
    </div>
  );
}

/* ── detail rows ────────────────────────────────────── */

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null) return null;
  return (
    <div className="flex justify-between gap-4">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-right">{value}</span>
    </div>
  );
}

/* ── main export ────────────────────────────────────── */

export default function RiskSummary({ hazard }: { hazard: HazardResponse }) {
  const { flood, landslide, tsunami, liquefaction, composite_score } = hazard;

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-bold">ハザードリスク</h2>

      <CompositeBadge
        score={composite_score.score}
        level={composite_score.level}
        description={composite_score.description}
      />

      <div className="grid gap-3">
        {/* ── Flood ─────── */}
        <HazardCard
          title="洪水"
          icon="🌊"
          level={flood.risk_level}
          score={flood.risk_score}
        >
          <Row label="浸水深" value={flood.depth_range} />
          {flood.depth_m != null && (
            <Row label="浸水深 (m)" value={`${flood.depth_m} m`} />
          )}
          <Row
            label="再現期間"
            value={
              flood.return_period_years
                ? `${flood.return_period_years} 年`
                : null
            }
          />
          <Row label="出典" value={flood.source} />
        </HazardCard>

        {/* ── Landslide ─── */}
        <HazardCard
          title="土砂災害"
          icon="⛰️"
          level={landslide.risk_level}
          score={landslide.risk_score}
        >
          <Row label="区域区分" value={landslide.zone_type} />
          <Row label="出典" value={landslide.source} />
        </HazardCard>

        {/* ── Tsunami ───── */}
        <HazardCard
          title="津波"
          icon="🌊"
          level={tsunami.risk_level}
          score={tsunami.risk_score}
        >
          {tsunami.depth_m != null && (
            <Row label="浸水深" value={`${tsunami.depth_m} m`} />
          )}
          <Row label="出典" value={tsunami.source} />
        </HazardCard>

        {/* ── Liquefaction ─ */}
        <HazardCard
          title="液状化"
          icon="🏗️"
          level={liquefaction.risk_level}
          score={liquefaction.risk_score}
        >
          <Row label="備考" value={liquefaction.note} />
          {liquefaction.map_url && (
            <Row
              label="地図リンク"
              value={
                <a
                  href={liquefaction.map_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  J-SHIS 液状化マップを開く ↗
                </a>
              }
            />
          )}
          <Row label="出典" value={liquefaction.source} />
        </HazardCard>
      </div>
    </section>
  );
}
