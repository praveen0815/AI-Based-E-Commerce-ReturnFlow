import type { ReturnStatusEvent } from "../types/commerce";
import { formatDateTime } from "../utils/format";

export function ReturnTimeline({ events }: { events: ReturnStatusEvent[] }) {
  return (
    <ol className="space-y-4 border-l border-navy-600 pl-4">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span className="absolute -left-[1.3rem] mt-1.5 h-2.5 w-2.5 rounded-full bg-cyan-300" aria-hidden="true" />
          <p className="text-sm font-medium text-white">{event.to_status.replaceAll("_", " ")}</p>
          <p className="text-xs text-ink-muted">
            {formatDateTime(new Date(event.created_at))}
            {event.actor_email ? ` · ${event.actor_email}` : ""}
          </p>
          {event.note ? <p className="mt-1 text-sm text-ink">{event.note}</p> : null}
        </li>
      ))}
    </ol>
  );
}