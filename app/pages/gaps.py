import streamlit as st
from datetime import datetime

from app.core.agent import ResearchAgent
from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>🔍 Stated Limitations & Research Gap Finder</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Identify simplified assumptions, evaluation boundaries, unresolved issues, and proposed future experiments.
        </p>
    </div>
""", unsafe_allow_html=True)

docs = database.get_all_documents()
doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in docs if d["status"] == "indexed"}

if not doc_options:
    st.warning("Upload and index research documents first!")
else:
    selected_ids = st.multiselect(
        "Select papers to analyze",
        options=list(doc_options.keys()),
        default=list(doc_options.keys())[:2],
        format_func=lambda x: doc_options[x]
    )
    
    if st.button("Analyze Research Gaps", type="primary") and selected_ids:
        with st.spinner("Extracting limits and future work vectors..."):
            agent = ResearchAgent()
            result = agent.research_gap_analysis(doc_ids=selected_ids)
            
        st.subheader("💡 Identified Research Gaps & Open Questions")
        st.markdown(result.answer)
        
        # Meta
        st.write("---")
        st.metric("Confidence Level", result.confidence.upper())
        if result.warnings:
            st.warning("\n".join(result.warnings))
            
        # Actions
        st.write("### ⚙️ Save & Export")
        note_title = st.text_input("Note Title", value="Stated Limitations & Research Gaps")
        if st.button("Save as Research Note", type="primary"):
            database.add_note(
                document_id=None,
                workspace_id=None,
                page_number=None,
                note_type="research gap",
                title=note_title,
                content=result.answer,
                tags="limitations, research-gaps, future-work"
            )
            st.success("Note saved successfully!")
            
        st.download_button("Download Gaps Report MD", result.answer, file_name="research_gaps.md")
        
        st.write("#### Supporting passages used:")
        for i, ev in enumerate(result.citations):
            with st.expander(f"Evidence [{i + 1}] — {ev.source} p.{ev.page}"):
                st.write(ev.text)
