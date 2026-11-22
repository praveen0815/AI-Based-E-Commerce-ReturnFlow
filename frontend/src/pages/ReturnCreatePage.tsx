import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { EligibilityPanel } from "../components/EligibilityPanel";
import { ApiError } from "../services/api";
import { createReturn, getOrder } from "../services/commerce";
import { evaluateEligibility, requestEligibilityReview } from "../services/eligibility";
import type { OrderItem, OrderSummary, RequestedResolution } from "../types/commerce";
import type { EligibilityResult } from "../types/eligibility";

export function ReturnCreatePage() {
  const { orderId = "" } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderSummary | null>(null);
  const [reason, setReason] = useState("");
  const [description, setDescription] = useState("");
  const [resolution, setResolution] = useState<RequestedResolution>("REFUND");
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [eligibilityLoading, setEligibilityLoading] = useState(false);
  const [conditions, setConditions] = useState<Record<string, string>>({});

  useEffect(() => {
    getOrder(orderId)
      .then((item) => {
        setOrder(item);
        const initial: Record<string, number> = {};
        item.items?.forEach((line) => {
          if ((line.returnable_quantity ?? 0) > 0) {
            initial[line.id] = 1;
          }
        });
        setQuantities(initial);
      })
      .catch((caught: unknown) => {
        setError(caught instanceof ApiError ? caught.message : "Order not found.");
      })
      .finally(() => setLoading(false));
  }, [orderId]);

  function selectedLines(): Array<{ order_item_id: string; quantity: number }> {
    return Object.entries(quantities)
      .filter(([, qty]) => qty > 0)
      .map(([order_item_id, quantity]) => ({ order_item_id, quantity }));
  }

  async function onCheckEligibility() {
    if (!order) {
      return;
    }
    const items = selectedLines().map((line) => ({
      ...line,
      condition: conditions[line.order_item_id] || undefined,
    }));
    if (!items.length) {
      setError("Select at least one item before checking eligibility.");
      return;
    }
    setEligibilityLoading(true);
    setError("");
    try {
      const result = await evaluateEligibility({
        order_id: order.id,
        reason: reason.trim(),
        description: description.trim(),
        requested_resolution: resolution,
        items,
        include_ai_explanation: true,
      });
      setEligibility(result);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Eligibility check failed.");
    } finally {
      setEligibilityLoading(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order) {
      return;
    }
    const items = selectedLines();
    if (!items.length || reason.trim().length < 2 || description.trim().length < 2) {
      setError("Pick at least one item and complete the reason fields.");
      return;
    }
    setPending(true);
    setError("");
    try {
      const created = await createReturn({
        order_id: order.id,
        reason: reason.trim(),
        description: description.trim(),
        requested_resolution: resolution,
        items,
      });
      navigate(`/returns/${created.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The return could not be created.");
    } finally {
      setPending(false);
    }
  }

  if (loading) {
    return <Spinner label="Loading order" />;
  }
  if (!order) {
    return <Alert tone="danger" title="Order unavailable">{error || "Not found."}</Alert>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Return"
        title="Start a return"
        description={`Order ${order.order_number}. Only returnable quantities are offered.`}
      />
      {error ? <Alert tone="danger" title="Could not start the return">{error}</Alert> : null}
      <EligibilityPanel
        result={eligibility}
        loading={eligibilityLoading}
        onRequestReview={
          eligibility
            ? async () => {
                const updated = await requestEligibilityReview(eligibility.id);
                setEligibility(updated);
              }
            : undefined
        }
      />
      <form className="max-w-2xl space-y-4" onSubmit={onSubmit} noValidate>
        <Card className="space-y-3 p-5">
          <h2 className="text-base font-semibold text-white">Items</h2>
          {order.items?.map((line) => (
            <LineQuantity
              key={line.id}
              line={line}
              value={quantities[line.id] ?? 0}
              onChange={(value) => setQuantities((current) => ({ ...current, [line.id]: value }))}
              condition={conditions[line.id] ?? ""}
              onConditionChange={(value) => setConditions((current) => ({ ...current, [line.id]: value }))}
            />
          ))}
        </Card>
        <Input id="reason" label="Reason" value={reason} onChange={(event) => setReason(event.target.value)} />
        <Input
          id="description"
          label="Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <Select
          id="resolution"
          label="Requested resolution"
          value={resolution}
          options={[
            { value: "REFUND", label: "Refund" },
            { value: "EXCHANGE", label: "Exchange" },
            { value: "STORE_CREDIT", label: "Store credit" },
          ]}
          onChange={(event) => setResolution(event.target.value as RequestedResolution)}
        />
        <input className="sr-only" aria-hidden="true" readOnly value={order.id} />
        <div className="flex flex-wrap gap-3">
          <Button type="button" variant="secondary" disabled={eligibilityLoading} onClick={() => void onCheckEligibility()}>
            Check eligibility
          </Button>
          <Button type="submit" disabled={pending || eligibility?.decision === "INELIGIBLE"}>
            {pending ? "Submitting" : "Submit return"}
          </Button>
          <Link to={`/orders/${order.id}`} className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
            Back to order
          </Link>
        </div>
      </form>
    </div>
  );
}

function LineQuantity({
  line,
  value,
  onChange,
  condition,
  onConditionChange,
}: {
  line: OrderItem;
  value: number;
  onChange: (value: number) => void;
  condition: string;
  onConditionChange: (value: string) => void;
}) {
  const max = line.returnable_quantity ?? 0;
  if (max <= 0) {
    return null;
  }
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-navy-600 px-3 py-2">
      <div>
        <p className="text-sm font-medium text-white">{line.line_name}</p>
        <p className="text-xs text-ink-muted">Returnable {max}</p>
      </div>
      <Select
        id={`condition-${line.id}`}
        label="Condition"
        className="w-32"
        value={condition}
        options={[
          { value: "", label: "—" },
          { value: "NEW", label: "New" },
          { value: "OPENED", label: "Opened" },
          { value: "USED", label: "Used" },
          { value: "DAMAGED", label: "Damaged" },
        ]}
        onChange={(event) => onConditionChange(event.target.value)}
      />
      <Input
        id={`qty-${line.id}`}
        label="Qty"
        type="number"
        min={0}
        max={max}
        value={String(value)}
        className="w-24"
        onChange={(event) => onChange(Math.min(max, Math.max(0, Number(event.target.value) || 0)))}
      />
    </div>
  );
}