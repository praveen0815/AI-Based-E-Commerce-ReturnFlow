export type AiReviewRunStatus =
  | "PENDING"
  | "RUNNING"
  | "AWAITING_HUMAN"
  | "COMPLETED"
  | "FAILED"
  | "TIMED_OUT";

export type AiReviewRun = {
  id: string;
  store_id: string;
  return_request_id: string;
  status: AiReviewRunStatus;
  current_agent: string | null;
  revision_count: number;
  output_payload: Record<string, unknown> | null;
  error_message: string | null;
  human_decision: string | null;
  human_note: string | null;
  started_at: string;
  completed_at: string | null;
};

export type AiReviewEvent = {
  id: string;
  sequence: number;
  agent: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};