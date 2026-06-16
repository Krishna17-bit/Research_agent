from __future__ import annotations

import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel

from app.core.agent import ResearchAgent
from app.core.config import settings
from app.core.retriever import HybridRetriever
from app.core.llm import active_provider, generate_answer
from app.core.schemas import RAGAnswer, SourceEvidence
from app.core import database

api = FastAPI(
    title="Research PDF RAG Agent API",
    description="REST API for citation-grounded RAG, multi-document comparison, notes management, and model analytics.",
    version="1.0.0"
)


# --- Schemas ---

class AskRequest(BaseModel):
    question: str
    top_k: int | None = None
    doc_ids: list[str] | None = None


class RetrieveRequest(BaseModel):
    query: str
    top_k: int | None = None
    doc_ids: list[str] | None = None


class WorkspaceFilterRequest(BaseModel):
    doc_ids: list[str] | None = None


class CompareRequest(BaseModel):
    doc_ids: list[str]


class NoteCreateRequest(BaseModel):
    document_id: str | None = None
    workspace_id: str | None = None
    page_number: int | None = None
    note_type: str = "user note"
    title: str | None = None
    content: str
    tags: str | None = None


# --- Endpoints ---

@api.get("/health")
def health():
    return {"status": "ok", "provider": active_provider(), "mock_mode": settings.mock_mode}


@api.get("/api/documents")
def list_documents():
    docs = database.get_all_documents()
    return [dict(d) for d in docs]


@api.post("/api/documents/upload")
def upload_document(file: UploadFile = File(...)):
    # Size validation (20MB limit)
    try:
        file_bytes = file.file.read()
        if len(file_bytes) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File exceeds maximum size limit of 20MB.")
        
        # Save temp copy
        out_path = settings.upload_dir / file.filename
        with out_path.open("wb") as f:
            f.write(file_bytes)
            
        retriever = HybridRetriever()
        count = retriever.build_from_paths([out_path])
        doc_id = Path(out_path).name  # simplified
        
        # Look up added doc to return detail
        return {"status": "success", "indexed_chunks": count, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@api.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    try:
        f_path = Path(doc["file_path"])
        if f_path.exists():
            f_path.unlink()
        
        # Clear cached vector files
        emb_f = settings.index_dir.parent / "embeddings" / f"{doc_id}.npy"
        chunk_f = settings.index_dir.parent / "chunks" / f"{doc_id}.json"
        if emb_f.exists():
            emb_f.unlink()
        if chunk_f.exists():
            chunk_f.unlink()
            
        database.delete_document(doc_id)
        
        # Reload global active index
        HybridRetriever().load()
        return {"status": "success", "detail": f"Document {doc_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/documents/{doc_id}/reprocess")
def reprocess_document(doc_id: str):
    doc = database.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        retriever = HybridRetriever()
        count = retriever.build_from_paths([Path(doc["file_path"])])
        return {"status": "success", "indexed_chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/ask")
def ask(req: AskRequest):
    try:
        agent = ResearchAgent()
        res = agent.ask(req.question, top_k=req.top_k, doc_ids=req.doc_ids)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/retrieve")
def retrieve(req: RetrieveRequest):
    try:
        retriever = HybridRetriever()
        evidence = retriever.search(req.query, top_k=req.top_k, doc_ids=req.doc_ids)
        return [dict(e) for e in evidence]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/summarize")
def summarize(req: WorkspaceFilterRequest):
    try:
        agent = ResearchAgent()
        res = agent.summarize(doc_ids=req.doc_ids)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/compare")
def compare(req: CompareRequest):
    try:
        agent = ResearchAgent()
        res = agent.compare_methods(doc_ids=req.doc_ids)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/research-gaps")
def find_research_gaps(req: CompareRequest):
    try:
        agent = ResearchAgent()
        res = agent.research_gap_analysis(doc_ids=req.doc_ids)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.post("/api/methodology")
def extract_methodology(req: CompareRequest):
    try:
        agent = ResearchAgent()
        res = agent.extract_methodology(doc_ids=req.doc_ids)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Notes CRUD ---

@api.get("/api/notes")
def get_notes():
    notes = database.get_notes()
    return [dict(n) for n in notes]


@api.post("/api/notes")
def create_note(req: NoteCreateRequest):
    try:
        note_id = database.add_note(
            document_id=req.document_id,
            workspace_id=req.workspace_id,
            page_number=req.page_number,
            note_type=req.note_type,
            title=req.title,
            content=req.content,
            tags=req.tags
        )
        return {"status": "success", "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api.delete("/api/notes/{note_id}")
def delete_note(note_id: str):
    try:
        database.delete_note(note_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Telemetry & Analytics ---

@api.get("/api/runs")
def get_runs():
    runs = database.get_runs()
    return [dict(r) for r in runs]


@api.get("/api/evals")
def get_evals():
    evals = database.get_eval_runs()
    return [dict(eh) for eh in evals]
