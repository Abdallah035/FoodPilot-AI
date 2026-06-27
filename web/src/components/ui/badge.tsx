import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-muted text-muted-foreground",
        brand: "bg-brand-500/12 text-brand-600 dark:text-brand-300",
        success: "bg-leaf-500/15 text-leaf-600 dark:text-leaf-400",
        warning: "bg-sun-500/18 text-sun-600 dark:text-sun-400",
        danger: "bg-red-500/12 text-red-600 dark:text-red-400",
        glass: "glass-subtle text-foreground/80",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
