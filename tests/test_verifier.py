from app.core.verifier import verify_citations, clean_source_name
from app.core.schemas import SourceEvidence


def test_clean_source_name():
    assert clean_source_name("Paper.pdf") == "paper"
    assert clean_source_name("scientific-rag_demo_paper.TXT") == "scientificragdemopaper"
    assert clean_source_name("My Research_Outline 2026.md") == "myresearchoutline2026"


def test_verify_citations_success():
    evidence = [
        SourceEvidence(
            chunk_id="doc1:p1",
            source="paper_one.pdf",
            page=1,
            score=0.9,
            text="The baseline RAG model parameters are evaluated with a context window of 8000 tokens."
        ),
        SourceEvidence(
            chunk_id="doc2:p3",
            source="paper_two.pdf",
            page=3,
            score=0.8,
            text="We introduce a hybrid retrieval framework combining SentenceTransformers and BM25 search."
        )
    ]
    
    # Text with correct matching citations
    answer = (
        "According to [paper_one.pdf p.1], the baseline parameters are evaluated with 8000 tokens. "
        "Also, we utilize a hybrid retrieval framework [paper_two.pdf p.3]."
    )
    
    result = verify_citations(answer, evidence)
    assert len(result["verified"]) == 2
    assert len(result["unverified"]) == 0
    assert result["grounding_score"] == 1.0


def test_verify_citations_fail():
    evidence = [
        SourceEvidence(
            chunk_id="doc1:p1",
            source="paper_one.pdf",
            page=1,
            score=0.9,
            text="Simple text evidence."
        )
    ]
    
    # Citations that point to non-retrieved pages or wrong document names
    answer = (
        "This claim is unsupported [fake_paper.pdf p.1]. "
        "This claim has the wrong page [paper_one.pdf p.4]."
    )
    
    result = verify_citations(answer, evidence)
    assert len(result["verified"]) == 0
    assert len(result["unverified"]) == 2
    assert result["grounding_score"] == 0.0
    assert len(result["warnings"]) > 0
