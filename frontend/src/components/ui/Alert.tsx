import type { ReactNode } from "react";

import { cn } from "../../utils/cn";

type AlertProps = {
  tone: "info" | "success" | "warning" | "danger";
  title: string;
  children?: ReactNode;
};

const tones: Record<AlertProps["tone"], string> = {
  info: "border-cyan-400/30 bg-cyan-400/10 text-cyan-50",
  success: "border-emerald-400/30 bg-emerald-400/10 text-emerald-50",
  warning: "border-amber-400/30 bg-amber-400/10 text-amber-50",
  danger: "border-rose-400/40 bg-rose-400/10 text-rose-50",
};

export function Alert({ tone, title, children }: AlertProps) {
  const live = tone === "danger" || tone === "warning" ? "alert" : "status";
  return (
    <div role={live} className={cn("rounded-xl border px-4 py-3", tones[tone])}>
      <p className="text-sm font-semibold">{title}</p>
      {children ? <div className="mt-1 text-sm leading-6 text-ink/90">{children}</div> : null}
    </div>
  );
}
