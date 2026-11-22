import { useCallback, useEffect, useState } from "react";

import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Spinner } from "./ui/Spinner";
import { ApiError } from "../services/api";
import {
  completeReturnFulfillment,
  finalizeRefund,
  getFulfillment,
  initiateRefund,
  markInTransit,
  markReceived,
  requestReturnLabel,
  startExchange,
} from "../services/fulfillment";
import type { FulfillmentSnapshot } from "../types/fulfillment";
import { formatDateTime } from "../utils/format";

export function ReturnFulfillmentPanel({
  returnId,
  canManage,
  requestedResolution,
  onStatusChange,
}: {
  returnId: string;
  canManage: boolean;
  requestedResolution: string;
  onStatusChange?: () => void;
}) {
  const [snapshot, setSnapshot] = useState<FulfillmentSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    const data = await getFulfillment(returnId);
    setSnapshot(data);
  }, [returnId]);

  useEffect(() => {
    refresh()
      .catch((caught: unknown) => {
        setError(caught instanceof ApiError ? caught.message : "Could not load fulfillment.");
      })
      .finally(() => setLoading(false));
  }, [refresh]);

  async function run(action: () => Promise<unknown>) {
    setError("");
    setBusy(true);
    try {
      await action();
      await refresh();
      onStatusChange?.();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Fulfillment action failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <Spinner label="Loading fulfillment" />;
  }

  const shipment = snapshot?.shipment ?? null;
  const refund = snapshot?.refund ?? null;
  const timeline = snapshot?.timeline ?? [];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white">Refund &amp; logistics</h2>
      {error ? <Alert tone="danger" title="Fulfillment">{error}</Alert> : null}

      <Card className="space-y-3 p-5">
        <h3 className="text-base font-semibold text-white">Refund timeline</h3>
        <ol className="space-y-2">
          {timeline.map((step) => (
            <li key={step.key} className="flex items-center gap-2 text-sm">
              <span
                className={
                  step.completed
                    ? "h-2 w-2 rounded-full bg-emerald-400"
                    : step.current
                      ? "h-2 w-2 rounded-full bg-cyan-300"
                      : "h-2 w-2 rounded-full bg-navy-600"
                }
                aria-hidden="true"
              />
              <span className={step.current ? "font-medium text-white" : "text-ink-muted"}>{step.label}</span>
            </li>
          ))}
        </ol>
      </Card>

      <Card className="space-y-2 p-5">
        <h3 className="text-base font-semibold text-white">Return label</h3>
        {shipment?.label_url ? (
          <p className="text-sm text-ink">
            <a className="text-cyan-300 underline" href={shipment.label_url} target="_blank" rel="noreferrer">
              Download label (mock)
            </a>
          </p>
        ) : (
          <p className="text-sm text-ink-muted">No label generated yet.</p>
        )}
        {shipment?.failure_reason ? (
          <p className="text-sm text-amber-100">Label error: {shipment.failure_reason}</p>
        ) : null}
      </Card>

      <Card className="space-y-2 p-5">
        <h3 className="text-base font-semibold text-white">Shipment tracking</h3>
        {shipment ? (
          <>
            <p className="text-sm text-ink-muted">
              {shipment.carrier} · {shipment.status.replaceAll("_", " ")}
            </p>
            <p className="text-sm text-ink">{shipment.tracking_number ?? "—"}</p>
          </>
        ) : (
          <p className="text-sm text-ink-muted">Tracking will appear after the label is ready.</p>
        )}
      </Card>

      <Card className="space-y-2 p-5">
        <h3 className="text-base font-semibold text-white">Refund status</h3>
        {refund ? (
          <>
            <p className="text-sm text-ink">
              {refund.amount} {refund.currency} · {refund.status}
            </p>
            {refund.failure_reason ? <p className="text-sm text-amber-100">{refund.failure_reason}</p> : null}
          </>
        ) : (
          <p className="text-sm text-ink-muted">Refund has not started.</p>
        )}
      </Card>

      <Card className="space-y-2 p-5">
        <h3 className="text-base font-semibold text-white">Notification history (mock email)</h3>
        {snapshot?.notifications.length ? (
          <ul className="space-y-2">
            {snapshot.notifications.map((row) => (
              <li key={row.id} className="border-b border-navy-700 pb-2 text-sm last:border-0">
                <p className="font-medium text-white">{row.subject}</p>
                <p className="text-ink-muted">{formatDateTime(new Date(row.created_at))} · {row.event_type}</p>
                <p className="text-ink">{row.body_preview}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-muted">No notifications yet.</p>
        )}
      </Card>

      {canManage ? (
        <Card className="flex flex-wrap gap-2 p-5">
          <Button disabled={busy} variant="secondary" onClick={() => run(() => requestReturnLabel(returnId))}>
            Request label
          </Button>
          <Button disabled={busy} variant="secondary" onClick={() => run(() => markInTransit(returnId))}>
            Mark in transit
          </Button>
          <Button disabled={busy} variant="secondary" onClick={() => run(() => markReceived(returnId))}>
            Mark received
          </Button>
          {requestedResolution === "EXCHANGE" ? (
            <Button disabled={busy} variant="secondary" onClick={() => run(() => startExchange(returnId))}>
              Start exchange
            </Button>
          ) : (
            <>
              <Button disabled={busy} variant="secondary" onClick={() => run(() => initiateRefund(returnId))}>
                Initiate refund
              </Button>
              <Button disabled={busy} variant="secondary" onClick={() => run(() => finalizeRefund(returnId))}>
                Finalize refund
              </Button>
            </>
          )}
          <Button
            disabled={busy}
            onClick={() => run(() => completeReturnFulfillment(returnId))}
          >
            Close return
          </Button>
        </Card>
      ) : null}
    </div>
  );
}