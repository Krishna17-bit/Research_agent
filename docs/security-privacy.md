# Research PDF RAG Agent — Security & Privacy Model

This document outlines the security controls, key handling, and data privacy principles of the Research PDF RAG Agent.

---

## 1. Local-First Design (Local Data Isolation)
By default, the Research PDF RAG Agent is built for local-first operations:
- **Vector Processing**: Embeddings are computed locally using HuggingFace models (`sentence-transformers`) and stored in the localized `app/storage/embeddings/` directory. No text is uploaded to external embeddings APIs.
- **Structured Database**: Metadata catalog, notes, telemetry, and benchmarks are saved in a local SQLite database (`app/storage/research_agent.db`).
- **Scanned Images**: Cached OCR page images are kept inside the workspace `app/storage/page_images/` directory.

---

## 2. API Key Management & Secrets Safety
To protect API keys and credentials:
- **Environment Separation**: API keys for Gemini, OpenAI, Anthropic, Groq, and Mistral are stored in a local `.env` file. This file is added to `.gitignore` and is **never** committed to version control.
- **Secret Masking**: The UI Settings page masks inputs (using Streamlit's `type="password"` option) to prevent keys from being visible in screenshots or screenshares.
- **Connection Diagnostics**: Setting checks do not log keys, and error stack traces redact secret strings before displaying warnings to users.

---

## 3. Ingestion Security & File Boundaries
To prevent denial-of-service (DoS) or path traversal attacks:
- **File Validation**: Upload files are validated. The server enforces a size limit of **20MB** per file and verifies header signatures (such as `%PDF` for PDF documents) to block executables.
- **Path Resolution**: File paths are strictly resolved against `settings.upload_dir` and the project root to prevent path traversal exploits (`../`).
- **Input Sanitization**: Database queries leverage parameterized SQL statements via Python's standard `sqlite3` driver, completely neutralizing SQL injection risks.

---

## 4. Multi-Provider API Data Flows
When using real API LLM providers, be aware of where text flows:
- **Mock Mode**: Text remains completely local.
- **Ollama**: Text is sent to your local Ollama port (`localhost:11434`), maintaining local isolation.
- **Cloud LLM APIs (Gemini, OpenAI, Anthropic, Groq, Mistral)**: Only the matching retrieved evidence chunks and the user's question are sent to the provider. The rest of the document corpus remains local and is never uploaded.
- **Privacy Warning**: If you are working with confidential documents, trade secrets, or patient data, do not configure cloud LLM API keys. Use local Ollama models or Mock Mode to ensure zero data leakage.
