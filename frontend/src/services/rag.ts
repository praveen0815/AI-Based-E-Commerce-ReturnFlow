import type { SuccessResponse } from "../types/api";
import type { PolicyAskResponse } from "../types/rag";
import { api } from "./api";

export async function askPolicyQuestion(question: string, topK = 5): Promise<PolicyAskResponse> {
  const response = await api.post<SuccessResponse<PolicyAskResponse>>("/api/v1/stores/current/knowledge/rag/ask", {
    question,
    top_k: topK,
  });
  return response.data.data;
}

export async function reindexKnowledge(): Promise<{ indexed: number; failed: number; total: number }> {
  const response = await api.post<SuccessResponse<{ indexed: number; failed: number; total: number }>>(
    "/api/v1/stores/current/knowledge/rag/reindex",
    {},
  );
  return response.data.data;
}

export async function submitPolicyFeedback(payload: {
  helpful: boolean;
  question: string;
  answer_excerpt?: string;
}): Promise<void> {
  await api.post("/api/v1/stores/current/knowledge/rag/feedback", payload);
}