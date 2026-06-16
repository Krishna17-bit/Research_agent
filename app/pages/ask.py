import streamlit as st
import pandas as pd
from pathlib import Path

from app.core.agent import ResearchAgent
from app.core import database
from app.core.config import settings

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>💬 Citation-Grounded Q&A Workspace</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Ask questions across one or many research documents. Answers are strictly grounded in retrieved evidence with citation verifications.
        </p>
    </div>
""", unsafe_allow_html=True)

# 1. Select Workspace / Documents
workspaces = database.get_workspaces()
active_ws_id = st.selectbox(
    "Ground Q&A in Workspace",
    options=[w["id"] for w in workspaces],
    format_func=lambda x: next(w["name"] for w in workspaces if w["id"] == x)
)

ws_docs = database.get_workspace_documents(active_ws_id)
if not ws_docs:
    st.warning("No documents in this workspace. Add documents on the Library page or upload new ones!")
else:
    doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in ws_docs}
    selected_docs = st.multiselect(
        "Restrict search to specific papers (or leave blank to search all workspace files)",
        options=list(doc_options.keys()),
        format_func=lambda x: doc_options[x]
    )

    doc_filter_ids = selected_docs if selected_docs else list(doc_options.keys())

    # 2. Advanced Parameters
    with st.expander("⚙️ Advanced Retrieval Parameters"):
        top_k = st.slider("Max Evidence Chunks (Top-K)", 3, 20, settings.top_k)
        sim_threshold = st.slider("Similarity Score Threshold", 0.0, 1.0, settings.similarity_threshold, step=0.05)
        settings.top_k = top_k
        settings.similarity_threshold = sim_threshold

    # 3. Question Form
    st.write("---")
    question = st.text_area("Your Research Question", height=100, placeholder="e.g. What datasets and metrics were used to evaluate baseline RAG models?")
    
    if st.button("Query Research Agent", type="primary") and question.strip():
        with st.spinner("Retrieving evidence, compiling index, and generating grounded answer..."):
            agent = ResearchAgent()
            result = agent.ask(question, top_k=top_k, doc_ids=doc_filter_ids)
            
            # Display result
            st.subheader("📝 Answer")
            st.markdown(result.answer)
            
            # Metadata row
            c1, c2, c3 = st.columns(3)
            confidence_colors = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}
            c1.metric("Grounding Confidence", confidence_colors.get(result.confidence, "Low"))
            c2.metric("Used Generative LLM", "Yes" if result.used_llm else "Offline Extractive Fallback")
            
            # Latency and token metrics from database (retrieve latest run)
            latest_runs = database.get_runs()
            if latest_runs:
                last_run = latest_runs[0]
                c3.metric("Cost / Tokens", f"${last_run['cost']:.4f} / {last_run['tokens']} tkn", help="Estimated provider cost.")
                
            # Warnings / Grounding checks
            if result.warnings:
                st.warning("⚠️ **Grounding Verification Warnings:**\n" + "\n".join(f"- {w}" for w in result.warnings))
            else:
                st.success("✅ **Citation Verification Pass:** All claims match retrieved evidence coordinates.")

            # Save as Note functionality
            st.write("---")
            st.write("### 📓 Research Annotations")
            save_col1, save_col2 = st.columns([2, 1])
            with save_col1:
                note_title = st.text_input("Note Title", value=f"Q&A Note: {question[:45]}...")
                note_tags = st.text_input("Tags (comma separated)", value="rag-qa, evidence")
            with save_col2:
                st.write("")
                st.write("")
                if st.button("Save Answer as Note", type="primary"):
                    database.add_note(
                        document_id=None,
                        workspace_id=active_ws_id,
                        page_number=None,
                        note_type="summary",
                        title=note_title,
                        content=result.answer,
                        tags=note_tags
                    )
                    st.success("Answer saved to Notes dashboard!")

            # Export Markdown
            md_content = f"""# Question: {question}
{result.answer}

## Evidence Citations
""" + "\n".join(f"- {ev.source} p.{ev.page} (similarity: {ev.score:.3f})" for ev in result.citations)
            
            st.download_button(
                "📥 Export Answer as Markdown", 
                md_content, 
                file_name=f"research_answer_{datetime.now().strftime('%d_%H%M%S') if 'datetime' in globals() else 'rag'}.md"
            )

            # 4. Display Retrieved Evidence
            st.write("### 📌 Supporting Evidence Chunks")
            for i, ev in enumerate(result.citations):
                ocr_flag = "📸 OCR/Image Text" if "[ocr/image text]" in ev.text.lower() else "📝 Selectable Text"
                with st.expander(f"[{i + 1}] {ev.source} — Page {ev.page} — Score: {ev.score:.3f} — {ocr_flag}"):
                    st.write(ev.text)
