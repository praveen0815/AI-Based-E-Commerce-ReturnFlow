import { useEffect, useState } from "react";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { listAudit } from "../services/auth";
import type { AuditEvent } from "../types/auth";
import { formatDateTime } from "../utils/format";

export function AuditPage() {
  const { storeId } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listAudit()
      .then((rows) => {
        if (!cancelled) {
          setEvents(rows);
          setError("");
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Audit events could not be loaded.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [storeId]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Security"
        title="Audit"
        description="Security events for the current store. Passwords and access tokens are not written to these records."
      />
      {error ? (
        <Alert tone="danger" title="Could not load audit events">
          {error}
        </Alert>
      ) : null}
      {loading ? <Spinner label="Loading audit events" /> : null}
      {!loading && events.length === 0 ? (
        <Alert tone="info" title="No store events yet">
          Creating the store and membership changes appear here.
        </Alert>
      ) : null}
      <div className="space-y-3">
        {events.map((event) => (
          <Card key={event.id} className="p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <p className="font-medium text-white">{event.action}</p>
              <p className="text-xs text-ink-faint">{formatDateTime(new Date(event.created_at))}</p>
            </div>
            <p className="mt-1 text-sm text-ink-muted">{event.actor_email ?? "Unknown actor"}</p>
            {Object.keys(event.details).length > 0 ? (
              <dl className="mt-3 grid gap-1 text-sm text-ink-muted">
                {Object.entries(event.details).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <dt className="font-medium text-ink">{key}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </Card>
        ))}
      </div>
    </div>
  );
}
