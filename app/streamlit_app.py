from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from app.core.agent import ResearchAgent
from app.core.config import ENV_FILE, settings
from app.core.llm import active_provider
from app.core.retriever import HybridRetriever

st.set_page_config(page_title="Scientific PDF RAG Agent", page_icon="🔬", layout="wide")

st.title("Scientific PDF RAG + Research Agent")
st.caption("Gemini-powered, citation-grounded research assistant with optional OCR for scanned and figure-heavy PDFs.")

with st.sidebar:
    st.header("Index documents")
    st.caption(f"Provider: {active_provider()}")
    st.caption(f"Env file: {ENV_FILE}")
    st.caption(f"OCR mode: {settings.ocr_mode}")

    uploaded = st.file_uploader(
        "Upload PDF/TXT/MD files", type=["pdf", "txt", "md"], accept_multiple_files=True
    )
    if st.button("Build / Rebuild Index", type="primary"):
        if not uploaded:
            st.warning("Upload at least one document first.")
        else:
            paths = []
            for file in uploaded:
                out = settings.upload_dir / file.name
                with out.open("wb") as f:
                    f.write(file.read())
                paths.append(out)
            with st.spinner("Indexing documents with text + OCR-aware extraction and hybrid retrieval..."):
                count = HybridRetriever().build_from_paths(paths)
            st.success(f"Indexed {count} chunks from {len(paths)} file(s).")

    st.divider()
    st.subheader("Good research questions")
    st.code("Extract all reported results from figures and tables.")
    st.code("What are the limitations and missing experiments?")
    st.code("Create a reproducibility checklist for this paper.")
    st.code("Map each major claim to supporting evidence.")

retriever = HybridRetriever()
has_index = retriever.load()

if not has_index:
    st.info("No index found yet. Upload documents in the sidebar or run: python scripts/index_sample_docs.py")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Indexed chunks", len(retriever.chunks))
    c2.metric("Documents", len({c.source for c in retriever.chunks}))
    c3.metric("LLM provider", active_provider())
    ocr_chunks = sum(1 for c in retriever.chunks if "[ocr/image text]" in c.text.lower() or "ocr" in c.text.lower())
    c4.metric("OCR/image chunks", ocr_chunks)

agent = ResearchAgent(retriever)

mode = st.radio(
    "Mode",
    [
        "Ask a question",
        "Research summary",
        "Methodology",
        "Results / Figures / Tables",
        "Compare methods",
        "Contributions",
        "Limitations",
        "Research gaps",
        "Reproducibility checklist",
        "Claim/evidence checker",
        "Evidence map",
    ],
    horizontal=False,
)


def render_result(result):
    st.subheader("Answer")
    st.markdown(result.answer)
    c1, c2 = st.columns(2)
    c1.metric("Confidence", result.confidence)
    c2.metric("Used Gemini", "Yes" if result.used_llm else "No")
    if result.warnings:
        st.warning("\n".join(result.warnings))

    md = result.answer + "\n\n## Evidence\n" + "\n".join(
        f"- {ev.source} p.{ev.page}, score {ev.score:.3f}" for ev in result.citations
    )
    st.download_button("Download answer as Markdown", md, file_name="rag_research_answer.md")

    st.subheader("Evidence")
    for ev in result.citations:
        label = "OCR/image" if "[ocr/image text]" in ev.text.lower() else "text"
        with st.expander(f"{ev.source} — page {ev.page} — score {ev.score:.3f} — {label}"):
            st.write(ev.text)


def render_evidence_map():
    if not retriever.chunks:
        st.warning("No chunks loaded.")
        return
    rows = []
    for c in retriever.chunks:
        text_lower = c.text.lower()
        rows.append(
            {
                "source": c.source,
                "page": c.page,
                "chunk_id": c.chunk_id,
                "chars": len(c.text),
                "type": "ocr/image" if "[ocr/image text]" in text_lower else "text/caption",
                "preview": c.text[:220].replace("\n", " "),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download evidence map CSV", df.to_csv(index=False), "evidence_map.csv")


if mode == "Ask a question":
    question = st.text_area("Question", height=100, placeholder="Ask a technical question about the indexed documents...")
    top_k = st.slider("Retrieved evidence chunks", 3, 20, settings.top_k)
    if st.button("Ask Research Agent", type="primary") and question.strip():
        with st.spinner("Retrieving evidence and generating answer..."):
            render_result(agent.ask(question, top_k=top_k))

elif mode == "Research summary":
    if st.button("Generate research brief", type="primary"):
        with st.spinner("Creating research brief..."):
            render_result(agent.summarize())

elif mode == "Methodology":
    if st.button("Extract methodology", type="primary"):
        with st.spinner("Extracting methodology..."):
            render_result(agent.extract_methodology())

elif mode == "Results / Figures / Tables":
    if st.button("Extract results", type="primary"):
        with st.spinner("Extracting results, figure text, tables, and captions..."):
            render_result(agent.extract_results())

elif mode == "Compare methods":
    if st.button("Compare methods", type="primary"):
        with st.spinner("Comparing methods from retrieved evidence..."):
            render_result(agent.compare_methods())

elif mode == "Contributions":
    if st.button("Extract contributions", type="primary"):
        with st.spinner("Extracting contributions..."):
            render_result(agent.extract_contributions())

elif mode == "Limitations":
    if st.button("Find limitations", type="primary"):
        with st.spinner("Finding limitations and future work..."):
            render_result(agent.find_limitations())

elif mode == "Research gaps":
    if st.button("Find research gaps", type="primary"):
        with st.spinner("Finding research gaps and next experiments..."):
            render_result(agent.research_gap_analysis())

elif mode == "Reproducibility checklist":
    if st.button("Create checklist", type="primary"):
        with st.spinner("Creating reproducibility checklist..."):
            render_result(agent.reproducibility_checklist())

elif mode == "Claim/evidence checker":
    if st.button("Check claims", type="primary"):
        with st.spinner("Mapping claims to evidence..."):
            render_result(agent.claim_checker())

else:
    render_evidence_map()
