from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mm_rag.config import Settings
from mm_rag.embeddings import build_embedder, resolve_backend
from mm_rag.evaluation import load_benchmarks, run_benchmarks, save_benchmark_report
from mm_rag.ingestion import PDFIngestor
from mm_rag.qa import QASystem
from mm_rag.retrieval import VectorStore
from mm_rag.utils import ensure_dir


DATA_DIR = ROOT / "data"
SAMPLE_DIR = DATA_DIR / "sample_corpus"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEX_DIR = ROOT / "storage" / "index"
EVAL_DIR = ROOT / "storage" / "evaluation"
BENCHMARKS_PATH = DATA_DIR / "benchmarks" / "economic_report_questions.json"
ENV_FILE = ROOT / ".env"


def _ensure_dirs() -> None:
    for path in [DATA_DIR, SAMPLE_DIR, UPLOADS_DIR, INDEX_DIR.parent, EVAL_DIR]:
        ensure_dir(path)


def _load_sources() -> list[dict]:
    path = SAMPLE_DIR / "sources.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("sources", []))


def _list_pdfs(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")


def _save_uploaded_files(files, target_dir: Path) -> list[Path]:
    ensure_dir(target_dir)
    saved: list[Path] = []
    for file in files:
        destination = target_dir / file.name
        destination.write_bytes(file.getbuffer())
        saved.append(destination)
    return saved


def _build_index(folder: Path, backend: str, env_file: Path, index_dir: Path, asset_dir: Path) -> dict:
    settings = Settings.from_env(env_file)
    backend_kind = resolve_backend(backend, settings)
    ingestion_settings = settings
    if backend_kind == "local":
        ingestion_settings = replace(settings, google_api_key=None, enable_image_captioning=False)

    pdf_paths = _list_pdfs(folder)
    if not pdf_paths:
        raise ValueError(f"No PDF files found in {folder}")

    ingestor = PDFIngestor(ingestion_settings)
    chunks = ingestor.ingest_many(pdf_paths, asset_dir=asset_dir)
    embedder = build_embedder(backend_kind, settings)
    store = VectorStore.build(chunks, embedder, backend_kind=backend_kind)
    store.save(index_dir)

    modality_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    for chunk in chunks:
        modality_counts[chunk.modality] = modality_counts.get(chunk.modality, 0) + 1
        role = chunk.metadata.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    return {
        "documents": sorted({chunk.document_name for chunk in chunks}),
        "chunks": len(chunks),
        "modality_counts": modality_counts,
        "role_counts": role_counts,
        "backend": backend_kind,
    }


def _load_runtime(index_dir: Path, env_file: Path, generator: str = "auto"):
    settings = Settings.from_env(env_file)
    store = VectorStore.load(index_dir)
    embedder = build_embedder(store.backend_kind, settings, state=store.backend_state)
    generator_backend = generator
    if generator == "auto":
        generator_backend = "gemini" if store.backend_kind == "gemini" else "local"
    qa = QASystem(settings, backend=generator_backend)
    return store, embedder, qa


def _read_index_summary(index_dir: Path) -> dict | None:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _index_matches_corpus(index_summary: dict | None, pdfs: list[Path]) -> tuple[bool, str | None]:
    if not index_summary:
        return False, "No saved index found yet."
    indexed_docs = set(index_summary.get("documents", []))
    corpus_docs = {pdf.name for pdf in pdfs}
    if not corpus_docs:
        return False, "No real PDFs are present in the selected corpus folder yet."
    if indexed_docs != corpus_docs:
        return False, "The saved index does not match the PDFs currently in your corpus folder. Rebuild the index first."
    return True, None


def _render_answer(question: str, index_dir: Path, env_file: Path, top_k: int, generator: str) -> None:
    store, embedder, qa = _load_runtime(index_dir, env_file, generator=generator)
    results = store.search(question, embedder, top_k=top_k)
    answer = qa.answer(question, results)

    st.subheader("Answer")
    st.write(answer.answer_text)
    st.caption(f"Mode: {answer.generator}")

    if answer.warning:
        st.warning(answer.warning)

    if answer.citations:
        st.markdown("**Citations**")
        for citation in answer.citations:
            st.write(f"- {citation}")

    with st.expander("Retrieved Context"):
        for result in answer.context:
            st.write(f"score={result.score:.4f} | {result.chunk.citation} | {result.chunk.modality}")
            st.write(result.chunk.content)
            st.divider()


def _render_benchmark(index_dir: Path, env_file: Path, output_dir: Path, top_k: int, generator: str) -> None:
    store, embedder, qa = _load_runtime(index_dir, env_file, generator=generator)
    benchmarks = load_benchmarks(BENCHMARKS_PATH)
    report = run_benchmarks(store, embedder, qa, benchmarks, top_k=top_k)
    json_path, markdown_path = save_benchmark_report(report, output_dir)

    st.success("Benchmark evaluation complete.")
    st.write(report["summary"])
    st.write(f"JSON report: {json_path}")
    st.write(f"Markdown report: {markdown_path}")

    with st.expander("Benchmark Answers"):
        for item in report["results"]:
            st.markdown(f"**{item['question']}**")
            st.write(item["answer"])
            if item["citations"]:
                st.write("Citations:")
                for citation in item["citations"]:
                    st.write(f"- {citation}")
            st.divider()


def main() -> None:
    _ensure_dirs()
    st.set_page_config(page_title="DSAI413 Multi-Modal RAG", layout="wide")
    st.title("DSAI 413 Multi-Modal Document Intelligence")
    st.write(
        "A browser UI for building and testing the multi-modal RAG system on real policy or financial PDF reports."
    )

    with st.sidebar:
        st.header("Run Settings")
        corpus_dir = st.text_input("PDF folder", value=str(SAMPLE_DIR))
        index_dir_text = st.text_input("Index folder", value=str(INDEX_DIR))
        env_file_text = st.text_input("Env file", value=str(ENV_FILE))
        backend = st.selectbox("Embedding backend", ["local", "gemini"], index=0)
        generator = st.selectbox("Answer generator", ["auto", "local", "gemini"], index=0)
        top_k = st.slider("Top-k retrieval", min_value=3, max_value=12, value=8)

        st.markdown("**Quick sources**")
        for source in _load_sources():
            st.markdown(f"- [{source['title']}]({source['publication_page']})")

    left, right = st.columns([1.1, 0.9])

    with left:
        st.subheader("1. Add Real PDFs")
        st.write(
            "Use the official IMF links in `data/sample_corpus/README.md`, download the PDFs in your browser, "
            "and save them into the selected folder below."
        )
        st.code(str(Path(corpus_dir)), language="text")

        uploaded_files = st.file_uploader(
            "Or upload PDFs directly here",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            saved = _save_uploaded_files(uploaded_files, Path(corpus_dir))
            st.success(f"Saved {len(saved)} PDF(s) into {Path(corpus_dir)}")

        pdfs = _list_pdfs(Path(corpus_dir))
        st.markdown("**Detected PDFs**")
        if pdfs:
            for pdf in pdfs:
                st.write(f"- {pdf.name}")
        else:
            st.info("No PDFs found yet. Download real reports first or upload them here.")

        index_summary = _read_index_summary(Path(index_dir_text))
        st.markdown("**Current Index Status**")
        if index_summary:
            st.write(f"Backend: {index_summary['backend_kind']}")
            st.write("Indexed documents:")
            for document in index_summary.get("documents", []):
                st.write(f"- {document}")
        else:
            st.info("No saved index found yet. Build the index after adding PDFs.")
        index_ok, index_message = _index_matches_corpus(index_summary, pdfs)
        if index_message:
            st.warning(index_message)

        st.subheader("2. Build Index")
        if st.button("Build / Rebuild Index", use_container_width=True):
            try:
                with st.spinner("Building multimodal index..."):
                    summary = _build_index(
                        folder=Path(corpus_dir),
                        backend=backend,
                        env_file=Path(env_file_text),
                        index_dir=Path(index_dir_text),
                        asset_dir=ROOT / "storage" / "assets",
                    )
                st.success("Index build complete.")
                st.json(summary)
            except Exception as exc:
                st.error(str(exc))

        st.subheader("3. Run Benchmarks")
        if st.button("Run Assignment Benchmark Suite", use_container_width=True):
            try:
                index_summary = _read_index_summary(Path(index_dir_text))
                index_ok, index_message = _index_matches_corpus(index_summary, pdfs)
                if not index_ok:
                    st.error(index_message or "Please rebuild the index first.")
                    st.stop()
                with st.spinner("Running benchmark questions..."):
                    _render_benchmark(
                        index_dir=Path(index_dir_text),
                        env_file=Path(env_file_text),
                        output_dir=EVAL_DIR,
                        top_k=top_k,
                        generator=generator,
                    )
            except Exception as exc:
                st.error(str(exc))

    with right:
        st.subheader("4. Ask Questions")
        sample_questions = [
            "What are the main fiscal risks discussed in the reports?",
            "What does the report say about inflation and monetary policy?",
            "Which table contains the main macroeconomic indicators?",
            "What structural reforms are recommended?",
            "Are there any notes or source statements that affect interpretation?",
        ]
        selected_question = st.selectbox("Sample questions", [""] + sample_questions)
        default_question = selected_question or st.session_state.get("question_input", "")
        question = st.text_area(
            "Question",
            value=default_question,
            height=120,
            placeholder="Type a question about your uploaded reports...",
            key="question_input",
        )
        if st.button("Ask", use_container_width=True):
            try:
                if not question.strip():
                    st.error("Please type a question first.")
                    st.stop()
                index_summary = _read_index_summary(Path(index_dir_text))
                index_ok, index_message = _index_matches_corpus(index_summary, _list_pdfs(Path(corpus_dir)))
                if not index_ok:
                    st.error(index_message or "Please rebuild the index first.")
                    st.stop()
                with st.spinner("Retrieving evidence and generating answer..."):
                    _render_answer(
                        question=question.strip(),
                        index_dir=Path(index_dir_text),
                        env_file=Path(env_file_text),
                        top_k=top_k,
                        generator=generator,
                    )
            except Exception as exc:
                st.error(str(exc))

        with st.expander("Where do I find PDFs to upload?"):
            st.write("Use real policy or financial reports. Good starting points:")
            for source in _load_sources():
                st.markdown(f"- [{source['title']}]({source['publication_page']})")
                st.caption(f"Direct PDF: {source['pdf_url']}")
            st.write(
                "The easiest path is: open the publication page in your browser, click Download PDF, "
                "then save it into `data/sample_corpus`."
            )

        with st.expander("Good video demo flow"):
            st.write("1. Show the uploaded PDFs")
            st.write("2. Click Build / Rebuild Index")
            st.write("3. Ask 2 to 3 sample questions")
            st.write("4. Run the benchmark suite")
            st.write("5. Open the generated report in storage/evaluation")


if __name__ == "__main__":
    main()
