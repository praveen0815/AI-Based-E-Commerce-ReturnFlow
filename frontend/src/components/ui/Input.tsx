import type { InputHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
};

export function Input({ id, label, hint, error, className, ...props }: InputProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "focus-ring w-full rounded-lg border bg-navy-950 px-3 py-2 text-sm text-ink placeholder:text-ink-faint",
          error ? "border-rose-400" : "border-navy-600",
          className,
        )}
        {...props}
      />
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
