# Research PDF RAG Agent — API Reference Guide

The Research PDF RAG Agent provides a comprehensive REST API to programmatically upload papers, ask citation-grounded questions, synthesize reviews, extract methodologies, and manage annotations.

---

## Base URL
All API requests should be sent to:
```text
http://localhost:8000
```
*(assuming FastAPI server runs on port 8000)*

---

## Endpoints

### 1. Ingestion & Documents

#### `GET /api/documents`
List all cataloged documents in the database.
- **Response**: `200 OK`
- **Example Response**:
```json
[
  {
    "id": "7ad4b8ea1c32b509",
    "file_name": "scientific_rag_demo_paper.txt",
    "file_path": "/workspace/app/storage/uploads/scientific_rag_demo_paper.txt",
    "title": "A Demonstration Study on Citation-Grounded Retrieval-Augmented Generation",
    "authors": "Unknown",
    "year": "2026",
    "doc_type": "paper",
    "tags": "imported",
    "page_count": 1,
    "chunk_count": 4,
    "status": "indexed",
    "upload_date": "2026-06-16T11:45:12.435"
  }
]
```

#### `POST /api/documents/upload`
Upload a document (PDF, TXT, MD) to the ingestion pipeline (max 20MB).
- **Request**: Multipart Form Data with a `file` field.
- **Response**: `200 OK`
- **Example Response**:
```json
{
  "status": "success",
  "indexed_chunks": 4,
  "filename": "my_paper.pdf"
}
```

#### `DELETE /api/documents/{doc_id}`
Delete a document catalog metadata and local chunk/embedding storage.
- **Response**: `200 OK`
- **Example Response**:
```json
{
  "status": "success",
  "detail": "Document 7ad4b8ea1c32b509 deleted."
}
```

#### `POST /api/documents/{doc_id}/reprocess`
Reparse text layout and recompute vectors for a document.
- **Response**: `200 OK`
- **Example Response**:
```json
{
  "status": "success",
  "indexed_chunks": 4
}
```

---

### 2. Retrieval & Grounded Q&A

#### `POST /api/ask`
Execute a citation-grounded Q&A query.
- **Request Body**:
```json
{
  "question": "What is the similarity threshold set for hybrid search?",
  "top_k": 5,
  "doc_ids": ["7ad4b8ea1c32b509"]
}
```
*(Leave `doc_ids` empty or null to search the entire active library.)*
- **Response**:
```json
{
  "question": "What is the similarity threshold set for hybrid search?",
  "answer": "The hybrid retrieval combines semantic and lexical search... [health_check.pdf p.1].",
  "confidence": "high",
  "citations": [
    {
      "chunk_id": "7ad4b8ea1c32b509:p1:c0",
      "source": "health_check.pdf",
      "page": 1,
      "score": 0.85,
      "text": "The hybrid similarity threshold is configured at 0.20..."
    }
  ],
  "used_llm": true,
  "warnings": []
}
```

#### `POST /api/retrieve`
Fetch raw matching chunks with semantic/lexical similarity scores without generating an answer.
- **Request Body**: Same as `/api/ask`
- **Response**: Array of matching `SourceEvidence` blocks.

---

### 3. Synthesis & Analytical Tools

#### `POST /api/summarize`
Synthesize a structured research brief of specific papers.
- **Request Body**: `{"doc_ids": ["7ad4b8ea1c32b509"]}`
- **Response**: `RAGAnswer` JSON.

#### `POST /api/compare`
Generate a comparative methodology matrix of 2+ papers.
- **Request Body**: `{"doc_ids": ["doc_a_id", "doc_b_id"]}`
- **Response**: `RAGAnswer` JSON.

---

### 4. Research Notes CRUD

#### `GET /api/notes`
Get list of all saved research notes.
- **Response**: `200 OK`

#### `POST /api/notes`
Save a research note or annotation.
- **Request Body**:
```json
{
  "document_id": "7ad4b8ea1c32b509",
  "note_type": "method",
  "title": "Methodology parameters note",
  "content": "Baseline setup includes MiniLM embedding vectors...",
  "tags": "method, parameters"
}
```
- **Response**: `{"status": "success", "note_id": "3aefd40c"}`

#### `DELETE /api/notes/{note_id}`
Delete a note.
- **Response**: `{"status": "success"}`

---

## Client Integration Examples

### Python (Requests)
```python
import requests

# Ask a citation-grounded question
res = requests.post(
    "http://localhost:8000/api/ask",
    json={
        "question": "What baseline datasets were evaluated?",
        "top_k": 6
    }
)
data = res.json()
print("Answer:", data["answer"])
print("Confidence:", data["confidence"])
print("Citations:")
for c in data["citations"]:
    print(f"- {c['source']} page {c['page']} (score: {c['score']})")
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Summarize core limitations", "top_k": 5}'
```
