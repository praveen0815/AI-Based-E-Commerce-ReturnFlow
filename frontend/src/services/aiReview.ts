import type { SuccessResponse } from "../types/api";
import type { AiReviewEvent, AiReviewRun } from "../types/aiReview";
import { api } from "./api";

export async function startAiReview(returnId: string): Promise<AiReviewRun> {
  const response = await api.post<SuccessResponse<AiReviewRun>>(
    `/api/v1/stores/current/returns/${returnId}/ai-review`,
    {},
    { timeout: 120_000 },
  );
  return response.data.data;
}

export async function latestAiReview(returnId: string): Promise<AiReviewRun | null> {
  const response = await api.get<SuccessResponse<AiReviewRun | null>>(
    `/api/v1/stores/current/returns/${returnId}/ai-review/latest`,
  );
  return response.data.data;
}

export async function getAiReviewRun(returnId: string, runId: string): Promise<AiReviewRun> {
  const response = await api.get<SuccessResponse<AiReviewRun>>(
    `/api/v1/stores/current/returns/${returnId}/ai-review/runs/${runId}`,
  );
  return response.data.data;
}

export async function listAiReviewEvents(returnId: string, runId: string): Promise<AiReviewEvent[]> {
  const response = await api.get<SuccessResponse<{ events: AiReviewEvent[] }>>(
    `/api/v1/stores/current/returns/${returnId}/ai-review/runs/${runId}/events`,
  );
  return response.data.data.events;
}

export async function resumeAiReview(
  returnId: string,
  runId: string,
  payload: { decision: "ACKNOWLEDGE" | "OVERRULE_RECOMMENDATION"; note?: string },
): Promise<AiReviewRun> {
  const response = await api.post<SuccessResponse<AiReviewRun>>(
    `/api/v1/stores/current/returns/${returnId}/ai-review/runs/${runId}/resume`,
    payload,
  );
  return response.data.data;
}