"""Loads Markdown documents with YAML frontmatter into validated Document objects."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from app.config import CORPUS_DIR, REQUIRED_METADATA_FIELDS
from app.models.schemas import Document

logger = logging.getLogger(__name__)

FRONTMATTER_DELIMITER = "---"


@dataclass
class LoadIssue:
    """Represents a problem encountered while loading a single file."""

    file_path: str
    reason: str


class DocumentLoader:
    """Loads and validates Markdown + YAML-frontmatter financial documents."""

    def __init__(self, corpus_dir: Optional[Path] = None):
        self.corpus_dir = Path(corpus_dir) if corpus_dir else CORPUS_DIR
        self.issues: list[LoadIssue] = []

    def _split_frontmatter(self, raw_text: str) -> tuple[Optional[str], str]:
        """Split raw markdown into (yaml_text, body_text). Returns (None, raw_text) if
        no valid frontmatter block is found."""
        stripped = raw_text.lstrip("\ufeff")  # tolerate BOM
        if not stripped.startswith(FRONTMATTER_DELIMITER):
            return None, raw_text

        parts = stripped.split(FRONTMATTER_DELIMITER, 2)
        # parts[0] is empty string before the first '---'
        if len(parts) < 3:
            return None, raw_text

        yaml_text = parts[1]
        body_text = parts[2].lstrip("\n")
        return yaml_text, body_text

    def _load_single_file(self, file_path: Path) -> Optional[Document]:
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.issues.append(LoadIssue(str(file_path), f"Could not read file: {exc}"))
            return None

        yaml_text, body_text = self._split_frontmatter(raw_text)
        if yaml_text is None:
            self.issues.append(
                LoadIssue(str(file_path), "Missing or malformed YAML frontmatter block.")
            )
            return None

        try:
            metadata = yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError as exc:
            self.issues.append(LoadIssue(str(file_path), f"Invalid YAML frontmatter: {exc}"))
            return None

        if not isinstance(metadata, dict):
            self.issues.append(LoadIssue(str(file_path), "Frontmatter did not parse to a mapping."))
            return None

        missing_fields = [f for f in REQUIRED_METADATA_FIELDS if not metadata.get(f)]
        if missing_fields:
            self.issues.append(
                LoadIssue(str(file_path), f"Missing required metadata fields: {missing_fields}")
            )
            return None

        body_text = body_text.strip()
        if not body_text:
            self.issues.append(LoadIssue(str(file_path), "Document body is empty."))
            return None

        try:
            document = Document(**metadata, text=body_text)
        except ValidationError as exc:
            self.issues.append(LoadIssue(str(file_path), f"Metadata validation failed: {exc}"))
            return None

        return document

    def load_all(self) -> list[Document]:
        """Load every .md file in the corpus directory. Malformed documents are
        skipped and recorded in self.issues rather than raising."""
        self.issues = []
        documents: list[Document] = []

        if not self.corpus_dir.exists():
            logger.warning("Corpus directory does not exist: %s", self.corpus_dir)
            return documents

        for file_path in sorted(self.corpus_dir.glob("*.md")):
            document = self._load_single_file(file_path)
            if document is not None:
                documents.append(document)
            else:
                logger.warning("Skipped document %s: see issues log", file_path)

        return documents

    def load_one(self, file_path: Path) -> Optional[Document]:
        """Load a single document file directly (used mainly by tests)."""
        self.issues = []
        return self._load_single_file(Path(file_path))
