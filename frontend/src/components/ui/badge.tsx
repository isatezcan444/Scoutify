import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold tracking-tight transition-colors select-none",
  {
    variants: {
      variant: {
        default:
          "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
        primary:
          "bg-[#7367F0]/15 text-[#7367F0] dark:bg-[#7367F0]/25 dark:text-[#A59DF8]",
        success:
          "bg-[#28C76F]/15 text-[#28C76F] dark:bg-[#28C76F]/25 dark:text-[#5BE49B]",
        danger:
          "bg-[#EA5455]/15 text-[#EA5455] dark:bg-[#EA5455]/25 dark:text-[#FF7F80]",
        warning:
          "bg-[#FF9F43]/15 text-[#FF9F43] dark:bg-[#FF9F43]/25 dark:text-[#FFBD7A]",
        info:
          "bg-[#00CFE8]/15 text-[#00CFE8] dark:bg-[#00CFE8]/25 dark:text-[#4DE2F5]",
        secondary:
          "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
        outline:
          "border border-slate-300 text-slate-600 dark:border-white/[0.12] dark:text-slate-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
