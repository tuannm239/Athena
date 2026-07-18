import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
  {
    variants: {
      variant: {
        default: "bg-secondary text-secondary-foreground ring-border",
        primary: "bg-primary/15 text-primary ring-primary/30",
        gain: "bg-gain/15 text-gain ring-gain/30",
        loss: "bg-loss/15 text-loss ring-loss/30",
        warn: "bg-warn/15 text-warn ring-warn/30",
        muted: "bg-muted text-muted-foreground ring-border",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
