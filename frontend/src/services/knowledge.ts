import type { SuccessResponse } from "../types/api";
import type { KnowledgeDocumentDetail, KnowledgeDocumentSummary, KnowledgeDocumentType } from "../types/knowledge";
import type { Paginated } from "../types/commerce";
import { api } from "./api";

export async function listKnowledgeDocuments(
  params: Record<string, string | number | undefined> = {},
): Promise<Paginated<KnowledgeDocumentSummary>> {
  const response = await api.get<SuccessResponse<Paginated<KnowledgeDocumentSummary>>>(
    "/api/v1/stores/current/knowledge/documents",
    { params },
  );
  return response.data.data;
}

export async function getKnowledgeDocument(documentId: string): Promise<KnowledgeDocumentDetail> {
  const response = await api.get<SuccessResponse<KnowledgeDocumentDetail>>(
    `/api/v1/stores/current/knowledge/documents/${documentId}`,
  );
  return response.data.data;
}

export async function uploadKnowledgeDocument(file: File, documentType: KnowledgeDocumentType): Promise<KnowledgeDocumentDetail> {
  const body = new FormData();
  body.append("file", file);
  body.append("document_type", documentType);
  const response = await api.post<SuccessResponse<KnowledgeDocumentDetail>>(
    "/api/v1/stores/current/knowledge/documents",
    body,
    {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120_000,
    },
  );
  return response.data.data;
}

export async function deleteKnowledgeDocument(documentId: string): Promise<void> {
  await api.delete(`/api/v1/stores/current/knowledge/documents/${documentId}`);
}

export async function reprocessKnowledgeDocument(documentId: string): Promise<KnowledgeDocumentDetail> {
  const response = await api.post<SuccessResponse<KnowledgeDocumentDetail>>(
    `/api/v1/stores/current/knowledge/documents/${documentId}/reprocess`,
  );
  return response.data.data;
}