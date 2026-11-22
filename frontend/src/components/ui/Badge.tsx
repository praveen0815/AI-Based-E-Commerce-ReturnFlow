import type { HTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "cyan" | "warning";
};

const tones: Record<NonNullable<BadgeProps["tone"]>, string> = {
  neutral: "bg-navy-800 text-ink-muted",
  cyan: "bg-cyan-400/15 text-cyan-200",
  warning: "bg-amber-400/15 text-amber-200",
};

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
