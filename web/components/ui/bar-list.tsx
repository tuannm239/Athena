import { cn } from "@/lib/utils";

export interface BarDatum {
  label: string;
  value: number;
  tone?: "primary" | "gain" | "loss" | "warn" | "muted";
}

const TONE: Record<NonNullable<BarDatum["tone"]>, string> = {
  primary: "bg-primary",
  gain: "bg-gain",
  loss: "bg-loss",
  warn: "bg-warn",
  muted: "bg-muted-foreground",
};

/**
 * Pure-CSS horizontal bar list (no chart lib) — cheap, accessible, SSR-safe.
 * Bars are scaled to the largest value in the set.
 */
export function BarList({ data, className }: { data: BarDatum[]; className?: string }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <ul className={cn("space-y-2", className)} role="list">
      {data.map((d) => (
        <li key={d.label} className="grid grid-cols-[5rem_1fr_2rem] items-center gap-2 text-xs">
          <span className="truncate text-muted-foreground" title={d.label}>
            {d.label}
          </span>
          <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
            <span
              className={cn("block h-full rounded-full", TONE[d.tone ?? "primary"])}
              style={{ width: `${(d.value / max) * 100}%` }}
            />
          </span>
          <span className="text-right tabular-nums">{d.value}</span>
        </li>
      ))}
    </ul>
  );
}
