import { cn } from "@/lib/utils";
export function Stat({
  label, value, sub, valueClassName,
}: { label: string; value: React.ReactNode; sub?: React.ReactNode; valueClassName?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className={cn("text-2xl font-semibold tabular-nums", valueClassName)}>{value}</span>
      {sub ? <span className="text-xs text-muted-foreground">{sub}</span> : null}
    </div>
  );
}
