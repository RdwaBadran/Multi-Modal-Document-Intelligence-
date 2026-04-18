# Video Demo Script

## Goal

Record a 2 to 5 minute walkthrough showing the pipeline, the QA demo, and the design rationale on **real report PDFs**.

## Suggested Flow

1. Show the project structure  
   Briefly open the codebase and explain the key modules: ingestion, embeddings, retrieval, evaluation, QA, CLI, and Streamlit UI.

2. Explain the free-stack design  
   Mention that the system works with no paid APIs. Point out the local fallback mode and optional Google AI Studio integration.

3. Show the real corpus  
   Open `data/sample_corpus` or the folder where you saved real IMF or policy PDFs.

4. Launch the browser UI  
   Run:

   ```powershell
   python -m streamlit run streamlit_app.py
   ```

5. Build the index live  
   In the browser UI, point the app at `data/sample_corpus` and click `Build / Rebuild Index`.

6. Ask a few questions  
   Use the browser UI question box.

7. Run the benchmark suite  
   Click `Run Assignment Benchmark Suite`.

8. Optionally show the CLI equivalent  
   Run:

   ```powershell
   python main.py ingest "data\sample_corpus" --backend local --index-dir storage\index
   python main.py ask "What are the main fiscal risks discussed in the reports?" --index-dir storage\index --show-context
   python main.py evaluate --index-dir storage\index --benchmarks data\benchmarks\economic_report_questions.json --output-dir storage\evaluation
   ```

9. Show the chat interface  
   Run:

   ```powershell
   python main.py chat --index-dir storage\index
   ```

10. Highlight citations and modalities  
   Point out that answers include page-level citations and that retrieval can return text, table, figure metadata, footnotes, and image-derived chunks.

11. Close with architecture summary  
   Mention:
   - multi-modal ingestion
   - unified retrieval
   - grounded QA
   - benchmark evaluation
   - local free mode plus optional Gemini enhancement
