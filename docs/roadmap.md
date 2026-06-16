# Research PDF RAG Agent — Product Roadmap

This document outlines the features implemented in this release and our future roadmap for technical and academic research.

---

## 📅 Released Upgrades (Completed)

We have upgraded the MVP into a production-ready application by implementing:
- **Lightweight DB Persistence**: Switched to SQLite database (`app/storage/research_agent.db`) to record documents cataloging, projects workspaces, notes, history logs, and evals.
- **Incremental Embedding Cache**: Generates vectors per-document and saves them to disk, allowing instant workspace index compilation, deletions, and zero re-embedding overhead.
- **Multi-Provider API Router**: Native support for Gemini, OpenAI, Anthropic, Groq, Mistral, Ollama, and Custom endpoints.
- **Mock Mode**: Fully interactive mock mode enabling hello-world testing and page syntheses without paid keys.
- **Citation Verification Engine**: Scans text for citation tags, validates them against evidence files/pages, and calculates word overlap Jaccard scores.
- **Multipage Streamlit Navigation**: Integrated `st.navigation` for structured layouts.
- **Evaluation Benchmark Suite**: Diagnostic testing on expected scientific terms.

---

## 📈 Phase 2: Near-Term Enhancements (Q3 2026)

- **Interactive PDF Viewer with Highlighting**: Render and display the cited PDF pages in the Streamlit UI with highlighting on the verified text chunk.
- **Dynamic Table Parsing (LayoutParser/Unstructured)**: Integrate layout-aware parsing libraries to convert document tables directly to Markdown/CSV tables.
- **BibTeX/RIS Auto-Lookup**: Integrate DOI lookup APIs (like OpenAlex or CrossRef) to fetch academic citations automatically on upload.

---

## 🚀 Phase 3: Long-Term Enterprise Features (Q4 2026 - 2027)

- **PostgreSQL & Qdrant Integration**: Provide configuration instructions and drivers to swap SQLite/local vectors for Postgres + Qdrant.
- **SSO Authentication & Workspaces Isolation**: Add OAuth/OpenID login and role-based permissions (Researcher, Reviewer, Read-Only) to isolate libraries across multi-user deployments.
- **Automated RAG Benchmarking**: Schedule weekly evaluation cron-jobs that run test suites and alert developers if RAG answer grounding falls below thresholds.
