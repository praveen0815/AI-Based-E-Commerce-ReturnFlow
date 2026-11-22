import type { CSSProperties } from "react";

import { cn } from "../../utils/cn";

export function TimeSeriesChart({
  title,
  points,
  emptyLabel = "No data for this window.",
}: {
  title: string;
  points: Array<{ bucket: string; value: string }>;
  emptyLabel?: string;
}) {
  const values = points.map((p) => Number(p.value));
  const max = Math.max(1, ...values);

  if (points.length === 0) {
    return (
      <figure className="space-y-2">
        <figcaption className="text-sm font-semibold text-white">{title}</figcaption>
        <p className="text-sm text-ink-muted">{emptyLabel}</p>
      </figure>
    );
  }

  return (
    <figure className="space-y-3" aria-labelledby={`ts-${title}`}>
      <figcaption id={`ts-${title}`} className="text-sm font-semibold text-white">
        {title}
      </figcaption>
      <ul className="flex h-40 items-end gap-1" role="list" aria-label={`${title} over time`}>
        {points.map((point) => {
          const value = Number(point.value);
          const barStyle: CSSProperties = { height: `${Math.max(4, Math.round((value / max) * 100))}%` };
          return (
            <li key={point.bucket} className="flex flex-1 flex-col items-center gap-1">
              <span className="sr-only">
                {point.bucket}: {value}
              </span>
              <div
                className={cn("w-full max-w-6 rounded-t bg-cyan-400/80")}
                style={barStyle}
                title={`${point.bucket}: ${value}`}
                aria-hidden="true"
              />
              <span className="hidden text-[10px] text-ink-faint sm:block">{point.bucket.slice(5)}</span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}