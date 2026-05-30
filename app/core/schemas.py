from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    source: str
    page: int
    text: str
    section_hint: str | None = None


class SourceEvidence(BaseModel):
    chunk_id: str
    source: str
    page: int
    score: float
    text: str


class RAGAnswer(BaseModel):
    question: str
    answer: str
    confidence: str
    citations: list[SourceEvidence]
    used_llm: bool = False
    warnings: list[str] = Field(default_factory=list)
