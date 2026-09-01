# Financial Document RAG

**Module 2 of the Multi-Agent Autonomous Financial Intelligence System.**
Owns: `Documents → Loading → Chunking → Embeddings → Chroma → Retrieval → Attributed JSON → Fundamental Agent`.

This module is fully isolated. It does not depend on, and is not depended on
by, the frontend, market-data module, signal engine, sentiment/risk agents,
user profile service, orchestrator, or synthesis layer.

> ⚠️ **The bundled financial documents are synthetic** and are used only for
> hackathon demonstration/testing. They are not real SEBI filings, real
> earnings reports, or real company disclosures.

---

## 1. Purpose

Convert a small corpus of financial documents (earnings reports, annual
reports, earnings transcripts, disclosures) into a semantically searchable
index, and expose a retrieval API that returns **grounded, fully-attributed**
evidence chunks for a natural-language financial query. This module performs
**no reasoning and gives no recommendations** — that is the Fundamental
Agent's job, downstream of this API.

## 2. Architecture

```text
Markdown + YAML docs (app/documents/corpus/)
        │
        ▼
DocumentLoader   — parses frontmatter, validates metadata, skips bad files
        │
        ▼
DocumentChunker  — section-aware chunking, ~500-800 words, ~50-100 overlap
        │
        ▼
EmbeddingService — sentence-transformers/all-MiniLM-L6-v2, loaded once
        │
        ▼
VectorStore      — persistent ChromaDB collection "financial_documents"
        │
        ▼
Retriever        — query validation, embed query, filtered similarity search
        │
        ▼
FastAPI (/retrieve, /documents, /ingest, /health)
        │
        ▼
Fundamental Agent (downstream, outside this module)
```

## 3. Folder structure

```text
financial_document_rag/
├── app/
│   ├── main.py                 FastAPI app, startup, error handlers
│   ├── config.py                Central config (env-driven, sane defaults)
│   ├── api/routes.py            /health /retrieve /documents /ingest
│   ├── models/schemas.py        Pydantic models (Document, Chunk, Retrieval*)
│   ├── ingestion/
│   │   ├── loader.py            DocumentLoader
│   │   ├── chunker.py           DocumentChunker
│   │   └── ingest.py            IngestionService (pipeline orchestration)
│   ├── retrieval/
│   │   ├── embeddings.py        EmbeddingService (loaded once, singleton)
│   │   ├── vector_store.py      VectorStore (Chroma wrapper)
│   │   └── retriever.py         Retriever (validation + orchestration)
│   └── documents/corpus/        6 synthetic .md documents (Reliance, TCS)
├── data/chroma/                 Persistent Chroma index (gitignored contents)
├── tests/                       38 tests, pytest
├── requirements.txt
├── .env.example
└── README.md
```

## 4. Document format

Markdown with YAML frontmatter:

```markdown
---
document_id: reliance_q4_2026
company: Reliance Industries
symbol: RELIANCE
document_type: earnings_report
title: Reliance Industries Q4 FY2026 Earnings Report
reporting_period: Q4 FY2026
published_date: 2026-05-15
source_name: Reliance Industries Investor Relations
source_type: synthetic
---

# Revenue
...
```

## 5. Required metadata fields

`document_id`, `company`, `symbol`, `document_type`, `title`,
`reporting_period`, `published_date`, `source_name`, `source_type`.

Allowed `document_type` values: `annual_report`, `earnings_report`,
`earnings_transcript`, `company_disclosure`.

Missing/malformed metadata → the file is **skipped** (logged), not a crash.

## 6. Chunking strategy

Section-aware: splits on Markdown `#`/`##`/`###` headers. Each section is then
broken into ~500-800 word windows with ~50-100 word overlap between
consecutive windows (only when a section exceeds the max window size).
`chunk_id` is deterministic — `sha1(document_id|section|index|text)` — so
re-running ingestion on identical content always yields identical IDs.

During ingestion, embeddings are computed over `"{title}. {section}. {text}"`
(title/section prepended as context) while the **raw** `text` is what's
stored and returned — this measurably improves retrieval quality for queries
that use section-level vocabulary (e.g. "outlook", "guidance") that may not
appear verbatim in a chunk's body.

## 7. Embedding model

`sentence-transformers/all-MiniLM-L6-v2`, loaded once as a process-wide
singleton (`EmbeddingService`). No API key required. Requires one-time
internet access to download the model from Hugging Face on first run; it is
then cached locally.

## 8. Chroma configuration

Persistent client at `./data/chroma` (configurable via `CHROMA_PATH`),
collection `financial_documents` (configurable via `COLLECTION_NAME`), cosine
distance. Re-ingestion is idempotent — existing `chunk_id`s are skipped.

