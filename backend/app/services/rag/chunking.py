"""Split cleaned text into overlapping chunks with metadata."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.rag.cleaning import clean_text


@dataclass(frozen=True)
class KnowledgeChunk:
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    section_label: str
    page_hint: str | None


def chunk_document_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    page_count: int | None,
) -> list[KnowledgeChunk]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    pieces = splitter.split_text(cleaned)
    total_chars = len(cleaned)
    chunks: list[KnowledgeChunk] = []
    offset = 0
    for index, piece in enumerate(pieces):
        start = cleaned.find(piece, offset)
        if start < 0:
            start = offset
        end = start + len(piece)
        offset = max(0, end - chunk_overlap)
        page_hint = _page_hint(start, end, total_chars, page_count)
        chunks.append(
            KnowledgeChunk(
                text=piece,
                chunk_index=index,
                char_start=start,
                char_end=end,
                section_label=f"Section {index + 1}",
                page_hint=page_hint,
            )
        )
    return chunks


def _page_hint(start: int, end: int, total: int, page_count: int | None) -> str | None:
    if not page_count or page_count < 1 or total < 1:
        return None
    page_size = total / page_count
    first = min(page_count, max(1, int(start / page_size) + 1))
    last = min(page_count, max(1, int(end / page_size) + 1))
    if first == last:
        return f"page {first}"
    return f"pages {first}-{last}"