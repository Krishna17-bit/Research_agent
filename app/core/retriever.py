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
from app.core.pdf_loader import load_document, extract_metadata, _doc_id
from app.core.schemas import DocumentChunk, SourceEvidence
from app.core import database

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class HybridRetriever:
    """
    Dynamic hybrid retriever. Stores embeddings and chunks per-document,
    allowing fast incremental updates and workspace-level indexing.
    """

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or settings.index_dir
        self.chunks_dir = self.index_dir.parent / "chunks"
        self.embs_dir = self.index_dir.parent / "embeddings"
        
        # Ensure directories exist
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.embs_dir.mkdir(parents=True, exist_ok=True)

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
        """
        Process documents: chunk them, embed them, save them to the disk cache,
        catalog them in SQLite, and compile the memory search index.
        """
        total_chunks = 0
        for path in paths:
            if not path.exists():
                continue
            
            doc_id = _doc_id(path)
            
            # 1. Parse and chunk document
            chunks = load_document(path)
            if not chunks:
                continue

            # Save chunks to json file
            chunk_file = self.chunks_dir / f"{doc_id}.json"
            with chunk_file.open("w", encoding="utf-8") as f:
                json.dump([c.model_dump() for c in chunks], f, indent=2)

            # 2. Check and generate embeddings
            emb_file = self.embs_dir / f"{doc_id}.npy"
            if emb_file.exists():
                # Load existing embeddings
                doc_embs = np.load(emb_file)
            else:
                # Encode and save
                texts = [c.text for c in chunks]
                emb = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
                doc_embs = normalize(emb)
                np.save(emb_file, doc_embs)

            # 3. Extract and save metadata to database
            meta = extract_metadata(path)
            database.add_document(
                doc_id=doc_id,
                file_name=path.name,
                file_path=str(path.resolve()),
                title=meta["title"],
                authors=meta["authors"],
                year=meta["year"],
                doc_type=meta["doc_type"],
                tags=meta["tags"],
                page_count=meta["page_count"],
                chunk_count=len(chunks),
                status="indexed"
            )
            # Add to default workspace
            database.add_document_to_workspace("default", doc_id)
            total_chunks += len(chunks)

        # Recompile memory index for all documents
        self.load()
        return total_chunks

    def load(self) -> bool:
        """Load and build index from all indexed documents in the library."""
        docs = database.get_all_documents()
        doc_ids = [d["id"] for d in docs if d["status"] == "indexed"]
        return self.load_active_index(doc_ids)

    def load_active_index(self, doc_ids: list[str]) -> bool:
        """Dynamically concatenate embeddings/chunks and compile the BM25 index for specified doc_ids."""
        self.chunks = []
        embs_list = []

        if not doc_ids:
            self.embeddings = None
            self.bm25 = None
            return False

        for doc_id in doc_ids:
            chunk_file = self.chunks_dir / f"{doc_id}.json"
            emb_file = self.embs_dir / f"{doc_id}.npy"

            if chunk_file.exists() and emb_file.exists():
                try:
                    with chunk_file.open("r", encoding="utf-8") as f:
                        c_data = json.load(f)
                    chunks = [DocumentChunk(**c) for c in c_data]
                    embs = np.load(emb_file)
                    
                    self.chunks.extend(chunks)
                    embs_list.append(embs)
                except Exception:
                    # skip corrupted files
                    continue

        if not self.chunks or not embs_list:
            self.embeddings = None
            self.bm25 = None
            return False

        self.embeddings = np.vstack(embs_list)
        
        # Build BM25 index on active chunks
        texts = [c.text for c in self.chunks]
        self.bm25 = BM25Okapi([tokenize(t) for t in texts])
        return True

    def save(self) -> None:
        """Mock save method for backward compatibility."""
        pass

    def search(self, query: str, top_k: int | None = None, doc_ids: list[str] | None = None) -> list[SourceEvidence]:
        """
        Search for relevant chunks using hybrid lexical-semantic matching.
        If doc_ids is specified, search is restricted to those documents.
        """
        top_k = top_k or settings.top_k
        
        # Ensure we have a loaded index
        if not self.chunks or self.embeddings is None or self.bm25 is None:
            # If doc_ids are specified, load them, otherwise load everything
            if doc_ids is not None:
                if not self.load_active_index(doc_ids):
                    return []
            else:
                if not self.load():
                    return []
        
        # Compile temporary subset index if doc_ids is provided and different from loaded
        loaded_doc_ids = set(c.doc_id for c in self.chunks)
        if doc_ids is not None and set(doc_ids) != loaded_doc_ids:
            # Temporarily build filter indices
            filter_indices = [i for i, c in enumerate(self.chunks) if c.doc_id in doc_ids]
            if not filter_indices:
                return []
            
            # Extract subset
            subset_chunks = [self.chunks[i] for i in filter_indices]
            subset_embs = self.embeddings[filter_indices]
            subset_bm25 = BM25Okapi([tokenize(c.text) for c in subset_chunks])
            
            # Search subset
            q_emb = normalize(self.model.encode([query], convert_to_numpy=True))
            vec_scores = cosine_similarity(q_emb, subset_embs)[0]
            bm25_raw = np.array(subset_bm25.get_scores(tokenize(query)), dtype=float)
            bm25_scores = bm25_raw / (bm25_raw.max() + 1e-9) if bm25_raw.size else bm25_raw
            hybrid = 0.62 * vec_scores + 0.38 * bm25_scores
            
            # Apply similarity threshold
            valid_indices = [idx for idx in np.argsort(hybrid)[::-1] if hybrid[idx] >= settings.similarity_threshold]
            idxs = valid_indices[:top_k]
            
            return [
                SourceEvidence(
                    chunk_id=subset_chunks[i].chunk_id,
                    source=subset_chunks[i].source,
                    page=subset_chunks[i].page,
                    score=float(hybrid[i]),
                    text=subset_chunks[i].text,
                )
                for i in idxs
            ]

        # Normal search across all loaded chunks
        q_emb = normalize(self.model.encode([query], convert_to_numpy=True))
        vec_scores = cosine_similarity(q_emb, self.embeddings)[0]
        bm25_raw = np.array(self.bm25.get_scores(tokenize(query)), dtype=float)
        bm25_scores = bm25_raw / (bm25_raw.max() + 1e-9) if bm25_raw.size else bm25_raw
        hybrid = 0.62 * vec_scores + 0.38 * bm25_scores
        
        # Apply similarity threshold
        valid_indices = [idx for idx in np.argsort(hybrid)[::-1] if hybrid[idx] >= settings.similarity_threshold]
        idxs = valid_indices[:top_k]
        
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
