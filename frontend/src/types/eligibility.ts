export type EligibilityDecision = "ELIGIBLE" | "INELIGIBLE" | "NEEDS_REVIEW";

export type EligibilityResult = {
  id: string;
  store_id: string;
  order_id: string;
  return_request_id: string | null;
  decision: EligibilityDecision;
  decision_code: string;
  explanation: string;
  decision_reason: string;
  policy_rule_version: number;
  policy_references: Array<Record<string, unknown>>;
  missing_information: Array<Record<string, string>>;
  recommended_next_steps: string[];
  ai_explanation: string | null;
  ai_model: string | null;
  human_review_requested: boolean;
  evaluated_at: string;
};