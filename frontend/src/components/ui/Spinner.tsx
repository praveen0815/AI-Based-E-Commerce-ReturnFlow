import { cn } from "../../utils/cn";

export function Spinner({ label, className }: { label: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3 text-sm text-ink-muted", className)} role="status">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-400/30 border-t-cyan-300"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}
