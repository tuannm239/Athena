"use client";

import { useMemo, useState } from "react";

/**
 * Pure-SVG candlestick chart — no chart library, SSR-safe, accessible.
 * Renders high–low wicks + open–close bodies (gain/loss coloured), an optional
 * volume band, MA20/MA50 overlays, and a hover crosshair with an O/H/L/C +
 * volume tooltip. Bars missing open/high/low fall back to a thin close mark.
 */
export interface Candle {
  day?: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume?: number | null;
}

const WIDTH = 800;
const _vn = new Intl.NumberFormat("vi-VN");
const num = (v: number | null | undefined) => (v == null ? "—" : _vn.format(Math.round(v)));

function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
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
  const [hover, setHover] = useState<number | null>(null);

  const view = useMemo(() => {
    if (data.length < 2) return null;
    const hasVol = showVolume && data.some((d) => d.volume != null && d.volume > 0);
    const volH = hasVol ? Math.round(height * 0.22) : 0;
    const priceH = height - volH - (hasVol ? 6 : 0);
    const pad = 4;
    const vals: number[] = [];
    for (const d of data) {
      vals.push(d.close);
      if (d.open != null) vals.push(d.open);
      if (d.high != null) vals.push(d.high);
      if (d.low != null) vals.push(d.low);
    }
    const min = Math.min(...vals);
    const span = Math.max(...vals) - min || 1;
    const y = (v: number) => priceH - ((v - min) / span) * (priceH - 2 * pad) - pad;
    const closes = data.map((d) => d.close);
    return {
      hasVol,
      volH,
      priceH,
      y,
      volTop: priceH + 6,
      maxVol: hasVol ? Math.max(...data.map((d) => d.volume ?? 0)) || 1 : 1,
      step: WIDTH / data.length,
      bodyW: Math.max(1, Math.min(10, (WIDTH / data.length) * 0.6)),
      ma20: sma(closes, 20),
      ma50: sma(closes, 50),
    };
  }, [data, height, showVolume]);

  if (!view) {
    return <div className="text-sm text-muted-foreground">Not enough data to chart.</div>;
  }
  const { y, step, bodyW, hasVol, volTop, volH, maxVol, ma20, ma50 } = view;

  const maPath = (ma: (number | null)[]) => {
    const segs: string[] = [];
    ma.forEach((v, i) => {
      if (v == null) return;
      const cmd = segs.length && ma[i - 1] != null ? "L" : "M";
      segs.push(`${cmd}${(i * step + step / 2).toFixed(1)},${y(v).toFixed(1)}`);
    });
    return segs.join(" ");
  };

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = (e.clientX - rect.left) / rect.width;
    setHover(Math.max(0, Math.min(data.length - 1, Math.floor(frac * data.length))));
  };

  const h = hover != null ? data[hover] : null;
  const hoverFrac = hover != null ? (hover + 0.5) / data.length : 0;

  return (
    <div className="relative" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
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
          const color = `hsl(var(--${d.close >= open ? "gain" : "loss"}))`;
          const bodyTop = y(Math.max(open, d.close));
          const bodyH = Math.max(1, y(Math.min(open, d.close)) - bodyTop);
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
              {hasVol
                ? (() => {
                    const barH = ((d.volume ?? 0) / maxVol) * (volH - 2);
                    return (
                      <rect
                        x={cx - bodyW / 2}
                        y={volTop + (volH - barH)}
                        width={bodyW}
                        height={Math.max(0, barH)}
                        fill={color}
                        opacity="0.45"
                      />
                    );
                  })()
                : null}
            </g>
          );
        })}
        <path
          d={maPath(ma20)}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
        <path
          d={maPath(ma50)}
          fill="none"
          stroke="hsl(var(--warn))"
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
        {hover != null ? (
          <line
            x1={hover * step + step / 2}
            x2={hover * step + step / 2}
            y1={0}
            y2={height}
            stroke="hsl(var(--muted-foreground))"
            strokeWidth="1"
            strokeDasharray="3 3"
            vectorEffect="non-scaling-stroke"
          />
        ) : null}
      </svg>

      {/* legend */}
      <div className="mt-1 flex gap-3 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-3" style={{ background: "hsl(var(--primary))" }} />
          MA20
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-3" style={{ background: "hsl(var(--warn))" }} />
          MA50
        </span>
      </div>

      {h ? (
        <div
          className="pointer-events-none absolute top-1 z-10 rounded-md border bg-popover/95 px-2 py-1.5 text-[11px] shadow-md backdrop-blur"
          style={{
            left: `${Math.min(Math.max(hoverFrac * 100, 0), 100)}%`,
            transform: `translateX(${hoverFrac > 0.6 ? "-105%" : "5%"})`,
          }}
        >
          {h.day ? <div className="mb-0.5 font-medium text-foreground">{h.day}</div> : null}
          <div className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5 tabular-nums">
            <span className="text-muted-foreground">O</span>
            <span className="text-right text-foreground">{num(h.open)}</span>
            <span className="text-muted-foreground">H</span>
            <span className="text-right text-foreground">{num(h.high)}</span>
            <span className="text-muted-foreground">L</span>
            <span className="text-right text-foreground">{num(h.low)}</span>
            <span className="text-muted-foreground">C</span>
            <span className="text-right font-medium text-foreground">{num(h.close)}</span>
            <span className="text-muted-foreground">Vol</span>
            <span className="text-right text-foreground">{num(h.volume)}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
