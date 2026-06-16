import streamlit as st

from app.core.agent import ResearchAgent
from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>📝 Structured Paper Summaries</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Extract contributions, baseline evaluations, limitations, or general briefs from individual or grouped papers.
        </p>
    </div>
""", unsafe_allow_html=True)

docs = database.get_all_documents()
doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in docs if d["status"] == "indexed"}

if not doc_options:
    st.warning("No indexed papers found. Upload papers first!")
else:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_id = st.selectbox("Select document to analyze", options=list(doc_options.keys()), format_func=lambda x: doc_options[x])
        
        summary_type = st.radio(
            "Summary Strategy",
            options=[
                "Global Research Brief",
                "Key Scientific Contributions",
                "Stated Limitations & Future Work",
                "Reproducibility Checklist",
                "Claim & Evidence Map"
            ]
        )
        
        submit_btn = st.button("Generate Analysis", type="primary")

    with col2:
        st.subheader("📊 Structured Output")
        
        if submit_btn:
            agent = ResearchAgent()
            doc_filter = [selected_id]
            
            with st.spinner("Extracting contents and generating grounded brief..."):
                if summary_type == "Global Research Brief":
                    result = agent.summarize(doc_ids=doc_filter)
                elif summary_type == "Key Scientific Contributions":
                    result = agent.extract_contributions(doc_ids=doc_filter)
                elif summary_type == "Stated Limitations & Future Work":
                    result = agent.find_limitations(doc_ids=doc_filter)
                elif summary_type == "Reproducibility Checklist":
                    result = agent.reproducibility_checklist(doc_ids=doc_filter)
                else:
                    result = agent.claim_checker(doc_ids=doc_filter)

            # Display
            st.markdown(result.answer)
            st.write("---")
            
            # Metadata & Warnings
            c1, c2 = st.columns(2)
            c1.metric("Confidence Level", result.confidence.upper())
            if result.warnings:
                st.warning("\n".join(result.warnings))
            else:
                st.success("Citation validation: Pass")
                
            # Actions
            st.write("### ⚙️ Save & Export")
            note_title = st.text_input("Note Title", value=f"{summary_type}: {doc_options[selected_id][:30]}")
            if st.button("Save as Research Note", type="primary"):
                database.add_note(
                    document_id=selected_id,
                    workspace_id=None,
                    page_number=None,
                    note_type="summary",
                    title=note_title,
                    content=result.answer,
                    tags=f"summary, {summary_type.lower().replace(' ', '_')}"
                )
                st.success("Note saved successfully!")
                
            st.download_button(
                "Download as Markdown", 
                result.answer + "\n\n## References\n" + "\n".join(f"- {ev.source} p.{ev.page}" for ev in result.citations),
                file_name="paper_summary.md"
            )
            
            st.write("#### Supporting passages used:")
            for i, ev in enumerate(result.citations):
                with st.expander(f"Evidence [{i + 1}] — {ev.source} p.{ev.page}"):
                    st.write(ev.text)
