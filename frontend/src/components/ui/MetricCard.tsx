import type { Density } from "../../hooks/usePreferences";
import { cn } from "../../utils/cn";
import { Badge } from "./Badge";

type MetricCardProps = {
  label: string;
  value: string;
  hint: string;
  density: Density;
};

export function MetricCard({ label, value, hint, density }: MetricCardProps) {
  return (
    <article
      className={cn(
        "rounded-2xl border border-navy-600 bg-navy-900",
        density === "compact" ? "p-4" : "p-5",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-sm font-medium text-ink-muted">{label}</h2>
        <Badge tone="warning">Sample</Badge>
      </div>
      <p className="mt-4 font-mono text-3xl font-medium tracking-tight text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-ink-faint">{hint}</p>
    </article>
  );
}
