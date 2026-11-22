import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "bg-cyan-400 text-navy-950 hover:bg-cyan-300",
  secondary: "border border-navy-600 bg-navy-800 text-ink hover:border-cyan-400/60",
  ghost: "text-ink-muted hover:bg-navy-800 hover:text-ink",
};

export function Button({ variant = "primary", className, type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "focus-ring inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
