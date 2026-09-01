from datetime import date

from app.ingestion.chunker import DocumentChunker
from app.models.schemas import Document


def _make_document(text: str, document_id: str = "doc1") -> Document:
    return Document(
        document_id=document_id,
        company="Test Co",
        symbol="TST",
        document_type="annual_report",
        title="Test Document",
        reporting_period="FY2026",
        published_date=date(2026, 1, 1),
        source_name="Test Source",
        source_type="synthetic",
        text=text,
    )


def test_multiple_chunks_created_from_bundled_corpus(sample_corpus_dir):
    from app.ingestion.loader import DocumentLoader

    loader = DocumentLoader(corpus_dir=sample_corpus_dir)
    documents = loader.load_all()
    chunker = DocumentChunker()
    chunks = chunker.chunk_documents(documents)
    assert len(chunks) >= len(documents)  # at least one chunk per document


def test_section_preservation():
    text = "# Revenue\n" + ("word " * 20) + "\n# Risks\n" + ("risk " * 20)
    doc = _make_document(text)
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(doc)
    sections = {c.section for c in chunks}
    assert sections == {"Revenue", "Risks"}


def test_deterministic_chunk_ids():
    text = "# Revenue\n" + ("word " * 900)  # forces multiple chunks
    doc = _make_document(text)
    chunker = DocumentChunker()
    chunks_a = chunker.chunk_document(doc)
    chunks_b = chunker.chunk_document(doc)
    ids_a = [c.chunk_id for c in chunks_a]
    ids_b = [c.chunk_id for c in chunks_b]
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a))  # all unique within one document


def test_overlap_between_consecutive_chunks():
    text = "# Revenue\n" + " ".join(f"word{i}" for i in range(1500))
    doc = _make_document(text)
    chunker = DocumentChunker(target_words=650, max_words=800, overlap_words=75)
    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 2
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    overlap = set(first_words[-75:]) & set(second_words[:75])
    assert len(overlap) > 0


def test_short_document_single_chunk():
    text = "# Revenue\nThis is a very short section with few words."
    doc = _make_document(text)
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section == "Revenue"


def test_empty_document_produces_no_chunks():
    doc = _make_document("   ")
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(doc)
    assert chunks == []


def test_document_without_headings_becomes_single_body_section():
    text = "Just plain text with no markdown headings at all, describing revenue."
    doc = _make_document(text)
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section == "Body"
