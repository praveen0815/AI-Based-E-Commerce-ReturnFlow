export type OrderStatus = "PENDING" | "PAID" | "FULFILLED" | "CANCELLED";
export type PaymentStatus = "PENDING" | "PAID" | "PARTIALLY_REFUNDED" | "REFUNDED" | "FAILED";
export type ReturnStatus =
  | "REQUESTED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "LABEL_PENDING"
  | "LABEL_GENERATED"
  | "RETURN_IN_TRANSIT"
  | "RECEIVED"
  | "REFUND_PENDING"
  | "REFUND_PROCESSING"
  | "REFUND_COMPLETED"
  | "COMPLETED"
  | "REJECTED"
  | "CANCELLED"
  | "EXCHANGE_PROCESSING";
export type RequestedResolution = "REFUND" | "EXCHANGE" | "STORE_CREDIT";

export interface OrderItem {
  id: string;
  product_id: string | null;
  line_name: string;
  sku: string;
  quantity: number;
  unit_price: string;
  item_metadata: Record<string, unknown>;
  returnable_quantity?: number | null;
}

export interface OrderSummary {
  id: string;
  order_number: string;
  customer_user_id: string;
  customer_email?: string;
  customer_display_name?: string;
  order_date: string;
  fulfillment_date?: string | null;
  status: OrderStatus;
  payment_status: PaymentStatus;
  currency: string;
  total_amount: string;
  is_sample: boolean;
  return_window_days: number;
  return_window_ends_at?: string | null;
  items?: OrderItem[];
}

export interface ReturnItem {
  id: string;
  order_item_id: string;
  line_name: string;
  sku: string;
  quantity: number;
}

export interface ReturnSummary {
  id: string;
  return_number: string;
  order_id: string;
  order_number: string;
  customer_user_id: string;
  customer_email?: string;
  reason: string;
  description: string;
  requested_resolution: RequestedResolution;
  status: ReturnStatus;
  submitted_at: string;
  decision_at?: string | null;
  return_window_days: number;
  return_window_ends_at: string;
  internal_notes?: string | null;
  items?: ReturnItem[];
}

export interface ReturnStatusEvent {
  id: string;
  from_status: ReturnStatus | null;
  to_status: ReturnStatus;
  actor_email?: string | null;
  note?: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}