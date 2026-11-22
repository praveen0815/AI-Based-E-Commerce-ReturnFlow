import { cn } from "../../utils/cn";

export function BarChart({
  title,
  items,
  valueKey = "count",
  labelKey = "label",
  formatValue,
  emptyLabel = "No data for this period.",
  className,
}: {
  title: string;
  items: Array<Record<string, string | number>>;
  valueKey?: string;
  labelKey?: string;
  formatValue?: (value: number) => string;
  emptyLabel?: string;
  className?: string;
}) {
  const numeric = items.map((row) => Number(row[valueKey] ?? 0));
  const max = Math.max(1, ...numeric);

  if (items.length === 0) {
    return (
      <figure className={cn("space-y-2", className)}>
        <figcaption className="text-sm font-semibold text-white">{title}</figcaption>
        <p className="text-sm text-ink-muted">{emptyLabel}</p>
      </figure>
    );
  }

  return (
    <figure className={cn("space-y-3", className)} role="group" aria-labelledby={`chart-${title}`}>
      <figcaption id={`chart-${title}`} className="text-sm font-semibold text-white">
        {title}
      </figcaption>
      <ul className="space-y-2" aria-label={`${title} data series`}>
        {items.map((row) => {
          const label = String(row[labelKey]);
          const value = Number(row[valueKey] ?? 0);
          const width = `${Math.round((value / max) * 100)}%`;
          const display = formatValue ? formatValue(value) : String(value);
          return (
            <li key={label} className="grid grid-cols-[minmax(0,8rem)_1fr_auto] items-center gap-2 text-sm">
              <span className="truncate text-ink-muted" title={label}>
                {label.replaceAll("_", " ")}
              </span>
              <input
                type="range"
                readOnly
                aria-hidden="true"
                tabIndex={-1}
                className="pointer-events-none h-2 w-full appearance-none rounded-full bg-navy-800 accent-cyan-400"
                style={{
                  background: `linear-gradient(to right, rgb(34 211 238 / 0.85) ${width}, rgb(30 41 59) ${width})`,
                }}
                value={value}
                min={0}
                max={max}
              />
              <span className="font-mono text-xs text-ink">{display}</span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}