import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { getOrder } from "../services/commerce";
import type { OrderSummary } from "../types/commerce";
import { hasPermission } from "../utils/access";
import { formatDateTime } from "../utils/format";

export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const { activeMembership } = useAuth();
  const canReturn = hasPermission(activeMembership?.permissions, "return:create");
  const [order, setOrder] = useState<OrderSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getOrder(orderId)
      .then((item) => {
        if (!cancelled) {
          setOrder(item);
          setError("");
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Order not found.");
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
  }, [orderId]);

  if (loading) {
    return <Spinner label="Loading order" />;
  }
  if (!order) {
    return <Alert tone="danger" title="Order unavailable">{error || "Not found."}</Alert>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Order"
        title={order.order_number}
        description={
          order.is_sample
            ? "This order is labeled as development sample data."
            : `Placed ${formatDateTime(new Date(order.order_date))}.`
        }
        actions={
          canReturn && order.status === "FULFILLED" ? (
            <Link to={`/orders/${order.id}/return`}>
              <Button type="button">Start a return</Button>
            </Link>
          ) : undefined
        }
      />
      <Card className="space-y-3 p-5">
        <p className="text-sm text-ink-muted">
          Status {order.status} · Payment {order.payment_status} · Total {order.currency} {order.total_amount}
        </p>
        {order.fulfillment_date ? (
          <p className="text-sm text-ink-muted">
            Fulfilled {formatDateTime(new Date(order.fulfillment_date))}
          </p>
        ) : null}
        {order.return_window_ends_at ? (
          <p className="text-sm text-ink-muted">
            Return window ends {formatDateTime(new Date(order.return_window_ends_at))}
          </p>
        ) : null}
      </Card>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Items</h2>
        {order.items?.map((item) => (
          <Card key={item.id} className="p-4">
            <p className="font-medium text-white">{item.line_name}</p>
            <p className="text-sm text-ink-muted">
              SKU {item.sku} · Qty {item.quantity} · {order.currency} {item.unit_price}
            </p>
            {item.returnable_quantity != null ? (
              <p className="mt-1 text-xs text-ink-faint">Returnable qty {item.returnable_quantity}</p>
            ) : null}
          </Card>
        ))}
      </section>
    </div>
  );
}