from __future__ import annotations

import json
from pathlib import Path
import pickle
import re

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from app.core.config import settings
from app.core.pdf_loader import load_document
from app.core.schemas import DocumentChunk, SourceEvidence

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class HybridRetriever:
    """Local hybrid retriever: SentenceTransformer vectors + BM25 with JSON/pickle persistence."""

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or settings.index_dir
        self.chunks: list[DocumentChunk] = []
        self.embeddings: np.ndarray | None = None
        self.bm25: BM25Okapi | None = None
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def build_from_paths(self, paths: list[Path]) -> int:
        all_chunks: list[DocumentChunk] = []
        for path in paths:
            all_chunks.extend(load_document(path))
        self.chunks = all_chunks
        texts = [c.text for c in self.chunks]
        if texts:
            emb = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
            self.embeddings = normalize(emb)
            self.bm25 = BM25Okapi([tokenize(t) for t in texts])
        self.save()
        return len(self.chunks)

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        (self.index_dir / 'chunks.jsonl').write_text(
            '\n'.join(c.model_dump_json() for c in self.chunks), encoding='utf-8'
        )
        if self.embeddings is not None:
            np.save(self.index_dir / 'embeddings.npy', self.embeddings)
        if self.bm25 is not None:
            with open(self.index_dir / 'bm25.pkl', 'wb') as f:
                pickle.dump(self.bm25, f)

    def load(self) -> bool:
        chunks_path = self.index_dir / 'chunks.jsonl'
        emb_path = self.index_dir / 'embeddings.npy'
        bm25_path = self.index_dir / 'bm25.pkl'
        if not chunks_path.exists() or not emb_path.exists() or not bm25_path.exists():
            return False
        self.chunks = [DocumentChunk(**json.loads(line)) for line in chunks_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        self.embeddings = np.load(emb_path)
        with open(bm25_path, 'rb') as f:
            self.bm25 = pickle.load(f)
        return True

    def search(self, query: str, top_k: int | None = None) -> list[SourceEvidence]:
        top_k = top_k or settings.top_k
        if not self.chunks or self.embeddings is None or self.bm25 is None:
            if not self.load():
                return []
        q_emb = normalize(self.model.encode([query], convert_to_numpy=True))
        vec_scores = cosine_similarity(q_emb, self.embeddings)[0]
        bm25_raw = np.array(self.bm25.get_scores(tokenize(query)), dtype=float)
        bm25_scores = bm25_raw / (bm25_raw.max() + 1e-9) if bm25_raw.size else bm25_raw
        hybrid = 0.62 * vec_scores + 0.38 * bm25_scores
        idxs = np.argsort(hybrid)[::-1][:top_k]
        return [
            SourceEvidence(
                chunk_id=self.chunks[i].chunk_id,
                source=self.chunks[i].source,
                page=self.chunks[i].page,
                score=float(hybrid[i]),
                text=self.chunks[i].text,
            )
            for i in idxs
        ]
