"""Validate uploads and extract plain text from supported formats."""

from __future__ import annotations

import io
import re
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.core.exceptions import AppError

_ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}

_PDF_MAGIC = b"%PDF"
_ZIP_MAGIC = b"PK\x03\x04"


def safe_original_filename(name: str) -> str:
    """Return a basename-only filename safe for display and storage metadata."""

    cleaned = name.replace("\x00", "").strip()
    if not cleaned:
        raise AppError("Filename is required", code="invalid_filename", status_code=400)
    base = PurePosixPath(cleaned.replace("\\", "/")).name
    if base in {"", ".", ".."} or ".." in base or "/" in base or "\\" in base:
        raise AppError("Filename is not allowed", code="invalid_filename", status_code=400)
    if len(base) > 255:
        raise AppError("Filename is too long", code="invalid_filename", status_code=400)
    return base


def extension_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise AppError(
            "Supported formats are PDF, DOCX, TXT, and Markdown",
            code="unsupported_format",
            status_code=400,
        )
    return suffix


def expected_mime_for_extension(ext: str) -> str:
    return _ALLOWED_EXTENSIONS[ext]


def validate_file_content(content: bytes, ext: str) -> None:
    if not content:
        raise AppError("File is empty", code="empty_file", status_code=400)
    if ext == ".pdf":
        if not content.startswith(_PDF_MAGIC):
            raise AppError("File content does not match PDF", code="invalid_file_content", status_code=400)
        return
    if ext == ".docx":
        if not content.startswith(_ZIP_MAGIC):
            raise AppError("File content does not match DOCX", code="invalid_file_content", status_code=400)
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise AppError("File content does not match DOCX", code="invalid_file_content", status_code=400)
        except zipfile.BadZipFile as exc:
            raise AppError("File content does not match DOCX", code="invalid_file_content", status_code=400) from exc
        return
    if b"\x00" in content[:8192]:
        raise AppError("Text file contains invalid binary content", code="invalid_file_content", status_code=400)
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppError("Text file must be UTF-8", code="invalid_file_content", status_code=400) from exc


def storage_relative_key(store_id: uuid.UUID, document_id: uuid.UUID, ext: str) -> str:
    """Relative path under the knowledge storage root (never exposed to clients)."""

    return f"{store_id}/{document_id}/payload{ext}"


def resolve_storage_path(root: Path, storage_key: str) -> Path:
    """Map a storage key to an absolute path and reject traversal."""

    normalized = PurePosixPath(storage_key.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise AppError("Invalid storage key", code="storage_error", status_code=500)
    target = (root / Path(*normalized.parts)).resolve()
    root_resolved = root.resolve()
    if not str(target).startswith(str(root_resolved)):
        raise AppError("Invalid storage path", code="storage_error", status_code=500)
    return target


def sanitize_processing_error(message: str) -> str:
    """Strip paths and keep a short client-safe message."""

    cleaned = re.sub(r"[A-Za-z]:\\[^\s]+|/[^\s]+", "[path]", message)
    cleaned = cleaned.replace("\n", " ").strip()
    if len(cleaned) > 480:
        cleaned = f"{cleaned[:477]}..."
    return cleaned or "Document processing failed"


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    page_count: int | None


def extract_text(content: bytes, ext: str) -> ExtractionResult:
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages).strip()
        return ExtractionResult(text=text, page_count=len(reader.pages))
    if ext == ".docx":
        try:
            from docx import Document

            document = Document(io.BytesIO(content))
            paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
            text = "\n".join(paragraphs).strip()
            page_count = len(document.sections) or None
        except Exception:  # noqa: BLE001 — fall back to raw document XML
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            text = re.sub(r"<w:tab[^/]*/>", "\t", xml)
            text = re.sub(r"</w:p>", "\n", text)
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
            page_count = None
        return ExtractionResult(text=text, page_count=page_count)
    text = content.decode("utf-8").strip()
    return ExtractionResult(text=text, page_count=None)