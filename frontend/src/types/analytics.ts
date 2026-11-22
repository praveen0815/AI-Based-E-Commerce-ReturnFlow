export interface AdminKpis {
  total_orders: number;
  total_return_requests: number;
  pending_review: number;
  approved_returns: number;
  rejected_returns: number;
  completed_refunds: number;
  refund_value: string;
  return_rate_percent: string | null;
}

export interface TimeSeriesPoint {
  bucket: string;
  value: string;
}

export interface CountSeriesPoint {
  label: string;
  count: number;
}

export interface ProductReturnFrequency {
  sku: string;
  line_name: string;
  return_quantity: number;
}

export interface ProcessingDurationStats {
  sample_size: number;
  avg_hours_to_decision: string | null;
  avg_hours_to_completion: string | null;
}

export interface AiHumanComparison {
  runs_with_recommendation: number;
  aligned: number;
  ai_approve_actual_approve: number;
  ai_deny_actual_deny: number;
  mismatches: number;
  escalated_without_decision: number;
}

export interface AdminAnalytics {
  kpis: AdminKpis;
  returns_over_time: TimeSeriesPoint[];
  return_reasons: CountSeriesPoint[];
  return_status_distribution: CountSeriesPoint[];
  refund_amounts_over_time: TimeSeriesPoint[];
  product_return_frequency: ProductReturnFrequency[];
  processing_duration: ProcessingDurationStats;
  ai_human_comparison: AiHumanComparison;
}

export interface CustomerKpis {
  order_count: number;
  active_returns: number;
  completed_returns: number;
  refund_total: string;
  currency: string | null;
}

export interface CustomerRefundRow {
  return_number: string;
  amount: string;
  currency: string;
  status: string;
  completed_at: string | null;
}

export interface CustomerAnalytics {
  kpis: CustomerKpis;
  active_return_statuses: CountSeriesPoint[];
  refunds: CustomerRefundRow[];
}