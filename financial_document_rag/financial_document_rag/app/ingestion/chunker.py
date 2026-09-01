"""Section-aware chunking of Document objects into Chunk objects."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.config import CHUNK_MAX_WORDS, CHUNK_OVERLAP_WORDS, CHUNK_TARGET_WORDS
from app.models.schemas import Chunk, Document

SECTION_HEADER_RE = re.compile(r"^#{1,3}\s+(.*)$", re.MULTILINE)


@dataclass
class _Section:
    title: str
    text: str


class DocumentChunker:
    """Splits a Document's body into overlapping, section-aware chunks.

    Chunk IDs are deterministic: they are derived from the document_id, the
    section name, and a running index, so re-chunking identical content always
    produces identical chunk_ids.
    """

    def __init__(
        self,
        target_words: int = CHUNK_TARGET_WORDS,
        max_words: int = CHUNK_MAX_WORDS,
        overlap_words: int = CHUNK_OVERLAP_WORDS,
    ):
        self.target_words = target_words
        self.max_words = max_words
        self.overlap_words = overlap_words

    def _split_into_sections(self, text: str) -> list[_Section]:
        """Split markdown body into (heading, content) sections. If no headings
        are found, the whole body is treated as a single 'Body' section."""
        matches = list(SECTION_HEADER_RE.finditer(text))
        if not matches:
            stripped = text.strip()
            if not stripped:
                return []
            return [_Section(title="Body", text=stripped)]

        sections: list[_Section] = []
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if content:
                sections.append(_Section(title=title, text=content))
        return sections

    def _words(self, text: str) -> list[str]:
        return text.split()

    def _chunk_section_text(self, words: list[str]) -> list[str]:
        """Break a long list of words into overlapping windows of ~target_words,
        never exceeding max_words, with overlap_words shared between consecutive
        windows."""
        if not words:
            return []
        if len(words) <= self.max_words:
            return [" ".join(words)]

        chunks: list[str] = []
        step = max(self.target_words - self.overlap_words, 1)
        start = 0
        while start < len(words):
            end = min(start + self.target_words, len(words))
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            if end >= len(words):
                break
            start += step
        return chunks

    def _make_chunk_id(self, document_id: str, section_title: str, index: int, text: str) -> str:
        """Deterministic chunk id: same document_id + section + index + content
        always yields the same id."""
        digest_source = f"{document_id}|{section_title}|{index}|{text}"
        digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:10]
        safe_section = re.sub(r"[^a-z0-9]+", "_", section_title.lower()).strip("_") or "section"
        return f"{document_id}_{safe_section}_{index:03d}_{digest}"

    def chunk_document(self, document: Document) -> list[Chunk]:
        """Chunk a single Document into a list of Chunk objects. Returns an
        empty list for an empty document body."""
        sections = self._split_into_sections(document.text)
        chunks: list[Chunk] = []

        for section in sections:
            words = self._words(section.text)
            section_texts = self._chunk_section_text(words)
            for idx, chunk_text in enumerate(section_texts):
                chunk_id = self._make_chunk_id(document.document_id, section.title, idx, chunk_text)
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        company=document.company,
                        symbol=document.symbol,
                        document_type=document.document_type,
                        title=document.title,
                        section=section.title,
                        source_name=document.source_name,
                        source_type=document.source_type,
                        published_date=document.published_date,
                        text=chunk_text,
                    )
                )
        return chunks

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks
