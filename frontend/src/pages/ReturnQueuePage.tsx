import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { listReturnQueue } from "../services/commerce";
import type { ReturnStatus, ReturnSummary } from "../types/commerce";
import { formatDateTime } from "../utils/format";

const QUEUE_STATUSES: ReturnStatus[] = [
  "REQUESTED",
  "UNDER_REVIEW",
  "APPROVED",
  "LABEL_PENDING",
  "LABEL_GENERATED",
  "RETURN_IN_TRANSIT",
  "RECEIVED",
  "REFUND_PENDING",
  "REFUND_PROCESSING",
];

export function ReturnQueuePage() {
  const { storeId } = useAuth();
  const [returns, setReturns] = useState<ReturnSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<string>("");
  const [sort, setSort] = useState("submitted_at");
  const [direction, setDirection] = useState<"asc" | "desc">("asc");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listReturnQueue({
        page,
        page_size: pageSize,
        sort,
        direction,
        status: status || undefined,
        q: query.trim() || undefined,
      });
      setReturns(result.items);
      setTotal(result.total);
      setError("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Queue could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [page, query, sort, direction, status]);

  useEffect(() => {
    load();
  }, [load, storeId]);

  function onSearch(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    load();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Return queue"
        description="Search, filter, and sort open returns. Each row links to eligibility, AI review, and fulfillment controls."
      />
      {error ? <Alert tone="danger" title="Could not load the queue">{error}</Alert> : null}

      <form className="grid gap-3 lg:grid-cols-4" onSubmit={onSearch}>
        <Input
          id="queue-search"
          label="Search"
          value={query}
          placeholder="Return #, order #, email"
          onChange={(event) => setQuery(event.target.value)}
        />
        <Select
          id="queue-status"
          label="Status"
          value={status}
          options={[{ value: "", label: "All open statuses" }, ...QUEUE_STATUSES.map((s) => ({ value: s, label: s.replaceAll("_", " ") }))]}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
        />
        <Select
          id="queue-sort"
          label="Sort"
          value={sort}
          options={[
            { value: "submitted_at", label: "Submitted" },
            { value: "return_number", label: "Return number" },
            { value: "status", label: "Status" },
          ]}
          onChange={(event) => setSort(event.target.value)}
        />
        <Select
          id="queue-direction"
          label="Direction"
          value={direction}
          options={[
            { value: "asc", label: "Ascending" },
            { value: "desc", label: "Descending" },
          ]}
          onChange={(event) => setDirection(event.target.value as "asc" | "desc")}
        />
        <div className="lg:col-span-4">
          <Button type="submit">Apply filters</Button>
        </div>
      </form>

      {loading ? <Spinner label="Loading queue" /> : null}
      {!loading && returns.length === 0 ? (
        <EmptyState title="Queue is clear" description="No open returns match these filters." />
      ) : null}

      <div className="space-y-3">
        {returns.map((item) => (
          <Link
            key={item.id}
            to={`/returns/${item.id}`}
            className="block rounded-2xl border border-navy-600 bg-navy-900/90 p-4 hover:border-cyan-400/40"
          >
            <p className="font-semibold text-white">{item.return_number}</p>
            <p className="text-sm text-ink-muted">
              {item.status.replaceAll("_", " ")} · {item.customer_email} · {formatDateTime(new Date(item.submitted_at))}
            </p>
          </Link>
        ))}
      </div>

      {!loading && total > pageSize ? (
        <nav className="flex items-center justify-between gap-3" aria-label="Queue pagination">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <p className="text-sm text-ink-muted">
            Page {page} of {totalPages} · {total} open
          </p>
          <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </nav>
      ) : null}
    </div>
  );
}