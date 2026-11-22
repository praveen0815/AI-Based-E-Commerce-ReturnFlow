import type { ReturnStatus } from "./commerce";

export type ShipmentProviderStatus = "LABEL_PENDING" | "LABEL_READY" | "IN_TRANSIT" | "DELIVERED" | "FAILED";
export type RefundProviderStatus =
  | "ELIGIBLE"
  | "INELIGIBLE"
  | "PENDING"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export interface ShipmentPublic {
  id: string;
  status: ShipmentProviderStatus;
  carrier: string;
  tracking_number: string | null;
  label_url: string | null;
  provider_ref: string;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface RefundPublic {
  id: string;
  status: RefundProviderStatus;
  amount: string;
  currency: string;
  provider_ref: string;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationPublic {
  id: string;
  event_type: string;
  recipient_email: string;
  subject: string;
  body_preview: string;
  mock_delivered: boolean;
  created_at: string;
}

export interface FulfillmentTimelineStep {
  key: string;
  label: string;
  completed: boolean;
  current: boolean;
}

export interface FulfillmentSnapshot {
  return_id: string;
  return_status: ReturnStatus;
  shipment: ShipmentPublic | null;
  refund: RefundPublic | null;
  notifications: NotificationPublic[];
  timeline: FulfillmentTimelineStep[];
}

export interface FulfillmentActionResult {
  return_status: ReturnStatus;
  shipment?: ShipmentPublic | null;
  refund?: RefundPublic | null;
  message?: string | null;
}