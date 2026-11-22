export type RagCitation = {
  label: string;
  document_id: string | null;
  original_filename: string | null;
  document_type: string | null;
  section_label: string | null;
  page_hint: string | null;
  chunk_index: number | null;
  score: number;
  excerpt: string;
};

export type PolicyAskResponse = {
  answer: string;
  grounded: boolean;
  model: string;
  citations: RagCitation[];
  retrieval_count: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  grounded?: boolean;
  citations?: RagCitation[];
  model?: string;
  error?: boolean;
};