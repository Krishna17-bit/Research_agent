# Research PDF RAG Agent — Deployment & Setup Guide

This document describes how to deploy and configure the Research PDF RAG Agent locally or in production environments.

---

## 💻 Local Setup (Bare Metal)

### Prerequisites
- Python 3.10 or 3.11 installed
- Tesseract OCR (Optional, for scanned PDFs)
  - **Windows**: Install Tesseract and add to system PATH or configure in `.env`.
  - **Ubuntu**: `sudo apt-get install tesseract-ocr`
  - **macOS**: `brew install tesseract`

### Step 1: Install Dependencies
Clone the repository and install requirements:
```bash
git clone https://github.com/your-username/research-pdf-rag-agent.git
cd research-pdf-rag-agent
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and fill in API keys:
```bash
cp .env.example .env
```
Default parameters in `.env`:
```env
LLM_PROVIDER=gemini
MOCK_MODE=true # Set to false to use real LLM APIs
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Step 3: Run the Streamlit Interface
Start the dashboard and workspace UI:
```bash
streamlit run app/streamlit_app.py
```
Open `http://localhost:8501` in your browser.

### Step 4: Run the API Server
Start the FastAPI REST server:
```bash
uvicorn app.api:api --host 0.0.0.0 --port 8000
```
API docs are available at `http://localhost:8000/docs`.

---

## 🐳 Docker Deployment

A `Dockerfile` and `docker-compose.yml` are provided in the repository root.

### Build & Run with Docker Compose
Run the entire stack (Streamlit UI + FastAPI API + SQLite storage) inside isolated containers:
```bash
docker compose up --build
```
This maps:
- Streamlit UI: `http://localhost:8501`
- FastAPI REST API: `http://localhost:8000`
- Persistent storage: Mapped to local folder `./app/storage`.

---

## 🛠️ Troubleshooting

### 1. Tesseract OCR binary not found (Windows)
If you get `pytesseract.TesseractNotFoundError` on Windows, download Tesseract OCR binary, install it, and add the path to `.env`:
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 2. SentenceTransformers Model Download Timeout
On slow connections, downloading the embedding model on first start can time out. Pre-download the model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
```

### 3. Missing Database Errors
The SQLite database file `research_agent.db` is initialized automatically on startup. If you encounter write locks or permission errors, ensure the `app/storage` directory has read-write permissions.
