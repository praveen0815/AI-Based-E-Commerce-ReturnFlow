import { useEffect, useState } from "react";

import { AdminDashboard } from "../components/AdminDashboard";
import { CustomerDashboard } from "../components/CustomerDashboard";
import { PageHeader } from "../components/PageHeader";
import { PlatformStatusCard } from "../components/PlatformStatusCard";
import { Alert } from "../components/ui/Alert";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { fetchAdminAnalytics, fetchCustomerAnalytics } from "../services/analytics";
import type { AdminAnalytics, CustomerAnalytics } from "../types/analytics";
import { hasPermission } from "../utils/access";

export function DashboardPage() {
  const { storeId, activeMembership } = useAuth();
  const staff = hasPermission(activeMembership?.permissions, "return:read");
  const customerOnly = hasPermission(activeMembership?.permissions, "return:read_own") && !staff;
  const [days, setDays] = useState("30");
  const [adminData, setAdminData] = useState<AdminAnalytics | null>(null);
  const [customerData, setCustomerData] = useState<CustomerAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    const task = staff
      ? fetchAdminAnalytics(Number(days))
      : customerOnly
        ? fetchCustomerAnalytics()
        : Promise.reject(new ApiError("Select a store with return access.", { status: 403, code: "forbidden" }));

    task
      .then((data) => {
        if (cancelled) {
          return;
        }
        if (staff) {
          setAdminData(data as AdminAnalytics);
          setCustomerData(null);
        } else {
          setCustomerData(data as CustomerAnalytics);
          setAdminData(null);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Dashboard could not be loaded.");
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
  }, [storeId, staff, customerOnly, days]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Dashboard"
        title={staff ? "Store operations" : "Your returns"}
        description={
          staff
            ? "KPIs and charts are calculated from live PostgreSQL data for the selected store."
            : "Orders, returns, and refunds scoped to your account."
        }
        actions={
          staff ? (
            <Select
              id="analytics-window"
              label="Chart window (days)"
              value={days}
              options={[
                { value: "30", label: "Last 30 days" },
                { value: "90", label: "Last 90 days" },
                { value: "180", label: "Last 180 days" },
              ]}
              onChange={(event) => setDays(event.target.value)}
            />
          ) : undefined
        }
      />

      {error ? <Alert tone="danger" title="Dashboard">{error}</Alert> : null}
      {loading ? <Spinner label="Loading dashboard" /> : null}

      <PlatformStatusCard />

      {!loading && staff && adminData ? <AdminDashboard data={adminData} /> : null}
      {!loading && customerOnly && customerData ? <CustomerDashboard data={customerData} /> : null}
    </div>
  );
}