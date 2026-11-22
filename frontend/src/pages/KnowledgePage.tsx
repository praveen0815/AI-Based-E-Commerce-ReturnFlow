import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import {
  deleteKnowledgeDocument,
  getKnowledgeDocument,
  listKnowledgeDocuments,
  reprocessKnowledgeDocument,
  uploadKnowledgeDocument,
} from "../services/knowledge";
import {
  KNOWLEDGE_TYPE_LABELS,
  type KnowledgeDocumentDetail,
  type KnowledgeDocumentSummary,
  type KnowledgeDocumentType,
  type KnowledgeProcessingStatus,
} from "../types/knowledge";
import { hasPermission } from "../utils/access";
import { formatDateTime } from "../utils/format";

const ACCEPTED = ".pdf,.docx,.txt,.md,.markdown";
const TYPE_OPTIONS = Object.entries(KNOWLEDGE_TYPE_LABELS) as [KnowledgeDocumentType, string][];
const STATUS_OPTIONS: { value: KnowledgeProcessingStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "UPLOADED", label: "Uploaded" },
  { value: "PROCESSING", label: "Processing" },
  { value: "PROCESSED", label: "Processed" },
  { value: "FAILED", label: "Failed" },
];

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function statusTone(status: KnowledgeProcessingStatus): string {
  if (status === "PROCESSED") {
    return "text-emerald-300";
  }
  if (status === "FAILED") {
    return "text-rose-300";
  }
  if (status === "PROCESSING") {
    return "text-amber-300";
  }
  return "text-ink-muted";
}

