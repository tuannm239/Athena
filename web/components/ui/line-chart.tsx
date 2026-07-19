"use client";

import { useId } from "react";

/**
 * Minimal pure-SVG line chart (Phase 8) — no chart library, SSR-safe,
 * accessible. Plots a single numeric series scaled to its own min/max.
 */
export function LineChart({
  data,
  height = 160,
  tone = "primary",
  label,
}: {
  data: number[];
  height?: number;
  tone?: "primary" | "gain" | "loss";
  label?: string;
}) {
  const id = useId();
  const width = 600;
  if (data.length < 2) {
    return <div className="text-sm text-muted-foreground">Not enough data to chart.</div>;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const dx = width / (data.length - 1);
  const y = (v: number) => height - ((v - min) / span) * (height - 8) - 4;
  const points = data.map((v, i) => `${(i * dx).toFixed(2)},${y(v).toFixed(2)}`).join(" ");
  const area = `M0,${height} L${points.replaceAll(" ", " L")} L${width},${height} Z`;
  const stroke = `hsl(var(--${tone}))`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label={label ?? "line chart"}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`g-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#g-${id})`} />
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
