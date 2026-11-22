import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { listMyOrders, listOrders, loadSampleCommerce, searchOrders } from "../services/commerce";
import type { OrderSummary } from "../types/commerce";
import { hasPermission } from "../utils/access";
import { formatDateTime } from "../utils/format";

export function OrdersPage() {
  const { activeMembership } = useAuth();
  const staffView = hasPermission(activeMembership?.permissions, "order:read");
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [seedMessage, setSeedMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const loader = staffView ? listOrders() : listMyOrders();
    loader
      .then((page) => {
        if (!cancelled) {
          setOrders(page.items);
          setError("");
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Orders could not be loaded.");
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
  }, [staffView]);

  async function onSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }
    setLoading(true);
    try {
      const page = await searchOrders(query.trim());
      setOrders(page.items);
      setError("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onLoadSample() {
    setSeedMessage("");
    try {
      const body = await loadSampleCommerce();
      setSeedMessage(body.message);
      const page = staffView ? await listOrders() : await listMyOrders();
      setOrders(page.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Sample data was not created.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Commerce"
        title={staffView ? "Store orders" : "Your orders"}
        description={
          staffView
            ? "Every row is scoped to the store selected in the sidebar."
            : "You only see orders placed under your account in this store."
        }
        actions={
          staffView ? (
            <Button variant="secondary" onClick={onLoadSample}>
              Load sample orders
            </Button>
          ) : undefined
        }
      />
      {seedMessage ? <Alert tone="info" title="Development sample">{seedMessage}</Alert> : null}
      {error ? <Alert tone="danger" title="Could not load orders">{error}</Alert> : null}
      {staffView ? (
        <form className="max-w-xl" onSubmit={onSearch}>
          <div className="flex gap-2">
            <Input
              id="order-search"
              label="Search"
              className="flex-1"
              value={query}
              placeholder="Order number or customer email"
              onChange={(event) => setQuery(event.target.value)}
            />
            <Button type="submit" className="mt-7">
              Search
            </Button>
          </div>
        </form>
      ) : null}
      {loading ? <Spinner label="Loading orders" /> : null}
      {!loading && orders.length === 0 ? (
        <EmptyState
          title="No orders yet"
          description="Orders appear here after they exist in PostgreSQL for this store. Owners can load labeled sample data in development."
        />
      ) : null}
      <div className="space-y-3">
        {orders.map((order) => (
          <Card key={order.id} className="p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-semibold text-white">
                  {order.order_number}
                  {order.is_sample ? <span className="ml-2 text-xs text-amber-300">sample</span> : null}
                </p>
                <p className="text-sm text-ink-muted">
                  {formatDateTime(new Date(order.order_date))} · {order.status}
                  {staffView && order.customer_email ? ` · ${order.customer_email}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-sm text-ink">
                  {order.currency} {order.total_amount}
                </p>
                <Link to={`/orders/${order.id}`} className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
                  View
                </Link>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}