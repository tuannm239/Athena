"use client";

/**
 * Minimal pure-SVG candlestick chart — no chart library, SSR-safe, accessible.
 * Each bar draws a high–low wick and an open–close body, coloured gain (close ≥
 * open) or loss (close < open). Bars missing open/high/low (older snapshots)
 * fall back to a thin close mark so the series still renders.
 */
export interface Candle {
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
}

export function CandlestickChart({
  data,
  height = 220,
  label,
}: {
  data: Candle[];
  height?: number;
  label?: string;
}) {
  if (data.length < 2) {
    return <div className="text-sm text-muted-foreground">Not enough data to chart.</div>;
  }
  const width = 800;
  const pad = 4;
  const values: number[] = [];
  for (const d of data) {
    values.push(d.close);
    if (d.open != null) values.push(d.open);
    if (d.high != null) values.push(d.high);
    if (d.low != null) values.push(d.low);
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const y = (v: number) => height - ((v - min) / span) * (height - 2 * pad) - pad;
  const step = width / data.length;
  const bodyW = Math.max(1, Math.min(10, step * 0.6));

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label={label ?? "candlestick chart"}
      preserveAspectRatio="none"
    >
      {data.map((d, i) => {
        const cx = i * step + step / 2;
        const open = d.open ?? d.close;
        const high = d.high ?? Math.max(open, d.close);
        const low = d.low ?? Math.min(open, d.close);
        const up = d.close >= open;
        const color = `hsl(var(--${up ? "gain" : "loss"}))`;
        const bodyTop = y(Math.max(open, d.close));
        const bodyBottom = y(Math.min(open, d.close));
        const bodyH = Math.max(1, bodyBottom - bodyTop);
        return (
          <g key={i}>
            <line
              x1={cx}
              x2={cx}
              y1={y(high)}
              y2={y(low)}
              stroke={color}
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
            <rect
              x={cx - bodyW / 2}
              y={bodyTop}
              width={bodyW}
              height={bodyH}
              fill={color}
            />
          </g>
        );
      })}
    </svg>
  );
}
