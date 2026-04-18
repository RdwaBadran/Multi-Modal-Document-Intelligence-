# Technical Report

## Title

Multi-Modal Document Intelligence for RAG-Based Question Answering

## Problem

The goal was to build a retrieval-augmented QA system that can work with real-world policy and financial PDF documents rather than plain text alone. Reports such as IMF Article IV consultations include narrative text, tables, chart titles, figures, notes, and image-based elements. A conventional text-only pipeline can miss evidence stored in figures, structured rows, or page layout. This project addresses that gap by converting each modality into a normalized, citation-aware retrieval unit.

## Architecture

The system has four stages:

1. Ingestion  
   PDFs are parsed with `pypdf` using layout-aware text extraction. The pipeline separates blocks into headings, regular text, table-like regions, chart or figure metadata, and note-like regions using structural heuristics. Embedded images are extracted to disk and represented as multimodal chunks.

2. Chunking and normalization  
   Each chunk stores document name, page number, optional section title, modality, content, role metadata, and citation string. Text blocks are split into overlapping chunks. Table-like blocks are preserved in semi-structured form. Figure or chart references and note-like text are retained as searchable metadata. Images are converted into text-rich metadata chunks using either a local fallback description or optional Gemini image captioning.

3. Retrieval  
   Two free modes are supported:
   - Local mode uses a deterministic hashing-based vectorizer with cosine similarity.
   - Gemini mode uses Google AI Studio free-tier embeddings through the official Gemini REST API.
   A lightweight lexical bonus is added during retrieval to improve section-aware matching for benchmark-style questions.

4. Answer generation  
   The QA layer retrieves top-k chunks and produces a citation-backed response. If a Gemini key is available, generation is done with grounded prompting over retrieved context. Otherwise, the system uses an extractive fallback that selects and cites the most relevant evidence spans. For assignment-style list questions such as deliverables, objectives, or evaluation criteria, the local answerer formats structured bullet answers directly from retrieved evidence.

## Design Choices

- `CLI demo instead of a web stack`: the assignment allows CLI, and this avoids dependency bloat.
- `No paid APIs`: the default system runs locally with zero API cost. Gemini integration is optional and works with the Google AI Studio free tier.
- `Unified multimodal index`: all modalities are converted into retrieval text, allowing a single vector space and one ranking pipeline.
- `Graceful degradation`: if Gemini is unavailable, the pipeline still ingests, indexes, retrieves, and answers questions.
- `Assignment-oriented evaluation`: a benchmark runner executes a reusable set of policy-report questions and saves JSON plus Markdown reports for the final submission.

## Evaluation Approach

The project supports simple benchmarking by running a shared set of questions against indexed documents and checking:

- relevance of retrieved chunks
- answer faithfulness to context
- citation correctness
- modality coverage across text, tables, and images

Unit tests verify embedding behavior, index persistence, section-aware retrieval, and extractive QA output. End-to-end testing can be done by ingesting a real corpus, running `ask`, and generating an evaluation report with `main.py evaluate`.

## Key Observations

- Layout-aware extraction improves readability compared to plain text extraction.
- Table-like blocks become retrievable even without a specialized table parser when chunked carefully.
- Embedded images benefit significantly from optional vision captioning, especially for charts and scanned content.
- Preserving figure titles, source notes, and footnote-like text improves retrieval quality for benchmark questions that would otherwise miss non-body-text evidence.
- A strong local fallback is valuable because it guarantees the system remains runnable under tight constraints.

## Conclusion

The final system is modular, free to run, and aligned with the assignment requirements when demonstrated on real reports. It demonstrates multi-modal ingestion, chunking, retrieval, grounded QA, source attribution, and benchmark evaluation while remaining easy to execute and extend.
