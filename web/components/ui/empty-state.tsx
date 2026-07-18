import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon, title, description, className, action,
}: {
  icon?: LucideIcon; title: string; description?: string; className?: string; action?: React.ReactNode;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-10 text-center", className)}>
      {Icon ? <Icon className="h-8 w-8 text-muted-foreground" aria-hidden /> : null}
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="max-w-sm text-xs text-muted-foreground">{description}</p> : null}
      {action}
    </div>
  );
}
