"use client";

import { useMemo, useState } from "react";

/**
 * Pure-SVG candlestick chart — no chart library, SSR-safe, accessible.
 * Renders high–low wicks + open–close bodies (gain/loss), a volume band,
 * MA20/MA50 overlays, price/time/volume axes (HTML overlays so text stays
 * crisp under the stretched SVG), and a hover crosshair + O/H/L/C/volume
 * tooltip. Bars missing open/high/low fall back to a thin close mark.
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
const GUTTER = 56; // right axis width (px)
const DATE_H = 18; // bottom date-axis height (px)
const _vn = new Intl.NumberFormat("vi-VN");
const num = (v: number | null | undefined) => (v == null ? "—" : _vn.format(Math.round(v)));
const compact = (v: number) =>
  v >= 1e9 ? `${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : _vn.format(v);
const shortDay = (d?: string) => (d ? `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(2, 4)}` : "");

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

  const v = useMemo(() => {
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
    const max = Math.max(...vals);
    const span = max - min || 1;
    const y = (val: number) => priceH - ((val - min) / span) * (priceH - 2 * pad) - pad;
    const closes = data.map((d) => d.close);
    const priceTicks = Array.from({ length: 5 }, (_, i) => min + (span * i) / 4);
    const n = data.length;
    const dateTicks = Array.from({ length: Math.min(6, n) }, (_, i) =>
      Math.round((i * (n - 1)) / (Math.min(6, n) - 1 || 1)),
    );
    return {
      hasVol,
      volH,
      priceH,
      y,
      min,
      max,
      priceTicks,
      dateTicks,
      volTop: priceH + 6,
      maxVol: hasVol ? Math.max(...data.map((d) => d.volume ?? 0)) || 1 : 1,
      step: WIDTH / n,
      bodyW: Math.max(1, Math.min(10, (WIDTH / n) * 0.6)),
      ma20: sma(closes, 20),
      ma50: sma(closes, 50),
    };
  }, [data, height, showVolume]);

  if (!v) return <div className="text-sm text-muted-foreground">Not enough data to chart.</div>;

  const maPath = (ma: (number | null)[]) => {
    const segs: string[] = [];
    ma.forEach((val, i) => {
      if (val == null) return;
      const cmd = segs.length && ma[i - 1] != null ? "L" : "M";
      segs.push(`${cmd}${(i * v.step + v.step / 2).toFixed(1)},${v.y(val).toFixed(1)}`);
    });
    return segs.join(" ");
  };

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const frac = (e.clientX - r.left) / r.width;
    setHover(Math.max(0, Math.min(data.length - 1, Math.floor(frac * data.length))));
  };

  const h = hover != null ? data[hover] : null;
  const hoverFrac = hover != null ? (hover + 0.5) / data.length : 0;
  const grid = "hsl(var(--border))";

  return (
    <div>
      <div className="relative" style={{ height, marginRight: GUTTER }}>
        <div
          className="absolute inset-0"
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
          <svg
            viewBox={`0 0 ${WIDTH} ${height}`}
            className="h-full w-full"
            role="img"
            aria-label={label ?? "candlestick chart"}
            preserveAspectRatio="none"
          >
            {v.priceTicks.map((t, i) => (
              <line
                key={`g${i}`}
                x1={0}
                x2={WIDTH}
                y1={v.y(t)}
                y2={v.y(t)}
                stroke={grid}
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
                opacity="0.5"
              />
            ))}
            {data.map((d, i) => {
              const cx = i * v.step + v.step / 2;
              const open = d.open ?? d.close;
              const high = d.high ?? Math.max(open, d.close);
              const low = d.low ?? Math.min(open, d.close);
              const color = `hsl(var(--${d.close >= open ? "gain" : "loss"}))`;
              const bodyTop = v.y(Math.max(open, d.close));
              const bodyH = Math.max(1, v.y(Math.min(open, d.close)) - bodyTop);
              const barH = v.hasVol ? ((d.volume ?? 0) / v.maxVol) * (v.volH - 2) : 0;
              return (
                <g key={i}>
                  <line
                    x1={cx}
                    x2={cx}
                    y1={v.y(high)}
                    y2={v.y(low)}
                    stroke={color}
                    strokeWidth="1"
                    vectorEffect="non-scaling-stroke"
                  />
                  <rect x={cx - v.bodyW / 2} y={bodyTop} width={v.bodyW} height={bodyH} fill={color} />
                  {v.hasVol ? (
                    <rect
                      x={cx - v.bodyW / 2}
                      y={v.volTop + (v.volH - barH)}
                      width={v.bodyW}
                      height={Math.max(0, barH)}
                      fill={color}
                      opacity="0.45"
                    />
                  ) : null}
                </g>
              );
            })}
            <path d={maPath(v.ma20)} fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
            <path d={maPath(v.ma50)} fill="none" stroke="hsl(var(--warn))" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
            {hover != null ? (
              <line
                x1={hover * v.step + v.step / 2}
                x2={hover * v.step + v.step / 2}
                y1={0}
                y2={height}
                stroke="hsl(var(--muted-foreground))"
                strokeWidth="1"
                strokeDasharray="3 3"
                vectorEffect="non-scaling-stroke"
              />
            ) : null}
          </svg>

          {/* price axis (right gutter) + volume max label */}
          {v.priceTicks.map((t, i) => (
            <div
              key={`p${i}`}
              className="pointer-events-none absolute text-[10px] tabular-nums text-muted-foreground"
              style={{ top: v.y(t), left: "100%", transform: "translateY(-50%)", paddingLeft: 4 }}
            >
              {num(t)}
            </div>
          ))}
          {v.hasVol ? (
            <div
              className="pointer-events-none absolute text-[10px] tabular-nums text-muted-foreground"
              style={{ top: v.volTop, left: "100%", transform: "translateY(-2px)", paddingLeft: 4 }}
            >
              {compact(v.maxVol)}
            </div>
          ) : null}

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
                <span className="text-right text-foreground">{compact(h.volume ?? 0)}</span>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* time axis (bottom) */}
      <div className="relative" style={{ height: DATE_H, marginRight: GUTTER }}>
        {v.dateTicks.map((i) => (
          <div
            key={`d${i}`}
            className="absolute text-[10px] tabular-nums text-muted-foreground"
            style={{ left: `${((i + 0.5) / data.length) * 100}%`, transform: "translateX(-50%)", top: 2 }}
          >
            {shortDay(data[i]?.day)}
          </div>
        ))}
      </div>

      {/* legend */}
      <div className="mt-0.5 flex gap-3 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-3" style={{ background: "hsl(var(--primary))" }} /> MA20
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-3" style={{ background: "hsl(var(--warn))" }} /> MA50
        </span>
      </div>
    </div>
  );
}
