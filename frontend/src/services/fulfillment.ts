import type { SuccessResponse } from "../types/api";
import type { FulfillmentActionResult, FulfillmentSnapshot } from "../types/fulfillment";
import { api } from "./api";

function idempotencyHeader(key: string): Record<string, string> {
  return { "Idempotency-Key": key };
}

function newKey(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`;
}

export async function getFulfillment(returnId: string): Promise<FulfillmentSnapshot> {
  const response = await api.get<SuccessResponse<FulfillmentSnapshot>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment`,
  );
  return response.data.data;
}

export async function requestReturnLabel(returnId: string, key?: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/label`,
    {},
    { headers: idempotencyHeader(key ?? newKey("label")) },
  );
  return response.data.data;
}

export async function markInTransit(returnId: string, key?: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/shipment/in-transit`,
    {},
    { headers: idempotencyHeader(key ?? newKey("transit")) },
  );
  return response.data.data;
}

export async function markReceived(returnId: string, key?: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/shipment/received`,
    {},
    { headers: idempotencyHeader(key ?? newKey("received")) },
  );
  return response.data.data;
}

export async function initiateRefund(returnId: string, key?: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/refund`,
    {},
    { headers: idempotencyHeader(key ?? newKey("refund")) },
  );
  return response.data.data;
}

export async function finalizeRefund(returnId: string, key?: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/refund/finalize`,
    {},
    { headers: idempotencyHeader(key ?? newKey("refund-finalize")) },
  );
  return response.data.data;
}

export async function startExchange(returnId: string, key?: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/exchange`,
    {},
    { headers: idempotencyHeader(key ?? newKey("exchange")) },
  );
  return response.data.data;
}

export async function completeReturnFulfillment(returnId: string): Promise<FulfillmentActionResult> {
  const response = await api.post<SuccessResponse<FulfillmentActionResult>>(
    `/api/v1/stores/current/returns/${returnId}/fulfillment/complete`,
    {},
  );
  return response.data.data;
}