import streamlit as st

from app.core.agent import ResearchAgent
from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>📖 Literature Review & Research Planner</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Compile annotated outlines, organize findings by thematic concepts, compare contradictions, and draft academic reviews.
        </p>
    </div>
""", unsafe_allow_html=True)

docs = database.get_all_documents()
doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in docs if d["status"] == "indexed"}

if len(doc_options) < 1:
    st.warning("Upload and index publications first to compile literature reviews!")
else:
    selected_ids = st.multiselect(
        "Select papers to synthesize",
        options=list(doc_options.keys()),
        default=list(doc_options.keys())[:3],
        format_func=lambda x: doc_options[x]
    )
    
    review_topic = st.text_input("Review Topic / Subject Theme", placeholder="e.g. Robustness challenges in retrieval augmented text models")
    
    if st.button("Synthesize Literature Review", type="primary") and selected_ids and review_topic.strip():
        with st.spinner("Synthesizing context and drafting thematic outline..."):
            agent = ResearchAgent()
            prompt = f"""Write a comprehensive academic literature review on the topic: '{review_topic}'.
Include the following structured sections:
1. **Background**: Synthesize general definitions and baseline setups.
2. **Thematic Comparison**: Compare how the selected documents treat key concepts.
3. **Contradictions & Open Questions**: Highlight contradictions, disagreements, or differing results between papers.
4. **Key Gaps & Future Directions**: Stated limits and next steps.
5. **Annotated Bibliography**: A short summary of each paper with its key contribution and cited evidence.
"""
            result = agent.ask(prompt, top_k=15, doc_ids=selected_ids)
            
        st.subheader("💡 Synthesized Literature Review")
        st.markdown(result.answer)
        
        # Meta
        st.write("---")
        st.metric("Confidence Level", result.confidence.upper())
        if result.warnings:
            st.warning("\n".join(result.warnings))
            
        # Export
        st.write("### 📥 Save & Export Review")
        note_title = st.text_input("Literature Review Title", value=f"Lit Review: {review_topic[:35]}")
        if st.button("Save as Note", type="primary"):
            database.add_note(
                document_id=None,
                workspace_id=None,
                page_number=None,
                note_type="summary",
                title=note_title,
                content=result.answer,
                tags="literature-review, synthesis, outline"
            )
            st.success("Note saved successfully!")
            
        st.download_button("Download Review MD", result.answer, file_name="literature_review.md")
        
        st.write("#### Referenced passages:")
        for i, ev in enumerate(result.citations):
            with st.expander(f"Evidence [{i + 1}] — {ev.source} p.{ev.page}"):
                st.write(ev.text)
