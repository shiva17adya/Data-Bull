"""Pydantic models used across the financial_document_rag module."""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.config import ALLOWED_DOCUMENT_TYPES


class Document(BaseModel):
    """A fully-loaded source document (one Markdown file)."""

    document_id: str
    company: str
    symbol: str
    document_type: str
    title: str
    reporting_period: str
    published_date: date
    source_name: str
    source_type: str
    text: str

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        if v not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(
                f"document_type '{v}' not in allowed set {sorted(ALLOWED_DOCUMENT_TYPES)}"
            )
        return v

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.strip().upper()


class Chunk(BaseModel):
    """A chunk of a document, ready for embedding + storage."""

    chunk_id: str
    document_id: str
    company: str
    symbol: str
    document_type: str
    title: str
    section: str
    source_name: str
    source_type: str
    published_date: date
    text: str


class SourceAttribution(BaseModel):
    document_id: str
    title: str
    company: str
    symbol: str
    document_type: str
    section: str
    source_name: str
    source_type: str
    published_date: date


class RetrievalResult(BaseModel):
    chunk_id: str
    text: str
    similarity_score: float
    source: SourceAttribution


class RetrievalRequest(BaseModel):
    query: str
    symbol: Optional[str] = None
    document_type: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query must not be empty.")
        return v.strip()

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        return v or None

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(
                f"document_type '{v}' not in allowed set {sorted(ALLOWED_DOCUMENT_TYPES)}"
            )
        return v


class RetrievalResponse(BaseModel):
    query: str
    symbol: Optional[str] = None
    results: list[RetrievalResult] = Field(default_factory=list)
    status: str = "OK"  # OK | NO_RESULTS | DEGRADED
    warnings: list[str] = Field(default_factory=list)


class DocumentsInfoResponse(BaseModel):
    total_documents: int
    symbols: list[str]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
