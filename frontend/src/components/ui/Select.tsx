import type { SelectHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  hint?: string;
  error?: string;
  options: Array<{ value: string; label: string }>;
};

export function Select({ id, label, hint, error, options, className, ...props }: SelectProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "focus-ring w-full rounded-lg border bg-navy-950 px-3 py-2 text-sm text-ink",
          error ? "border-rose-400" : "border-navy-600",
          className,
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint ? (
        <p id={hintId} className="text-xs leading-5 text-ink-faint">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-xs leading-5 text-rose-300">
          {error}
        </p>
      ) : null}
    </div>
  );
}
