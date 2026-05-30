from __future__ import annotations

import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from app.core.agent import ResearchAgent
from app.core.config import settings
from app.core.retriever import HybridRetriever

api = FastAPI(title="Scientific PDF RAG + Research Agent", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    top_k: int | None = None


@api.get("/health")
def health():
    return {"status": "ok"}


@api.post("/upload")
def upload(files: list[UploadFile] = File(...)):
    saved: list[Path] = []
    for file in files:
        out = settings.upload_dir / file.filename
        with out.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        saved.append(out)
    count = HybridRetriever().build_from_paths(saved)
    return {"indexed_chunks": count, "files": [p.name for p in saved]}


@api.post("/ask")
def ask(req: AskRequest):
    return ResearchAgent().ask(req.question, top_k=req.top_k).model_dump()


@api.post("/summarize")
def summarize():
    return ResearchAgent().summarize().model_dump()
