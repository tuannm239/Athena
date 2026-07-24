"use client";

/**
 * Minimal pure-SVG candlestick chart — no chart library, SSR-safe, accessible.
 * Each bar draws a high–low wick and an open–close body, coloured gain (close ≥
 * open) or loss (close < open). An optional volume band renders underneath.
 * Bars missing open/high/low (older snapshots) fall back to a thin close mark.
 */
export interface Candle {
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume?: number | null;
}

export function CandlestickChart({
  data,
  height = 260,
  label,
  showVolume = true,
}: {
  data: Candle[];
  height?: number;
  label?: string;
  showVolume?: boolean;
}) {
  if (data.length < 2) {
    return <div className="text-sm text-muted-foreground">Not enough data to chart.</div>;
  }
  const width = 800;
  const pad = 4;
  const hasVol = showVolume && data.some((d) => d.volume != null && d.volume > 0);
  const volH = hasVol ? Math.round(height * 0.22) : 0;
  const priceH = height - volH - (hasVol ? 6 : 0);

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
  const y = (v: number) => priceH - ((v - min) / span) * (priceH - 2 * pad) - pad;

  const maxVol = hasVol ? Math.max(...data.map((d) => d.volume ?? 0)) || 1 : 1;
  const volTop = priceH + 6;
  const vy = (v: number) => (v / maxVol) * (volH - 2);

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
        const bodyH = Math.max(1, y(Math.min(open, d.close)) - bodyTop);
        const barH = hasVol ? vy(d.volume ?? 0) : 0;
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
            <rect x={cx - bodyW / 2} y={bodyTop} width={bodyW} height={bodyH} fill={color} />
            {hasVol ? (
              <rect
                x={cx - bodyW / 2}
                y={volTop + (volH - barH)}
                width={bodyW}
                height={Math.max(0, barH)}
                fill={color}
                opacity="0.45"
              />
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}
