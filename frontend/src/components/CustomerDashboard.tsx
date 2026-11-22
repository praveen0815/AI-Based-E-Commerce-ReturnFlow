import { Link } from "react-router-dom";

import type { CustomerAnalytics } from "../types/analytics";
import { BarChart } from "./charts/BarChart";
import { Card } from "./ui/Card";
import { MetricCard } from "./ui/MetricCard";
import { usePreferences } from "../hooks/usePreferences";
import { cn } from "../utils/cn";
import { formatDateTime } from "../utils/format";

export function CustomerDashboard({ data }: { data: CustomerAnalytics }) {
  const { density } = usePreferences();
  const { kpis } = data;
  const currency = kpis.currency ?? "USD";

  return (
    <div className="space-y-6">
      <section
        aria-label="Your account summary"
        className={cn("grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4", density === "compact" ? "gap-3" : "gap-4")}
      >
        <MetricCard label="Your orders" value={String(kpis.order_count)} hint="Orders in this store." density={density} />
        <MetricCard label="Active returns" value={String(kpis.active_returns)} hint="Open cases." density={density} />
        <MetricCard label="Closed returns" value={String(kpis.completed_returns)} hint="Completed or rejected." density={density} />
        <MetricCard
          label="Refund total"
          value={`${currency} ${kpis.refund_total}`}
          hint="Completed mock refunds."
          density={density}
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <BarChart
            title="Return status"
            items={data.active_return_statuses.map((r) => ({ label: r.label, count: r.count }))}
            emptyLabel="You have no returns yet."
          />
        </Card>
        <Card className="space-y-3 p-5">
          <h2 className="text-sm font-semibold text-white">Refund history</h2>
          {data.refunds.length === 0 ? (
            <p className="text-sm text-ink-muted">Refunds appear after staff completes the mock refund flow.</p>
          ) : (
            <ul className="space-y-2">
              {data.refunds.map((row) => (
                <li key={`${row.return_number}-${row.completed_at}`} className="border-b border-navy-700 pb-2 text-sm last:border-0">
                  <p className="font-medium text-white">
                    {row.return_number} · {row.currency} {row.amount}
                  </p>
                  <p className="text-ink-muted">
                    {row.status}
                    {row.completed_at ? ` · ${formatDateTime(new Date(row.completed_at))}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <section className="flex flex-wrap gap-3">
        <Link to="/orders" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          View orders
        </Link>
        <Link to="/returns" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          My returns
        </Link>
        <Link to="/policy" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          Policy assistant
        </Link>
      </section>
    </div>
  );
}