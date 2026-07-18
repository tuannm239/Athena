import { cn } from "@/lib/utils";

/**
 * Probability / confidence radial gauge. Pure SVG (no chart lib) so it is
 * cheap, accessible and works in Storybook/SSR. `value` is 0..1.
 */
export function Gauge({
  value,
  label,
  size = 120,
  tone = "primary",
}: {
  value: number;
  label?: string;
  size?: number;
  tone?: "primary" | "gain" | "loss" | "warn";
}) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  const dash = c * clamped;
  const toneVar = { primary: "--primary", gain: "--gain", loss: "--loss", warn: "--warn" }[tone];
  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`${label ?? "value"}: ${(clamped * 100).toFixed(0)}%`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="hsl(var(--muted))" strokeWidth={8} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`hsl(var(${toneVar}))`}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          className={cn("fill-foreground text-lg font-semibold tabular-nums")}
          transform={`rotate(90 ${size / 2} ${size / 2})`}
        >
          {(clamped * 100).toFixed(0)}%
        </text>
      </svg>
      {label ? <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span> : null}
    </div>
  );
}
