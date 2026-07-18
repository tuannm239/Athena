import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import type { LucideIcon } from "lucide-react";

/**
 * Honest placeholder for feature areas whose backend endpoints are not yet
 * exposed (they return 501 / are unimplemented server-side). Rather than
 * fabricate business logic (forbidden by the directive), each renders the
 * planned scope and states which backend capability it awaits. When the
 * endpoint ships, the corresponding page is wired to it.
 */
export function PendingFeature({
  title,
  description,
  icon,
  scope,
  awaits,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  scope: string[];
  awaits: string;
}) {
  return (
    <>
      <PageHeader
        title={title}
        description={description}
        actions={<Badge variant="warn">endpoint pending</Badge>}
      />
      <EmptyState
        icon={icon}
        title="Awaiting backend capability"
        description={awaits}
        action={
          <ul className="mt-3 grid max-w-lg grid-cols-2 gap-x-6 gap-y-1 text-left text-xs text-muted-foreground">
            {scope.map((s) => (
              <li key={s} className="flex items-center gap-1.5">
                <span className="h-1 w-1 rounded-full bg-muted-foreground" />
                {s}
              </li>
            ))}
          </ul>
        }
      />
    </>
  );
}