export function KnowledgePage() {
  const { activeMembership, storeId } = useAuth();
  const canManage = hasPermission(activeMembership?.permissions, "knowledge:manage");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<KnowledgeDocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<KnowledgeDocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<KnowledgeDocumentType | "">("");
  const [statusFilter, setStatusFilter] = useState<KnowledgeProcessingStatus | "">("");
  const [documentType, setDocumentType] = useState<KnowledgeDocumentType>("RETURN_POLICY");
  const [dragOver, setDragOver] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const page = await listKnowledgeDocuments({
        q: query.trim() || undefined,
        document_type: typeFilter || undefined,
        processing_status: statusFilter || undefined,
        page_size: 50,
      });
      setDocuments(page.items);
      setError("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Documents could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [query, statusFilter, storeId, typeFilter]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const row = await getKnowledgeDocument(selectedId);
        if (!cancelled) {
          setDetail(row);
          if (row.processing_status === "UPLOADED" || row.processing_status === "PROCESSING") {
            timer = window.setTimeout(poll, 1500);
          } else {
            void loadList();
          }
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Document detail could not be loaded.");
        }
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [loadList, selectedId]);

  async function onUploadFiles(files: FileList | File[]) {
    if (!canManage) {
      return;
    }
    const list = Array.from(files);
    if (list.length === 0) {
      return;
    }
    setUploading(true);
    setError("");
    try {
      for (const file of list) {
        const created = await uploadKnowledgeDocument(file, documentType);
        setSelectedId(created.id);
      }
      await loadList();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  async function onDelete(documentId: string) {
    try {
      await deleteKnowledgeDocument(documentId);
      if (selectedId === documentId) {
        setSelectedId(null);
      }
      setConfirmDeleteId(null);
      await loadList();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Delete failed.");
    }
  }

  async function onReprocess(documentId: string) {
    try {
      const row = await reprocessKnowledgeDocument(documentId);
      setSelectedId(documentId);
      setDetail(row);
      await loadList();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Reprocess could not be started.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Knowledge"
        title="Policy knowledge center"
        description="Upload return policies, SOPs, and operational documents for this store. Text is extracted for review. Embeddings and RAG are not part of this phase."
      />
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {canManage ? (
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-white">Upload documents</h2>
          <p className="mt-1 text-sm text-ink-muted">PDF, DOCX, TXT, and Markdown up to 10 MB each.</p>
          <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">Document type</span>
              <select
                className="focus-ring w-full rounded-lg border border-navy-600 bg-navy-950 px-3 py-2 text-sm text-ink"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value as KnowledgeDocumentType)}
              >
                {TYPE_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <Button type="button" variant="secondary" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
              Choose files
            </Button>
          </div>
          <DropZone
            dragOver={dragOver}
            onDragEnter={() => setDragOver(true)}
            onDragLeave={() => setDragOver(false)}
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              void onUploadFiles(event.dataTransfer.files);
            }}
          >
            {uploading ? <Spinner label="Uploading" /> : "Drag and drop files here, or use Choose files."}
          </DropZone>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED}
            multiple
            className="sr-only"
            onChange={(event) => {
              if (event.target.files) {
                void onUploadFiles(event.target.files);
              }
            }}
          />
        </Card>
      ) : (
        <Alert tone="info" title="Read-only access">
          You can browse and preview extracted text. Upload, delete, and reprocess require a manager role or higher.
        </Alert>
      )}

      <form
        className="grid gap-3 lg:grid-cols-[1fr_auto_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          void loadList();
        }}
      >
        <Input
          id="knowledge-search"
          label="Search"
          value={query}
          placeholder="Filename or extracted text"
          onChange={(event) => setQuery(event.target.value)}
        />
        <label className="text-sm">
          <span className="mb-1 block font-medium text-ink">Type</span>
          <select
            className="focus-ring w-full rounded-lg border border-navy-600 bg-navy-950 px-3 py-2 text-sm text-ink"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value as KnowledgeDocumentType | "")}
          >
            <option value="">All types</option>
            {TYPE_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-ink">Status</span>
          <select
            className="focus-ring w-full rounded-lg border border-navy-600 bg-navy-950 px-3 py-2 text-sm text-ink"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as KnowledgeProcessingStatus | "")}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </form>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Card className="overflow-hidden">
          {loading ? <Spinner label="Loading documents" /> : null}
          {!loading && documents.length === 0 ? (
            <EmptyState title="No documents yet" description="Upload a policy or SOP to populate this table." />
          ) : null}
          {!loading && documents.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-navy-600 text-xs uppercase tracking-wide text-ink-faint">
                  <tr>
                    <th className="px-4 py-3 font-medium">File</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Size</th>
                    <th className="px-4 py-3 font-medium">Uploaded</th>
                    {canManage ? <th className="px-4 py-3 font-medium">Actions</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {documents.map((row) => (
                    <tr
                      key={row.id}
                      className={`border-b border-navy-700/80 ${selectedId === row.id ? "bg-cyan-400/5" : ""}`}
                    >
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          className="focus-ring text-left font-medium text-cyan-200 hover:underline"
                          onClick={() => setSelectedId(row.id)}
                        >
                          {row.original_filename}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{KNOWLEDGE_TYPE_LABELS[row.document_type]}</td>
                      <td className={`px-4 py-3 font-medium ${statusTone(row.processing_status)}`}>
                        {row.processing_status}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{formatBytes(row.file_size_bytes)}</td>
                      <td className="px-4 py-3 text-ink-muted">{formatDateTime(new Date(row.uploaded_at))}</td>
                      {canManage ? (
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            <Button type="button" variant="secondary" onClick={() => void onReprocess(row.id)}>
                              Reprocess
                            </Button>
                            <Button type="button" variant="secondary" onClick={() => setConfirmDeleteId(row.id)}>
                              Delete
                            </Button>
                          </div>
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold text-white">Extracted text preview</h2>
          {!selectedId || !detail ? (
            <p className="mt-3 text-sm text-ink-muted">Select a document to preview extracted text.</p>
          ) : (
            <div className="mt-3 space-y-3">
              <dl className="grid gap-1 text-sm text-ink-muted">
                <div>
                  <dt className="inline font-medium text-ink">Status: </dt>
                  <dd className={`inline ${statusTone(detail.processing_status)}`}>{detail.processing_status}</dd>
                </div>
                {detail.page_count !== null ? (
                  <div>
                    <dt className="inline font-medium text-ink">Pages: </dt>
                    <dd className="inline">{detail.page_count}</dd>
                  </div>
                ) : null}
                {detail.error_message ? (
                  <div className="text-rose-300">
                    <dt className="font-medium text-ink">Error</dt>
                    <dd>{detail.error_message}</dd>
                  </div>
                ) : null}
              </dl>
              <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-lg border border-navy-600 bg-navy-950 p-3 text-xs text-ink">
                {detail.extracted_text || detail.text_preview || "No extracted text yet."}
              </pre>
            </div>
          )}
        </Card>
      </div>

      {confirmDeleteId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/80 p-4">
          <Card className="w-full max-w-md p-5">
            <h2 className="text-lg font-semibold text-white">Delete document?</h2>
            <p className="mt-2 text-sm text-ink-muted">This removes the file and extracted text for this store.</p>
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setConfirmDeleteId(null)}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void onDelete(confirmDeleteId)}>
                Delete
              </Button>
            </div>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

type DropProps = {
  dragOver: boolean;
  children: React.ReactNode;
  onDragEnter: () => void;
  onDragLeave: () => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
};

function DropZone({ dragOver, children, onDragEnter, onDragLeave, onDragOver, onDrop }: DropProps) {
  return (
    <div
      className={`mt-4 flex min-h-28 items-center justify-center rounded-xl border border-dashed px-4 py-6 text-center text-sm ${
        dragOver ? "border-cyan-400 bg-cyan-400/5 text-cyan-100" : "border-navy-600 text-ink-muted"
      }`}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {children}
    </div>
  );
}