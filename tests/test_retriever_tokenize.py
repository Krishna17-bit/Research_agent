from app.core.retriever import tokenize


def test_tokenize_keeps_scientific_terms():
    assert "bm25" in tokenize("BM25 retrieval for PDF-RAG systems")
    assert "pdf-rag" in tokenize("BM25 retrieval for PDF-RAG systems")
