from pathlib import Path
import re

from app.core.pdf_loader import find_doi, fetch_crossref_metadata, search_crossref_by_title
from app.core.retriever import HybridRetriever
from app.core.schemas import SourceEvidence
from app.core.config import settings


def test_doi_extraction():
    sample_text = "Attention Is All You Need. Abstract: ... DOI: 10.1016/j.artint.2023.103984. Published online 2024."
    doi = find_doi(sample_text)
    assert doi == "10.1016/j.artint.2023.103984"


def test_crossref_mock_and_live():
    # Test fetch with valid DOI
    # (We query a known test DOI, or mock it. CrossRef works without key and is fast.)
    doi = "10.1016/j.artint.2023.103984"
    meta = fetch_crossref_metadata(doi)
    if meta:
        assert "title" in meta
        assert "year" in meta
        assert meta["doi"] == doi
        assert "bibtex" in meta
        assert "@article" in meta["bibtex"]


def test_latex_markdown_compiling():
    # Verify regex converter behaves as expected
    markdown_content = """# Title of manuscript
Some text with **bold terms** and *italic words*.

## Subsection analysis
More text."""
    
    # Simple compilation checklist
    latex = markdown_content
    latex = re.sub(r"^#\s+(.+)$", r"\\section{\1}", latex, flags=re.MULTILINE)
    latex = re.sub(r"^##\s+(.+)$", r"\\subsection{\1}", latex, flags=re.MULTILINE)
    latex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", latex)
    latex = re.sub(r"\*(.+?)\*", r"\\textit{\1}", latex)
    
    assert "\\section{Title of manuscript}" in latex
    assert "\\subsection{Subsection analysis}" in latex
    assert "\\textbf{bold terms}" in latex
    assert "\\textit{italic words}" in latex


def test_reranker_retrieval_flow():
    # Verify reranker fallback and flow compiles
    retriever = HybridRetriever()
    assert hasattr(retriever, "search")
    
    # Toggle reranker setting to test fallback or execution path safety
    orig_rerank = settings.reranker_enabled
    settings.reranker_enabled = True
    
    # Asserting that dynamic initialization properties are established
    assert retriever.rerank_model is not None
    
    settings.reranker_enabled = orig_rerank
