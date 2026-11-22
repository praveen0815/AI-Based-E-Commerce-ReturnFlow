import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../hooks/useAuth";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Spinner } from "../components/ui/Spinner";
import { ApiError } from "../services/api";
import { listReturns } from "../services/commerce";
import type { ReturnSummary } from "../types/commerce";
import { hasPermission } from "../utils/access";
import { formatDateTime } from "../utils/format";

export function ActivityPage() {
  const { storeId, activeMembership } = useAuth();
  const staff = hasPermission(activeMembership?.permissions, "return:read");
  const [recent, setRecent] = useState<ReturnSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listReturns({ page: 1, page_size: 8, sort: "submitted_at", direction: "desc" })
      .then((page) => {
        if (!cancelled) {
          setRecent(page.items);
          setError("");
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Activity could not be loaded.");
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
        eyebrow="Activity"
        title="Recent returns"
        description="Latest return requests for this store, loaded from the returns API."
      />
      {error ? <Alert tone="danger" title="Activity">{error}</Alert> : null}
      {loading ? <Spinner label="Loading activity" /> : null}
      {!loading && recent.length === 0 ? (
        <EmptyState
          title="No return activity"
          description="Returns appear here once customers submit them."
          action={
            <Link to="/orders">
              <Button type="button" variant="secondary">
                Browse orders
              </Button>
            </Link>
          }
        />
      ) : null}
      <ul className="space-y-2">
        {recent.map((item) => (
          <li key={item.id}>
            <Link to={`/returns/${item.id}`} className="block rounded-xl border border-navy-600 px-4 py-3 hover:border-cyan-400/40">
              <p className="font-medium text-white">{item.return_number}</p>
              <p className="text-sm text-ink-muted">
                {item.status.replaceAll("_", " ")} · {formatDateTime(new Date(item.submitted_at))}
              </p>
            </Link>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-3">
        <Link to="/returns" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          All returns
        </Link>
        {staff ? (
          <Link to="/returns/queue" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
            Return queue
          </Link>
        ) : null}
      </div>
    </div>
  );
}