## 9. Retrieval flow

`query → validate (non-empty, 1≤top_k≤10) → embed query → Chroma similarity
search (optional symbol / document_type filter) → map to RetrievalResult with
full source attribution → RetrievalResponse`.

## 10. API endpoints

| Method | Path         | Purpose                                             |
|--------|--------------|------------------------------------------------------|
| GET    | `/health`    | Liveness check                                        |
| POST   | `/retrieve`  | Semantic retrieval (the main integration point)       |
| GET    | `/documents` | Corpus/index summary (doc count, indexed symbols)     |
| POST   | `/ingest`    | (Re-)ingest the bundled corpus only — no arbitrary paths accepted |
| GET    | `/docs`      | Auto-generated Swagger UI (FastAPI default)           |

## 11. Example request

```bash
curl -X POST http://localhost:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was Reliance revenue growth?",
    "symbol": "RELIANCE",
    "top_k": 3
  }'
```

## 12. Example response

```json
{
  "query": "What was Reliance revenue growth?",
  "symbol": "RELIANCE",
  "results": [
    {
      "chunk_id": "reliance_q4_2026_revenue_growth_000_1363cb571d",
      "text": "On a year-over-year basis, revenue growth was broad-based...",
      "similarity_score": 0.9123,
      "source": {
        "document_id": "reliance_q4_2026",
        "title": "Reliance Industries Q4 FY2026 Earnings Report",
        "company": "Reliance Industries",
        "symbol": "RELIANCE",
        "document_type": "earnings_report",
        "section": "Revenue Growth",
        "source_name": "Reliance Industries Investor Relations",
        "source_type": "synthetic",
        "published_date": "2026-05-15"
      }
    }
  ],
  "status": "OK",
  "warnings": []
}
```

(Values above are illustrative; the running system returns live scores.)

## 13. Attribution

Every result's `source` object always contains all 9 attribution fields.
There is no code path that returns a chunk without full attribution. This
module never returns `BUY`/`SELL`/portfolio/investment recommendations — it
returns evidence only. The Fundamental Agent should render, at minimum:

```text
Source: Reliance Industries Q4 FY2026 Earnings Report
Section: Revenue
Source type: Synthetic
```

## 14. Error handling

| Condition                     | Response                                      |
|--------------------------------|-----------------------------------------------|
| Empty query                    | `400 INVALID_QUERY`                            |
| `top_k` out of `[1,10]`         | `400 INVALID_REQUEST`                          |
| Unknown/unindexed symbol       | `200 OK`, `status: NO_RESULTS`, empty results, explanatory warning |
| Malformed source document      | Skipped at ingestion time, logged, doesn't stop the pipeline |
| Chroma unavailable             | `503 VECTOR_STORE_UNAVAILABLE`                 |
| Unexpected internal error      | `500 INTERNAL_ERROR` (no stack trace exposed)  |

## 15. Installation

```bash
cd financial_document_rag
pip install -r requirements.txt
cp .env.example .env   # optional, defaults already work
```

## 16. Ingestion command

```bash
python -m app.ingestion.ingest
```

Re-running is safe — it will not duplicate chunks already in the index.
The first run downloads the embedding model (needs internet access once).

## 17. API startup command

```bash
uvicorn app.main:app --reload --port 8000
```

## 18. Test command

```bash
pytest -q
```

38 tests pass. 7 tests in `test_embeddings.py` will **skip** (not fail) in
network-restricted environments, since they exercise the real embedding
model download; all other tests (loader, chunker, vector store, retrieval,
API, missing-document handling) run fully offline against a deterministic
fake embedding service and do not require internet access.

## 19. Fundamental Agent integration contract

The Fundamental Agent should call:

```text
POST http://localhost:8000/retrieve
{
  "query": "What does management say about future revenue growth?",
  "symbol": "RELIANCE",
  "top_k": 5
}
```

It receives retrieved text + similarity score + full source metadata for
each result, and is responsible for all reasoning, synthesis, and any
investment-related conclusions drawn from that evidence. This module never
produces recommendations itself.

## 20. Limitations

- Corpus is small and entirely synthetic (6 documents, 2 companies) — built
  for hackathon demo scope, not production-scale retrieval.
- Similarity search is a flat top-k cosine search per query; no re-ranking,
  hybrid (keyword + semantic) search, or query expansion is implemented.
- No authentication on the API — not intended to be exposed outside the
  hackathon demo network.
- `EmbeddingService` requires one-time internet access to Hugging Face to
  download `all-MiniLM-L6-v2`; fully offline environments need to
  pre-download/cache the model separately.
- Chunking uses a simple word-count heuristic; it does not use a tokenizer
  aligned to the embedding model's actual token limits.
