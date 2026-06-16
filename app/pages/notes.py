import streamlit as st
import pandas as pd
from datetime import datetime

from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>📓 Personal Research Notes & Annotations</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Review saved Q&A outputs, methodology outlines, comparisons, and custom annotations. Export findings to Markdown or JSON.
        </p>
    </div>
""", unsafe_allow_html=True)

# Fetch notes
notes = database.get_notes()
workspaces = database.get_workspaces()
docs = database.get_all_documents()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("✍️ Add Manual Note")
    note_title = st.text_input("Title", placeholder="e.g. My research direction")
    note_type = st.selectbox("Category", ["user note", "summary", "quote", "method", "result", "limitation", "research gap"])
    
    ws_options = {w["id"]: w["name"] for w in workspaces}
    selected_ws = st.selectbox("Assign to Workspace", options=["None"] + list(ws_options.keys()), format_func=lambda x: "None" if x == "None" else ws_options[x])
    
    doc_options = {d["id"]: d["title"] or d["file_name"] for d in docs}
    selected_doc = st.selectbox("Associate with Document", options=["None"] + list(doc_options.keys()), format_func=lambda x: "None" if x == "None" else doc_options[x])
    
    note_page = st.number_input("Page Number (optional)", min_value=0, value=0)
    note_tags = st.text_input("Tags (comma-separated)", placeholder="my-ideas, draft")
    note_content = st.text_area("Note Content (Markdown supported)", height=150)
    
    if st.button("Add Note", type="primary") and note_content.strip():
        ws_id = None if selected_ws == "None" else selected_ws
        doc_id = None if selected_doc == "None" else selected_doc
        p_num = None if note_page == 0 else int(note_page)
        
        database.add_note(
            document_id=doc_id,
            workspace_id=ws_id,
            page_number=p_num,
            note_type=note_type,
            title=note_title.strip() or "Untitled Note",
            content=note_content,
            tags=note_tags
        )
        st.success("Note added successfully!")
        st.rerun()

with col2:
    st.subheader("📓 Saved Notes Library")
    
    if not notes:
        st.info("No research notes found. Use the manual form or save answers from RAG tools!")
    else:
        # Search & filters
        n_search = st.text_input("Search Notes content / title", "")
        n_category = st.selectbox("Filter Category", ["All"] + list(set(n["note_type"] for n in notes)))
        
        filtered = []
        for n in notes:
            if n_search.lower() and n_search.lower() not in n["title"].lower() and n_search.lower() not in n["content"].lower():
                continue
            if n_category != "All" and n["note_type"] != n_category:
                continue
            filtered.append(n)
            
        st.write(f"Showing **{len(filtered)}** notes:")
        
        for n in filtered:
            doc_name = next((d["title"] or d["file_name"] for d in docs if d["id"] == n["document_id"]), None) if n["document_id"] else None
            page_suffix = f" p.{n['page_number']}" if n["page_number"] else ""
            doc_info = f" 📄 {doc_name}{page_suffix}" if doc_name else ""
            
            with st.expander(f"📌 {n['title']} [{n['note_type'].upper()}]{doc_info}"):
                st.markdown(n["content"])
                st.caption(f"Created: {datetime.fromisoformat(n['created_at']).strftime('%Y-%m-%d %H:%M')} | Tags: {n['tags']}")
                
                # Delete note
                if st.button(f"🗑️ Delete Note {n['id']}", key=f"del_{n['id']}", type="secondary"):
                    database.delete_note(n["id"])
                    st.error("Note deleted.")
                    st.rerun()
                    
        st.write("---")
        # Export notes
        st.subheader("📥 Export Notes")
        notes_md = "\n\n".join(f"# {n['title']} ({n['note_type']})\n{n['content']}" for n in filtered)
        st.download_button("Export as Markdown", notes_md, file_name="my_research_notes.md")
        
        df_notes = pd.DataFrame([dict(n) for n in filtered])
        st.download_button("Export as CSV", df_notes.to_csv(index=False), file_name="my_research_notes.csv")
