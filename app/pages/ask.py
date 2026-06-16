import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from app.core.agent import ResearchAgent
from app.core import database
from app.core.config import settings

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>💬 Citation-Grounded Q&A Workspace</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Ask questions across workspace papers. Inspect verified page evidence visually side-by-side.
        </p>
    </div>
""", unsafe_allow_html=True)

# Initialize session state for query results
if "rag_result" not in st.session_state:
    st.session_state.rag_result = None
if "active_question" not in st.session_state:
    st.session_state.active_question = ""

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
        rc1, rc2 = st.columns(2)
        with rc1:
            top_k = st.slider("Max Evidence Chunks (Top-K)", 3, 20, settings.top_k)
            sim_threshold = st.slider("Similarity Score Threshold", 0.0, 1.0, settings.similarity_threshold, step=0.05)
        with rc2:
            reranker_enabled = st.checkbox("Enable Cross-Encoder Reranking", value=settings.reranker_enabled, help="Use a cross-encoder model to re-sort results for extreme precision.")
            hyde_enabled = st.checkbox("Enable HyDE (Hypothetical Document Embeddings)", value=settings.hyde_enabled, help="Generates a hypothetical passage to align vector embedding searches.")

        # Apply settings
        settings.top_k = top_k
        settings.similarity_threshold = sim_threshold
        settings.reranker_enabled = reranker_enabled
        settings.hyde_enabled = hyde_enabled

    # 3. Question Form
    st.write("---")
    question_input = st.text_area("Your Research Question", height=100, placeholder="e.g. What datasets and metrics were used to evaluate baseline RAG models?")
    
    if st.button("Query Research Agent", type="primary") and question_input.strip():
        st.session_state.active_question = question_input.strip()
        with st.spinner("Retrieving evidence, compiling index, and generating grounded answer..."):
            agent = ResearchAgent()
            result = agent.ask(question_input, top_k=top_k, doc_ids=doc_filter_ids)
            st.session_state.rag_result = result

    # 4. Display Results in Split-Screen columns
    if st.session_state.rag_result:
        res = st.session_state.rag_result
        
        col_left, col_right = st.columns([3, 2])
        
        with col_left:
            st.subheader("📝 Answer")
            st.markdown(res.answer)
            
            # Metadata row
            c1, c2, c3 = st.columns(3)
            confidence_colors = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}
            c1.metric("Grounding Confidence", confidence_colors.get(res.confidence, "Low"))
            c2.metric("Used Generative LLM", "Yes" if res.used_llm else "Offline Extractive Fallback")
            
            # Latency and token metrics from database
            latest_runs = database.get_runs()
            if latest_runs:
                last_run = latest_runs[0]
                c3.metric("Cost / Tokens", f"${last_run['cost']:.4f} / {last_run['tokens']} tkn")
                
            # Warnings
            if res.warnings:
                st.warning("⚠️ **Grounding Verification Warnings:**\n" + "\n".join(f"- {w}" for w in res.warnings))
            else:
                st.success("✅ **Citation Verification Pass:** All claims match retrieved evidence coordinates.")

            # Save as Note
            st.write("---")
            st.write("### 📓 Research Annotations")
            save_col1, save_col2 = st.columns([2, 1])
            with save_col1:
                note_title = st.text_input("Note Title", value=f"Q&A Note: {st.session_state.active_question[:45]}...")
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
                        content=res.answer,
                        tags=note_tags
                    )
                    st.success("Answer saved to Notes dashboard!")

            # Export Markdown
            md_content = f"# Question: {st.session_state.active_question}\n{res.answer}\n\n## Evidence Citations\n" + "\n".join(f"- {ev.source} p.{ev.page} (similarity: {ev.score:.3f})" for ev in res.citations)
            st.download_button("📥 Export Answer as Markdown", md_content, file_name=f"research_answer.md")

            # Display passages
            st.write("### 📌 Supporting Evidence Chunks")
            for i, ev in enumerate(res.citations):
                ocr_flag = "📸 OCR/Image Text" if "[ocr/image text]" in ev.text.lower() else "📝 Selectable Text"
                with st.expander(f"[{i + 1}] {ev.source} — Page {ev.page} — Score: {ev.score:.3f} — {ocr_flag}"):
                    st.write(ev.text)
                    
        with col_right:
            st.subheader("🖼️ Visual Citation Panel")
            st.write("Select a citation passage below to view the original PDF page context side-by-side:")
            
            # Map citations for selector
            cite_choices = []
            for i, ev in enumerate(res.citations):
                # find doc id by source name matching database
                doc_record = next((d for d in ws_docs if d["file_name"] == ev.source), None)
                doc_id = doc_record["id"] if doc_record else None
                cite_choices.append({
                    "label": f"[{i + 1}] {ev.source} (Page {ev.page})",
                    "doc_id": doc_id,
                    "page": ev.page,
                    "source": ev.source
                })
                
            if not cite_choices:
                st.info("No citations available to render.")
            else:
                selected_cite = st.selectbox(
                    "Select page context to render:",
                    options=range(len(cite_choices)),
                    format_func=lambda x: cite_choices[x]["label"]
                )
                
                choice = cite_choices[selected_cite]
                if not choice["doc_id"]:
                    st.warning("Could not identify catalog reference for this file.")
                else:
                    # Look up rendered page PNG image path
                    image_path = settings.page_image_dir / choice["doc_id"] / f"page_{choice['page']:04d}.png"
                    if image_path.exists():
                        st.image(str(image_path), caption=f"PDF Visual Context: {choice['source']} p.{choice['page']}", use_container_width=True)
                    else:
                        st.info("Visual page PNG not cached. Ensure settings.save_page_images = True is configured in Settings.")
