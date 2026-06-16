import streamlit as st
import pandas as pd
from pathlib import Path

from app.core import database
from app.core.config import settings

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>📚 PDF Document Library</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Manage research papers, catalog metadata, assign tags, and group files into custom workspaces.
        </p>
    </div>
""", unsafe_allow_html=True)

# Fetch documents
docs = database.get_all_documents()
workspaces = database.get_workspaces()

# --- Workspace Management ---
with st.expander("🛠️ Workspace Manager (Create / Delete Workspaces)"):
    wc1, wc2 = st.columns([2, 1])
    with wc1:
        new_ws_name = st.text_input("New Workspace Name", placeholder="e.g. Thesis Chapter 1")
        new_ws_desc = st.text_area("Description", placeholder="Gather literature about my methodology...", height=70)
        if st.button("Create Workspace", type="primary") and new_ws_name.strip():
            ws_id = database.create_workspace(new_ws_name.strip(), new_ws_desc.strip())
            st.success(f"Workspace '{new_ws_name}' created successfully (ID: {ws_id})!")
            st.rerun()
    with wc2:
        ws_to_delete = st.selectbox(
            "Delete Workspace",
            options=[w["id"] for w in workspaces if w["id"] != "default"],
            format_func=lambda x: next(w["name"] for w in workspaces if w["id"] == x),
            help="Note: Deleting a workspace will NOT delete the actual documents."
        )
        if st.button("Delete Workspace", type="secondary") and ws_to_delete:
            database.delete_workspace(ws_to_delete)
            st.warning("Workspace deleted.")
            st.rerun()

st.write("---")

# Active Workspace selection
ws_list = database.get_workspaces()
active_ws_id = st.selectbox(
    "Active Workspace View / Filter",
    options=[w["id"] for w in ws_list],
    format_func=lambda x: next(w["name"] for w in ws_list if w["id"] == x)
)

# Fetch workspace specific docs
ws_docs = database.get_workspace_documents(active_ws_id)
ws_doc_ids = {d["id"] for d in ws_docs}

if not docs:
    st.info("Your library is empty. Go to the Upload Center to import papers, technical manuals, or reports!")
else:
    # Sidebar filters
    with st.sidebar:
        st.header("Search & Filter")
        search_q = st.text_input("Search Title / Authors", "")
        doc_type_filter = st.selectbox("Document Type", ["All", "paper", "thesis", "manual", "report", "whitepaper", "patent"])
        
        # Tags extract
        all_tags = set()
        for d in docs:
            if d["tags"]:
                for t in d["tags"].split(","):
                    all_tags.add(t.strip())
        tag_filter = st.selectbox("Filter by Tag", ["All"] + sorted(list(all_tags)))

    # Filtered documents list
    filtered_docs = []
    for d in docs:
        # Search match
        title = d["title"] or ""
        authors = d["authors"] or ""
        fname = d["file_name"] or ""
        q = search_q.lower()
        if q and q not in title.lower() and q not in authors.lower() and q not in fname.lower():
            continue
        
        # Doc type match
        if doc_type_filter != "All" and d["doc_type"] != doc_type_filter:
            continue
            
        # Tag match
        if tag_filter != "All":
            doc_tags = [t.strip() for t in (d["tags"] or "").split(",")]
            if tag_filter not in doc_tags:
                continue
                
        filtered_docs.append(d)

    # Document details table
    st.subheader(f"Papers ({len(filtered_docs)} displayed)")
    
    rows = []
    for d in filtered_docs:
        in_ws = "✅ Yes" if d["id"] in ws_doc_ids else "❌ No"
        rows.append({
            "ID": d["id"],
            "File Name": d["file_name"],
            "Title": d["title"] or d["file_name"],
            "Authors": d["authors"] or "Unknown",
            "Year": d["year"] or "N/A",
            "Pages": d["page_count"],
            "Type": d["doc_type"].upper(),
            "Tags": d["tags"] or "",
            "In Workspace": in_ws
        })
        
    df = pd.DataFrame(rows)
    if not rows:
        st.info("No documents match your filter settings.")
    else:
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

        st.write("### ⚙️ Document Actions")
        selected_id = st.selectbox("Select document to edit or manage:", options=[r["id"] for r in rows], format_func=lambda x: next(r["Title"] for r in rows if r["ID"] == x))
        
        doc_to_manage = database.get_document(selected_id)
        if doc_to_manage:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📝 Edit Metadata**")
                edit_title = st.text_input("Title", value=doc_to_manage["title"] or "")
                edit_authors = st.text_input("Authors", value=doc_to_manage["authors"] or "")
                edit_year = st.text_input("Year", value=doc_to_manage["year"] or "")
                edit_type = st.selectbox(
                    "Document Type", 
                    options=["paper", "thesis", "manual", "report", "whitepaper", "patent"],
                    index=["paper", "thesis", "manual", "report", "whitepaper", "patent"].index(doc_to_manage["doc_type"] or "paper")
                )
                edit_tags = st.text_input("Tags (comma separated)", value=doc_to_manage["tags"] or "")
                edit_notes = st.text_area("Research Notes / Remarks", value=doc_to_manage["notes"] or "")
                
                if st.button("Save Changes", type="primary"):
                    database.update_document_metadata(
                        doc_id=selected_id,
                        title=edit_title,
                        authors=edit_authors,
                        year=edit_year,
                        doc_type=edit_type,
                        tags=edit_tags,
                        notes=edit_notes
                    )
                    st.success("Metadata updated successfully!")
                    st.rerun()
                    
            with col2:
                st.write("**🗂️ Workspace & File Actions**")
                
                # Add/remove from active workspace
                is_currently_in_ws = doc_to_manage["id"] in ws_doc_ids
                if is_currently_in_ws:
                    if st.button("Remove from Active Workspace", type="secondary"):
                        database.remove_document_from_workspace(active_ws_id, selected_id)
                        st.warning("Removed from workspace.")
                        st.rerun()
                else:
                    if st.button("Add to Active Workspace", type="primary"):
                        database.add_document_to_workspace(active_ws_id, selected_id)
                        st.success("Added to workspace!")
                        st.rerun()
                        
                st.write("---")
                # Reprocess
                if st.button("Reprocess Document Chunks", help="Recompile PyMuPDF text & run OCR again"):
                    with st.spinner("Extracting text and generating embeddings..."):
                        from app.core.retriever import HybridRetriever
                        HybridRetriever().build_from_paths([Path(doc_to_manage["file_path"])])
                    st.success("Reprocessed and re-indexed successfully.")
                    st.rerun()
                
                # Delete document
                if st.button("⚠️ Delete Document permanently", type="secondary"):
                    # Delete files
                    f_path = Path(doc_to_manage["file_path"])
                    if f_path.exists():
                        f_path.unlink()
                    
                    # Delete numpy embeddings & chunks cache
                    emb_f = settings.index_dir.parent / "embeddings" / f"{selected_id}.npy"
                    chunk_f = settings.index_dir.parent / "chunks" / f"{selected_id}.json"
                    if emb_f.exists():
                        emb_f.unlink()
                    if chunk_f.exists():
                        chunk_f.unlink()
                    
                    # Delete from DB
                    database.delete_document(selected_id)
                    
                    # Rebuild active retriever index
                    from app.core.retriever import HybridRetriever
                    HybridRetriever().load()
                    
                    st.error("Document deleted from storage and catalog index.")
                    st.rerun()
