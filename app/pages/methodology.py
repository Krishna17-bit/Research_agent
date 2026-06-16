import streamlit as st

from app.core.agent import ResearchAgent
from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>🧪 Methodology Extractor & Reproducibility Labs</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Extract technical workflows, processing steps, algorithms, hyperparameter configurations, and reproducibility blockers.
        </p>
    </div>
""", unsafe_allow_html=True)

docs = database.get_all_documents()
doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in docs if d["status"] == "indexed"}

if not doc_options:
    st.warning("Upload and index research papers first!")
else:
    selected_id = st.selectbox("Select document to analyze", options=list(doc_options.keys()), format_func=lambda x: doc_options[x])
    
    tab1, tab2 = st.tabs(["🧪 Methodology Extraction", "📋 Reproducibility Checklist"])
    
    agent = ResearchAgent()
    doc_filter = [selected_id]
    
    with tab1:
        st.write("Extract the model architectures, baseline comparators, preprocess parameters, and analysis workflows.")
        if st.button("Extract Pipeline Methodology", type="primary"):
            with st.spinner("Compiling methodology pipeline..."):
                res_method = agent.extract_methodology(doc_ids=doc_filter)
            st.markdown(res_method.answer)
            st.write("---")
            st.metric("Confidence", res_method.confidence.upper())
            
            note_t = st.text_input("Note Title (Methodology)", value=f"Methodology: {doc_options[selected_id][:30]}")
            if st.button("Save Methodology Note", type="primary"):
                database.add_note(selected_id, None, None, "method", note_t, res_method.answer, "methodology, pipeline")
                st.success("Saved Note!")
            st.download_button("Download Methodology MD", res_method.answer, file_name="methodology.md")
            
    with tab2:
        st.write("Construct a checklist covering source code, dataset availability, hyperparameters, and random seeds.")
        if st.button("Generate Reproducibility Checklist", type="primary"):
            with st.spinner("Checking parameters and source requirements..."):
                res_check = agent.reproducibility_checklist(doc_ids=doc_filter)
            st.markdown(res_check.answer)
            st.write("---")
            st.metric("Confidence", res_check.confidence.upper())
            
            note_c = st.text_input("Note Title (Checklist)", value=f"Checklist: {doc_options[selected_id][:30]}")
            if st.button("Save Checklist Note", type="primary"):
                database.add_note(selected_id, None, None, "method", note_c, res_check.answer, "reproducibility, checklist")
                st.success("Saved Note!")
            st.download_button("Download Checklist MD", res_check.answer, file_name="reproducibility_checklist.md")
