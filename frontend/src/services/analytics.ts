import type { SuccessResponse } from "../types/api";
import type { AdminAnalytics, CustomerAnalytics } from "../types/analytics";
import { api } from "./api";

export async function fetchAdminAnalytics(days = 30): Promise<AdminAnalytics> {
  const response = await api.get<SuccessResponse<AdminAnalytics>>("/api/v1/stores/current/analytics/admin", {
    params: { days },
  });
  return response.data.data;
}

export async function fetchCustomerAnalytics(): Promise<CustomerAnalytics> {
  const response = await api.get<SuccessResponse<CustomerAnalytics>>("/api/v1/stores/current/analytics/me");
  return response.data.data;
}