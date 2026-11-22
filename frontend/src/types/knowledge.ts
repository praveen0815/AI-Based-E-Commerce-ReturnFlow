export type KnowledgeDocumentType =
  | "RETURN_POLICY"
  | "REFUND_POLICY"
  | "SHIPPING_POLICY"
  | "WARRANTY"
  | "PRODUCT_CONDITIONS"
  | "STORE_SOP"
  | "CUSTOM";

export type KnowledgeProcessingStatus = "UPLOADED" | "PROCESSING" | "PROCESSED" | "FAILED";

export type KnowledgeIndexStatus = "NOT_INDEXED" | "INDEXING" | "INDEXED" | "INDEX_FAILED";

export type KnowledgeDocumentSummary = {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  uploaded_at: string;
  document_type: KnowledgeDocumentType;
  processing_status: KnowledgeProcessingStatus;
  page_count: number | null;
  text_preview: string | null;
  error_message: string | null;
  index_status: KnowledgeIndexStatus;
  indexed_at: string | null;
  indexed_chunk_count: number | null;
};

export type KnowledgeDocumentDetail = KnowledgeDocumentSummary & {
  store_id: string;
  extracted_text: string | null;
  uploaded_by_user_id: string | null;
};

export const KNOWLEDGE_TYPE_LABELS: Record<KnowledgeDocumentType, string> = {
  RETURN_POLICY: "Return policy",
  REFUND_POLICY: "Refund policy",
  SHIPPING_POLICY: "Shipping policy",
  WARRANTY: "Warranty",
  PRODUCT_CONDITIONS: "Product conditions",
  STORE_SOP: "Store SOP",
  CUSTOM: "Custom knowledge",
};