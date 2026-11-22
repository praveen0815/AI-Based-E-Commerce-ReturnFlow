import type { SuccessResponse } from "../types/api";
import type { RequestedResolution } from "../types/commerce";
import type { EligibilityResult } from "../types/eligibility";
import { api } from "./api";

export async function evaluateEligibility(payload: {
  order_id: string;
  reason: string;
  description: string;
  requested_resolution: RequestedResolution;
  items: Array<{ order_item_id: string; quantity: number; condition?: string }>;
  include_ai_explanation?: boolean;
}): Promise<EligibilityResult> {
  const response = await api.post<SuccessResponse<EligibilityResult>>(
    "/api/v1/stores/current/returns/eligibility/evaluate",
    payload,
  );
  return response.data.data;
}

export async function requestEligibilityReview(decisionId: string): Promise<EligibilityResult> {
  const response = await api.post<SuccessResponse<EligibilityResult>>(
    `/api/v1/stores/current/returns/eligibility/${decisionId}/request-review`,
  );
  return response.data.data;
}

export async function explainEligibility(decisionId: string): Promise<EligibilityResult> {
  const response = await api.post<SuccessResponse<EligibilityResult>>(
    `/api/v1/stores/current/returns/eligibility/${decisionId}/explain`,
  );
  return response.data.data;
}

export async function latestReturnEligibility(returnId: string): Promise<EligibilityResult | null> {
  const response = await api.get<SuccessResponse<{ decision: EligibilityResult | null }>>(
    `/api/v1/stores/current/returns/${returnId}/eligibility`,
  );
  return response.data.data.decision;
}