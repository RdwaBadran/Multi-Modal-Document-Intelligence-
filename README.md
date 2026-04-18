# Multi-Modal Document Intelligence RAG

A runnable **DSAI 413 - Assignment 1** codebase for a real-document, multi-modal RAG system. It ingests policy or financial PDF reports, extracts text, table-like regions, image metadata, and figure-adjacent content, builds a citation-aware vector index, and answers questions through a Streamlit UI or CLI chatbot.

The project is designed to stay **free to run**:

- Default mode uses a fully local hashing-based vector index and extractive answer composer.
- Optional Google AI Studio integration uses a **free-tier Gemini API key** for stronger image captioning, embeddings, and answer generation.

## Features

- Multi-modal ingestion for PDF text, table-like blocks, embedded images, figure/chart metadata, and note/footnote-like content
- Structural chunking with section-aware citations
- Unified vector retrieval over normalized chunk representations
- Optional Gemini generation and embeddings through Google AI Studio
- Local fallback that still works with **no API key**
- Streamlit web UI for browser-based demos and video recording
- CLI demo app for `ingest`, `ask`, `chat`, `inspect`, and `evaluate`
- Benchmark runner for assignment-style evaluation questions
- Unit tests for retrieval and QA behavior

## Project Layout

```text
data/
main.py
src/mm_rag/
tests/
TECHNICAL_REPORT.md
VIDEO_DEMO_SCRIPT.md
```

## Quick Start

### 1. Optional: add your free Google AI Studio key

Copy `.env.example` to `.env` and fill in:

```env
GOOGLE_API_KEY=your_google_ai_studio_key
```

If `.env` is missing, the app still runs in local mode.

### 2. Put real report PDFs somewhere accessible

You can point the ingestor at:

- a single PDF file
- a folder containing PDFs
- multiple files and folders

Recommended corpus:

- [Sample corpus guide](C:/Users/Magic/Documents/Codex/DSAI413/data/sample_corpus/README.md)
- Put at least two real policy reports in `data/sample_corpus`

### 3. Build the index

```powershell
python main.py ingest "data\sample_corpus" --backend local --index-dir storage\index
```

Force fully local mode:

```powershell
python main.py ingest "C:\path\to\documents" --backend local
```

Use Gemini embeddings if your free key is configured:

```powershell
python main.py ingest "C:\path\to\documents" --backend gemini
```

### 4. Ask a question

```powershell
python main.py ask "What are the main fiscal risks discussed in the reports?" --index-dir storage\index
```

Show the retrieved evidence:

```powershell
python main.py ask "Which table contains the main macroeconomic indicators?" --index-dir storage\index --show-context
```

### 5. Start the interactive chatbot

```powershell
python main.py chat --index-dir storage\index
```

Type `exit` to quit.

### 6. Launch the Streamlit UI

```powershell
python -m streamlit run streamlit_app.py
```

### 7. Run the benchmark suite

```powershell
python main.py evaluate --index-dir storage\index --benchmarks data\benchmarks\economic_report_questions.json --output-dir storage\evaluation
```

## Assignment-Aligned Workflow

Use the project on **real reports**, not the assignment sheet:

```powershell
python main.py ingest "data\sample_corpus" --backend local --index-dir storage\index
python main.py ask "What are the main fiscal risks discussed across the reports?" --index-dir storage\index --show-context
python main.py evaluate --index-dir storage\index --benchmarks data\benchmarks\economic_report_questions.json
python main.py chat --index-dir storage\index
```

## How It Works

### Ingestion

- Extract page text with `pypdf` layout-aware parsing
- Detect headings and table-like text blocks heuristically
- Label figure/chart metadata, table captions, and source-note-like blocks
- Extract embedded images when present
- Optionally caption images with Gemini for better retrieval

### Chunking

- Text is split into section-aware chunks with overlap
- Table-like blocks are preserved as structured evidence chunks
- Images are converted to text-rich metadata chunks for unified indexing
- Figure/chart metadata and footnote-like content are preserved as searchable evidence

### Retrieval

- Local mode: deterministic hashing-based vectorizer with cosine similarity
- Gemini mode: retrieval-optimized embeddings using Google AI Studio free-tier API
- Hybrid lexical + vector ranking improves section-aware benchmark questions

### Answer Generation

- Local mode: extractive evidence synthesis with inline citations
- Gemini mode: grounded answer generation constrained to retrieved context

## Notes and Limitations

- Fully scanned PDFs work best when you provide a Gemini key, because image captioning improves coverage for non-extractable text.
- Without OCR tooling installed, the local-only mode cannot read text that is present only inside raster page images.
- The benchmark suite is qualitative rather than gold-label-scored; it is meant for demo and report support.
- The assignment PDF is useful only as a smoke test. For the real submission, use policy or financial reports such as IMF Article IV documents.

## Testing

```powershell
python -m unittest discover -s tests -v
```

## Suggested Submission Items

- Codebase: this project
- Demo: Streamlit UI or CLI flow using `ingest` + `evaluate` + `chat`
- Report: [TECHNICAL_REPORT.md](C:/Users/Magic/Documents/Codex/DSAI413/TECHNICAL_REPORT.md)
- Video outline: [VIDEO_DEMO_SCRIPT.md](C:/Users/Magic/Documents/Codex/DSAI413/VIDEO_DEMO_SCRIPT.md)

## Google References

This project's optional Gemini integration follows official Google AI for Developers documentation:

- [Gemini API reference](https://ai.google.dev/api)
- [Embeddings guide](https://ai.google.dev/gemini-api/docs/embeddings)
- [Billing and free tier overview](https://ai.google.dev/gemini-api/docs/billing/)
