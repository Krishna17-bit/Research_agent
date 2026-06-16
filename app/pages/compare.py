import streamlit as st
from datetime import datetime

from app.core.agent import ResearchAgent
from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>⚖️ Multi-Paper Comparative Workspace</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Compare methodologies, datasets, algorithms, performance metrics, limitations, and assumptions across selected publications.
        </p>
    </div>
""", unsafe_allow_html=True)

docs = database.get_all_documents()
doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in docs if d["status"] == "indexed"}

if len(doc_options) < 1:
    st.warning("Upload and index at least one paper first to compare!")
else:
    selected_ids = st.multiselect(
        "Select papers to compare (prefer 2 or more)",
        options=list(doc_options.keys()),
        default=list(doc_options.keys())[:2],
        format_func=lambda x: doc_options[x]
    )
    
    if st.button("Generate Comparative Matrix", type="primary") and selected_ids:
        with st.spinner("Analyzing papers and compiling comparison matrices..."):
            agent = ResearchAgent()
            result = agent.compare_methods(doc_ids=selected_ids)
            
        st.subheader("💡 Methodology Comparison Matrix")
        st.markdown(result.answer)
        
        # Meta
        st.write("---")
        st.metric("Grounding Confidence", result.confidence.upper())
        if result.warnings:
            st.warning("\n".join(result.warnings))
            
        # Export
        st.write("### 📥 Save & Export Matrix")
        note_title = st.text_input("Comparison Note Title", value="Comparative Analysis Matrix")
        if st.button("Save Comparative Note", type="primary"):
            database.add_note(
                document_id=None,
                workspace_id=None,
                page_number=None,
                note_type="comparison",
                title=note_title,
                content=result.answer,
                tags="comparison, matrix, literature-review"
            )
            st.success("Note saved successfully!")
            
        st.download_button("Download Matrix MD", result.answer, file_name="comparison_matrix.md")
        
        st.write("#### Cited passages:")
        for i, ev in enumerate(result.citations):
            with st.expander(f"Reference [{i + 1}] — {ev.source} p.{ev.page}"):
                st.write(ev.text)
