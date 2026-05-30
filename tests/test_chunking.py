from app.core.pdf_loader import chunk_text


def test_chunk_text_returns_chunks():
    text = "Sentence one. " * 200
    chunks = chunk_text(text, size=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) > 30 for c in chunks)
