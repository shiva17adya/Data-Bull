"""Central configuration for the financial_document_rag module.

All values can be overridden via environment variables / a .env file.
No API key is required anywhere in this module.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base directory of this module (financial_document_rag/)
BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

_raw_chroma_path = os.getenv("CHROMA_PATH", "./data/chroma")
if os.path.isabs(_raw_chroma_path):
    CHROMA_PATH = _raw_chroma_path
else:
    CHROMA_PATH = str((BASE_DIR / _raw_chroma_path.lstrip("./")).resolve())

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "financial_documents")

DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
MAX_TOP_K = int(os.getenv("MAX_TOP_K", "10"))

CORPUS_DIR = BASE_DIR / "app" / "documents" / "corpus"

ALLOWED_DOCUMENT_TYPES = {
    "annual_report",
    "earnings_report",
    "earnings_transcript",
    "company_disclosure",
}

REQUIRED_METADATA_FIELDS = [
    "document_id",
    "company",
    "symbol",
    "document_type",
    "title",
    "reporting_period",
    "published_date",
    "source_name",
    "source_type",
]

CHUNK_TARGET_WORDS = 650  # midpoint of 500-800
CHUNK_MIN_WORDS = 500
CHUNK_MAX_WORDS = 800
CHUNK_OVERLAP_WORDS = 75  # midpoint of 50-100
