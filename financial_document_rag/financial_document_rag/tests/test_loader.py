from pathlib import Path

from app.ingestion.loader import DocumentLoader


def test_loads_valid_bundled_corpus(sample_corpus_dir):
    loader = DocumentLoader(corpus_dir=sample_corpus_dir)
    documents = loader.load_all()
    assert len(documents) == 6
    assert not loader.issues


def test_metadata_parsing(sample_corpus_dir):
    loader = DocumentLoader(corpus_dir=sample_corpus_dir)
    documents = loader.load_all()
    reliance_docs = [d for d in documents if d.symbol == "RELIANCE"]
    assert len(reliance_docs) == 4
    doc = next(d for d in reliance_docs if d.document_type == "earnings_report")
    assert doc.company == "Reliance Industries"
    assert doc.title == "Reliance Industries Q4 FY2026 Earnings Report"
    assert doc.source_type == "synthetic"
    assert doc.text.strip() != ""


def test_malformed_metadata_is_skipped(tmp_path):
    bad_file = tmp_path / "bad.md"
    bad_file.write_text(
        "---\n"
        "document_id: bad_doc\n"
        "company: Bad Co\n"
        "symbol: BAD\n"
        "document_type: not_a_real_type\n"
        "title: Bad Document\n"
        "reporting_period: Q1\n"
        "published_date: 2026-01-01\n"
        "source_name: Test\n"
        "source_type: synthetic\n"
        "---\n"
        "# Section\nSome text here.\n"
    )
    loader = DocumentLoader(corpus_dir=tmp_path)
    documents = loader.load_all()
    assert documents == []
    assert len(loader.issues) == 1
    assert "bad.md" in loader.issues[0].file_path


def test_missing_metadata_field_is_skipped(tmp_path):
    bad_file = tmp_path / "missing_field.md"
    bad_file.write_text(
        "---\n"
        "document_id: doc1\n"
        "company: Co\n"
        "symbol: SYM\n"
        "document_type: annual_report\n"
        "title: Title\n"
        "reporting_period: FY2026\n"
        "source_name: Test\n"
        "source_type: synthetic\n"
        "---\n"
        "# Section\nBody text.\n"
    )
    loader = DocumentLoader(corpus_dir=tmp_path)
    documents = loader.load_all()
    assert documents == []
    assert len(loader.issues) == 1
    assert "published_date" in loader.issues[0].reason


def test_missing_file_returns_none(tmp_path):
    loader = DocumentLoader(corpus_dir=tmp_path)
    result = loader.load_one(tmp_path / "does_not_exist.md")
    assert result is None
    assert len(loader.issues) == 1


def test_missing_corpus_directory_returns_empty(tmp_path):
    missing_dir = tmp_path / "nonexistent_corpus"
    loader = DocumentLoader(corpus_dir=missing_dir)
    documents = loader.load_all()
    assert documents == []
