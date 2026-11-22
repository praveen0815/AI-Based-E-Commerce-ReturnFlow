import type { HTMLAttributes } from "react";

import { cn } from "../../utils/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-2xl border border-navy-600 bg-navy-900/90 shadow-panel", className)}
      {...props}
    />
  );
}
