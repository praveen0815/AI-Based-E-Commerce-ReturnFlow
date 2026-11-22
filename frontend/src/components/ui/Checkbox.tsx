import type { InputHTMLAttributes } from "react";

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
  hint?: string;
};

export function Checkbox({ id, label, hint, ...props }: CheckboxProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className="flex gap-3">
      <input
        id={id}
        type="checkbox"
        aria-describedby={hintId}
        className="focus-ring mt-1 h-4 w-4 rounded border-navy-600 bg-navy-950 text-cyan-400"
        {...props}
      />
      <div>
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </label>
        {hint ? (
          <p id={hintId} className="text-xs leading-5 text-ink-faint">
            {hint}
          </p>
        ) : null}
      </div>
    </div>
  );
}
