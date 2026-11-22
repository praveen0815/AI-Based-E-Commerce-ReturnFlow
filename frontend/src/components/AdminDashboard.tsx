import { Link } from "react-router-dom";

import type { AdminAnalytics } from "../types/analytics";
import { BarChart } from "./charts/BarChart";
import { TimeSeriesChart } from "./charts/TimeSeriesChart";
import { Card } from "./ui/Card";
import { MetricCard } from "./ui/MetricCard";
import { usePreferences } from "../hooks/usePreferences";
import { cn } from "../utils/cn";

export function AdminDashboard({ data }: { data: AdminAnalytics }) {
  const { density } = usePreferences();
  const { kpis } = data;

  const metrics = [
    { id: "orders", label: "Total orders", value: String(kpis.total_orders), hint: "Fulfilled and open orders in this store." },
    {
      id: "returns",
      label: "Return requests",
      value: String(kpis.total_return_requests),
      hint: "All return cases in PostgreSQL.",
    },
    { id: "pending", label: "Pending review", value: String(kpis.pending_review), hint: "Requested or under review." },
    { id: "approved", label: "Approved returns", value: String(kpis.approved_returns), hint: "Approved or in fulfillment." },
    { id: "rejected", label: "Rejected", value: String(kpis.rejected_returns), hint: "Staff denied." },
    { id: "refunds", label: "Completed refunds", value: String(kpis.completed_refunds), hint: "Mock refunds marked completed." },
    {
      id: "value",
      label: "Refund value",
      value: kpis.refund_value,
      hint: "Sum of completed mock refunds.",
    },
    {
      id: "rate",
      label: "Return rate",
      value: kpis.return_rate_percent != null ? `${kpis.return_rate_percent}%` : "—",
      hint: "Returns ÷ orders.",
    },
  ];

  const aiLegend = [
    { label: "Aligned", count: data.ai_human_comparison.aligned },
    { label: "Mismatches", count: data.ai_human_comparison.mismatches },
    { label: "Escalated / pending", count: data.ai_human_comparison.escalated_without_decision },
    { label: "AI approve → approved", count: data.ai_human_comparison.ai_approve_actual_approve },
    { label: "AI deny → rejected", count: data.ai_human_comparison.ai_deny_actual_deny },
  ];

  return (
    <div className="space-y-6">
      <section aria-label="Key performance indicators">
        <div className={cn("grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4", density === "compact" ? "gap-3" : "gap-4")}>
          {metrics.map((metric) => (
            <MetricCard key={metric.id} label={metric.label} value={metric.value} hint={metric.hint} density={density} />
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <TimeSeriesChart title="Returns over time" points={data.returns_over_time} />
        </Card>
        <Card className="p-5">
          <TimeSeriesChart title="Refund amounts over time" points={data.refund_amounts_over_time} />
        </Card>
        <Card className="p-5">
          <BarChart
            title="Return reasons"
            items={data.return_reasons.map((r) => ({ label: r.label, count: r.count }))}
          />
        </Card>
        <Card className="p-5">
          <BarChart
            title="Return status distribution"
            items={data.return_status_distribution.map((r) => ({ label: r.label, count: r.count }))}
          />
        </Card>
        <Card className="p-5">
          <BarChart
            title="Product return frequency"
            items={data.product_return_frequency.map((r) => ({
              label: `${r.line_name} (${r.sku})`,
              count: r.return_quantity,
            }))}
            emptyLabel="No return line items yet."
          />
        </Card>
        <Card className="space-y-3 p-5">
          <h2 className="text-sm font-semibold text-white">Return processing duration</h2>
          <p className="text-sm text-ink-muted">
            Sample size {data.processing_duration.sample_size} returns in this store.
          </p>
          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-ink-muted">Avg. hours to decision</dt>
              <dd className="font-mono text-white">{data.processing_duration.avg_hours_to_decision ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink-muted">Avg. hours to completion</dt>
              <dd className="font-mono text-white">{data.processing_duration.avg_hours_to_completion ?? "—"}</dd>
            </div>
          </dl>
        </Card>
        <Card className="p-5 lg:col-span-2">
          <BarChart
            title="AI recommendation vs human outcome"
            items={aiLegend}
            emptyLabel="Run AI reviews to populate this chart."
          />
          <p className="mt-3 text-xs text-ink-muted">
            Based on {data.ai_human_comparison.runs_with_recommendation} completed review outputs with a finalization
            recommendation. Only returns with a resolved staff outcome are compared.
          </p>
        </Card>
      </section>

      <section className="flex flex-wrap gap-3">
        <Link to="/returns/queue" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          Open return queue
        </Link>
        <Link to="/returns" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          All returns
        </Link>
        <Link to="/orders" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          Orders
        </Link>
      </section>
    </div>
  );
}
