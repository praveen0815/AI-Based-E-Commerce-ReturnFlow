import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { ReturnTimeline } from "../components/ReturnTimeline";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { AiReviewPanel } from "../components/AiReviewPanel";
import { EligibilityPanel } from "../components/EligibilityPanel";
import { ReturnFulfillmentPanel } from "../components/ReturnFulfillmentPanel";
import { cancelReturn, getReturn, getReturnHistory, updateReturnStatus } from "../services/commerce";
import { explainEligibility, latestReturnEligibility } from "../services/eligibility";
import type { EligibilityResult } from "../types/eligibility";
import type { ReturnStatus, ReturnStatusEvent, ReturnSummary } from "../types/commerce";
import { hasPermission } from "../utils/access";
import { formatDateTime } from "../utils/format";

const STAFF_STATUSES: ReturnStatus[] = [
  "UNDER_REVIEW",
  "APPROVED",
  "LABEL_PENDING",
  "LABEL_GENERATED",
  "RETURN_IN_TRANSIT",
  "RECEIVED",
  "REFUND_PENDING",
  "REFUND_PROCESSING",
  "REFUND_COMPLETED",
  "EXCHANGE_PROCESSING",
  "COMPLETED",
  "REJECTED",
  "CANCELLED",
];

export function ReturnDetailPage() {
  const { returnId = "" } = useParams();
  const { activeMembership } = useAuth();
  const canManage = hasPermission(activeMembership?.permissions, "return:manage");
  const canCancel = hasPermission(activeMembership?.permissions, "return:create");
  const [item, setItem] = useState<ReturnSummary | null>(null);
  const [events, setEvents] = useState<ReturnStatusEvent[]>([]);
  const [nextStatus, setNextStatus] = useState<ReturnStatus>("UNDER_REVIEW");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  async function refresh() {
    const [detail, history, latest] = await Promise.all([
      getReturn(returnId),
      getReturnHistory(returnId),
      latestReturnEligibility(returnId).catch(() => null),
    ]);
    setItem(detail);
    setEvents(history);
    setEligibility(latest);
  }

  useEffect(() => {
    refresh()
      .catch((caught: unknown) => {
        setError(caught instanceof ApiError ? caught.message : "Return not found.");
      })
      .finally(() => setLoading(false));
  }, [returnId]);

  async function onCancel() {
    setError("");
    try {
      const updated = await cancelReturn(returnId);
      setItem(updated);
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Cancellation failed.");
    }
  }

  async function onAdvance() {
    setError("");
    try {
      const updated = await updateReturnStatus(returnId, { status: nextStatus, note: note.trim() || undefined });
      setItem(updated);
      setNote("");
      await refresh();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Status change failed.");
    }
  }

  if (loading) {
    return <Spinner label="Loading return" />;
  }
  if (!item) {
    return <Alert tone="danger" title="Return unavailable">{error || "Not found."}</Alert>;
  }

  const cancellable = item.status === "REQUESTED" || item.status === "UNDER_REVIEW";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Return"
        title={item.return_number}
        description={`Order ${item.order_number} · submitted ${formatDateTime(new Date(item.submitted_at))}`}
      />
      {error ? <Alert tone="danger" title="Action failed">{error}</Alert> : null}
      <EligibilityPanel
        result={eligibility}
        onExplain={
          eligibility && canManage
            ? async () => {
                setExplainLoading(true);
                try {
                  const updated = await explainEligibility(eligibility.id);
                  setEligibility(updated);
                } catch (caught) {
                  setError(caught instanceof ApiError ? caught.message : "Explanation failed.");
                } finally {
                  setExplainLoading(false);
                }
              }
            : undefined
        }
        explainLoading={explainLoading}
      />
      <Card className="space-y-2 p-5">
        <p className="text-sm text-ink-muted">Status {item.status.replaceAll("_", " ")}</p>
        <p className="text-sm text-ink-muted">Resolution {item.requested_resolution.replaceAll("_", " ")}</p>
        <p className="text-sm text-ink">{item.reason}</p>
        <p className="text-sm text-ink-muted">{item.description}</p>
        {item.internal_notes && canManage ? (
          <p className="text-sm text-amber-100">Internal notes: {item.internal_notes}</p>
        ) : null}
      </Card>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Items</h2>
        {item.items?.map((line) => (
          <Card key={line.id} className="p-4">
            <p className="font-medium text-white">{line.line_name}</p>
            <p className="text-sm text-ink-muted">
              SKU {line.sku} · Qty {line.quantity}
            </p>
          </Card>
        ))}
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Timeline</h2>
        <ReturnTimeline events={events} />
      </section>
      {canCancel && cancellable ? (
        <Button variant="secondary" onClick={onCancel}>
          Cancel return
        </Button>
      ) : null}
      {canManage ? <AiReviewPanel returnId={returnId} canManage={canManage} /> : null}
      <ReturnFulfillmentPanel
        returnId={returnId}
        canManage={canManage}
        requestedResolution={item.requested_resolution}
        onStatusChange={refresh}
      />
      {canManage && (item.status === "REQUESTED" || item.status === "UNDER_REVIEW") ? (
        <Card className="flex flex-wrap gap-2 p-5">
          <h2 className="w-full text-base font-semibold text-white">Quick review</h2>
          <Button
            onClick={async () => {
              setError("");
              try {
                const updated = await updateReturnStatus(returnId, { status: "APPROVED", note: "Approved from queue" });
                setItem(updated);
                await refresh();
              } catch (caught) {
                setError(caught instanceof ApiError ? caught.message : "Approval failed.");
              }
            }}
          >
            Approve
          </Button>
          <Button
            variant="secondary"
            onClick={async () => {
              setError("");
              try {
                const updated = await updateReturnStatus(returnId, { status: "REJECTED", note: "Rejected from queue" });
                setItem(updated);
                await refresh();
              } catch (caught) {
                setError(caught instanceof ApiError ? caught.message : "Rejection failed.");
              }
            }}
          >
            Reject
          </Button>
        </Card>
      ) : null}
      {canManage ? (
        <Card className="space-y-3 p-5">
          <h2 className="text-base font-semibold text-white">Review</h2>
          <Select
            id="return-status"
            label="Next status"
            value={nextStatus}
            options={STAFF_STATUSES.map((status) => ({ value: status, label: status.replaceAll("_", " ") }))}
            onChange={(event) => setNextStatus(event.target.value as ReturnStatus)}
          />
          <textarea
            id="return-note"
            aria-label="Note"
            className="focus-ring w-full rounded-lg border border-navy-600 bg-navy-950 px-3 py-2 text-sm text-ink"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional note for the timeline"
          />
          <Button onClick={onAdvance}>Apply status</Button>
        </Card>
      ) : null}
    </div>
  );
}