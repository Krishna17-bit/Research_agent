# Scientific PDF RAG + Research Agent

A Gemini-powered, citation-grounded research assistant for scientific papers, technical PDFs, theses, lab reports, SOPs, and figure-heavy research documents.

This project is built as a portfolio-ready and GitHub-ready demo of a practical research RAG system, not a toy chatbot. It supports PDF/TXT/MD ingestion, hybrid retrieval, citation-grounded answering, research workflows, and optional OCR for scanned or image-heavy PDFs.

## Why this exists

Many research-PDF chatbots fail in real research workflows because they:

- depend only on clean selectable PDF text,
- miss scanned pages and plot labels,
- do not show source evidence clearly,
- give polished answers without enough grounding,
- do not help with reproducibility, methodology extraction, or claim checking.

This tool focuses on the actual tasks researchers care about:

- understanding a paper quickly,
- extracting methods and results,
- finding limitations and research gaps,
- checking whether claims are supported,
- building a reproducibility checklist,
- searching across text, captions, and OCR/image-derived page text.

## Features

- Upload multiple PDF/TXT/MD files.
- Hybrid retrieval using SentenceTransformers + BM25.
- Gemini answer generation with inline citations.
- Offline extractive fallback when no Gemini key is provided.
- Optional OCR for scanned/image-only pages.
- Figure/table caption extraction from selectable PDF blocks.
- Page image saving for debugging OCR extraction.
- Markdown export for generated answers.
- Evidence map table with page, chunk type, and preview.
- GitHub-safe config with `.env.example` and no secrets committed.

## Research modes

The Streamlit app includes:

1. Ask a question
2. Research summary
3. Methodology extraction
4. Results / Figures / Tables extraction
5. Compare methods
6. Contributions
7. Limitations
8. Research gaps
9. Reproducibility checklist
10. Claim/evidence checker
11. Evidence map

## Tech stack

- Python
- Streamlit
- FastAPI
- Gemini API via `google-genai`
- PyMuPDF
- Tesseract OCR via `pytesseract`
- SentenceTransformers
- BM25 via `rank-bm25`
- Scikit-learn
- Pandas

## Setup on Windows / VS Code

Unzip the project, then open the inner project folder in VS Code.

```powershell
cd scientific_pdf_rag_agent
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Add your Gemini key in `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-pro
```

Run the app:

```powershell
streamlit run app\streamlit_app.py
```

Then upload a research PDF from the sidebar and click **Build / Rebuild Index**.

## OCR setup

OCR is optional but recommended for scanned papers and PDFs where plots/tables are embedded as images.

Install Tesseract OCR:

- Windows: install Tesseract OCR, then add it to PATH or set `TESSERACT_CMD` in `.env`.
- Linux: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`

Example Windows `.env` setting:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

OCR modes:

```env
OCR_MODE=off
OCR_MODE=auto
OCR_MODE=force
```

Recommended default:

```env
OCR_MODE=auto
```

Use `force` only when the PDF is heavily scanned or image-based, because it is slower.

## Notes on figure and plot extraction

This tool does not magically understand every plot the way a human would. It improves coverage by:

- extracting figure/table captions from PDF text blocks,
- running OCR on image-only or low-text pages,
- indexing OCR text such as plot labels, axis text, legends, table text, and annotations,
- preserving page citations so the user can inspect the original page.

For dense scientific plots, OCR quality depends on image resolution and chart text size.

## Environment variables

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-pro
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TOP_K=7
CHUNK_SIZE=900
CHUNK_OVERLAP=150
UPLOAD_DIR=app/storage/uploads
INDEX_DIR=app/storage/vector_index
OCR_MODE=auto
OCR_DPI=220
OCR_MIN_TEXT_CHARS=120
TESSERACT_CMD=
SAVE_PAGE_IMAGES=true
PAGE_IMAGE_DIR=app/storage/page_images
```

## GitHub push

```powershell
git init
git add .
git commit -m "Initial scientific PDF RAG research agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/scientific_pdf_rag_agent.git
git push -u origin main
```

Make sure `.env` is not committed.

## Project structure

```text
scientific_pdf_rag_agent/
├── app/
│   ├── core/
│   │   ├── agent.py
│   │   ├── config.py
│   │   ├── llm.py
│   │   ├── pdf_loader.py
│   │   ├── retriever.py
│   │   └── schemas.py
│   ├── api.py
│   ├── cli.py
│   └── streamlit_app.py
├── docs/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Safety and grounding

The assistant is instructed to answer only using retrieved evidence. It shows citations and evidence chunks so users can verify the source. If evidence is missing, it should say what is missing rather than inventing details.

## Limitations

- OCR can be noisy on low-resolution scans.
- Complex mathematical notation may not OCR cleanly.
- Plot interpretation is limited to extracted text, captions, labels, and retrieved context.
- Gemini API usage may incur cost depending on your account and usage.
