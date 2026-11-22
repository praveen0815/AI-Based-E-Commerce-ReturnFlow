import type { SuccessResponse } from "../types/api";
import type {
  OrderSummary,
  Paginated,
  RequestedResolution,
  ReturnStatus,
  ReturnStatusEvent,
  ReturnSummary,
} from "../types/commerce";
import { api } from "./api";

export async function listOrders(params: Record<string, string | number | undefined> = {}): Promise<Paginated<OrderSummary>> {
  const response = await api.get<SuccessResponse<Paginated<OrderSummary>>>("/api/v1/stores/current/orders", { params });
  return response.data.data;
}

export async function searchOrders(q: string, page = 1): Promise<Paginated<OrderSummary>> {
  const response = await api.get<SuccessResponse<Paginated<OrderSummary>>>("/api/v1/stores/current/orders/search", {
    params: { q, page },
  });
  return response.data.data;
}

export async function listMyOrders(page = 1): Promise<Paginated<OrderSummary>> {
  const response = await api.get<SuccessResponse<Paginated<OrderSummary>>>("/api/v1/stores/current/orders/me", {
    params: { page },
  });
  return response.data.data;
}

export async function getOrder(orderId: string): Promise<OrderSummary> {
  const response = await api.get<SuccessResponse<OrderSummary>>(`/api/v1/stores/current/orders/${orderId}`);
  return response.data.data;
}

export async function listReturns(params: Record<string, string | number | undefined> = {}): Promise<Paginated<ReturnSummary>> {
  const response = await api.get<SuccessResponse<Paginated<ReturnSummary>>>("/api/v1/stores/current/returns", { params });
  return response.data.data;
}

export async function listReturnQueue(
  params: Record<string, string | number | undefined> = {},
): Promise<Paginated<ReturnSummary>> {
  const response = await api.get<SuccessResponse<Paginated<ReturnSummary>>>("/api/v1/stores/current/returns/queue", {
    params,
  });
  return response.data.data;
}

export async function getReturn(returnId: string): Promise<ReturnSummary> {
  const response = await api.get<SuccessResponse<ReturnSummary>>(`/api/v1/stores/current/returns/${returnId}`);
  return response.data.data;
}

export async function getReturnHistory(returnId: string): Promise<ReturnStatusEvent[]> {
  const response = await api.get<SuccessResponse<{ events: ReturnStatusEvent[] }>>(
    `/api/v1/stores/current/returns/${returnId}/history`,
  );
  return response.data.data.events;
}

export async function createReturn(payload: {
  order_id: string;
  reason: string;
  description: string;
  requested_resolution: RequestedResolution;
  items: Array<{ order_item_id: string; quantity: number }>;
}): Promise<ReturnSummary> {
  const response = await api.post<SuccessResponse<ReturnSummary>>("/api/v1/stores/current/returns", payload);
  return response.data.data;
}

export async function cancelReturn(returnId: string): Promise<ReturnSummary> {
  const response = await api.post<SuccessResponse<ReturnSummary>>(`/api/v1/stores/current/returns/${returnId}/cancel`);
  return response.data.data;
}

export async function updateReturnStatus(
  returnId: string,
  payload: { status: ReturnStatus; note?: string; internal_notes?: string },
): Promise<ReturnSummary> {
  const response = await api.patch<SuccessResponse<ReturnSummary>>(
    `/api/v1/stores/current/returns/${returnId}/status`,
    payload,
  );
  return response.data.data;
}

export async function loadSampleCommerce(): Promise<{ order_number: string; is_sample: boolean; message: string }> {
  const response = await api.post<SuccessResponse<{ order_number: string; is_sample: boolean; message: string }>>(
    "/api/v1/stores/current/dev/sample-commerce",
  );
  return response.data.data;
}