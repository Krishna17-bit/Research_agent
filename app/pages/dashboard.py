import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from app.core import database
from app.core.config import settings
from app.core.llm import active_provider

st.set_page_config(layout="wide")

# Custom header styling
st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>🔬 Research Intelligence Dashboard</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Citation-grounded analysis catalog, personal workspace libraries, and retrieval validation.
        </p>
    </div>
""", unsafe_allow_html=True)

# Fetch stats from SQLite
docs = database.get_all_documents()
total_docs = len(docs)
failed_docs = sum(1 for d in docs if d["status"] == "failed")
indexed_pages = sum(d["page_count"] for d in docs if d["status"] == "indexed")
total_chunks = sum(d["chunk_count"] for d in docs if d["status"] == "indexed")

runs = database.get_runs()
total_runs = len(runs)
avg_latency = pd.DataFrame(runs)["latency"].mean() if runs else 0.0

# Count workspace stats
workspaces = database.get_workspaces()
active_ws_id = st.sidebar.selectbox(
    "Active Workspace",
    options=[w["id"] for w in workspaces],
    format_func=lambda x: next(w["name"] for w in workspaces if w["id"] == x)
)
st.sidebar.caption("Change active workspace filter to view specific stats.")

ws_docs = database.get_workspace_documents(active_ws_id)
ws_doc_count = len(ws_docs)

# Metrics Grid
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Indexed Documents", f"{total_docs} total", help="All PDFs uploaded and cataloged.")
c2.metric("Total Pages", f"{indexed_pages} pgs", help="Cumulative pages parsed.")
c3.metric("Vector Chunks", f"{total_chunks} chunks", help="Chunks stored in the dynamic index.")
c4.metric("Workspace Papers", f"{ws_doc_count} active", help="Documents in the selected workspace.")
c5.metric("Avg Latency", f"{avg_latency:.2f}s", help="Average generation time.")

st.write("---")

# Row 2: Double Column Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📝 Recent Questions & Answers")
    if not runs:
        st.info("No questions logged in this run history yet. Start asking questions in the Q&A tab!")
    else:
        # Convert runs to DataFrame for display
        df_runs = pd.DataFrame([
            {
                "Timestamp": datetime.fromisoformat(r["timestamp"]).strftime("%Y-%m-%d %H:%M"),
                "Question": r["question"],
                "Answer Preview": r["answer"][:120] + "...",
                "Confidence": r["confidence"].upper(),
                "Provider": r["provider"],
                "Verification": r["citation_quality"]
            }
            for r in runs[:6]
        ])
        st.dataframe(df_runs, use_container_width=True, hide_index=True)

with col2:
    st.subheader("⚙️ System Status")
    
    # Provider Badge
    provider_str = active_provider()
    st.info(f"**LLM Service**: {provider_str}")
    
    # Config status table
    cfg_data = {
        "Parameter": ["Mock Mode", "Embedding Model", "OCR Mode", "Similarity Limit", "Vector Store"],
        "Value": [
            "🟢 ON" if settings.mock_mode else "🔴 OFF (Real API)",
            settings.embedding_model.split("/")[-1],
            settings.ocr_mode.upper(),
            f"{settings.similarity_threshold:.2f}",
            settings.vector_store.upper()
        ]
    }
    st.table(pd.DataFrame(cfg_data))

# Extra Row: Storage Status
st.subheader("📂 Index & Files Information")
sc1, sc2, sc3 = st.columns(3)

# Size of SQL DB
db_path = settings.resolve_path(Path("app/storage/research_agent.db"))
db_size = db_path.stat().st_size / 1024 if db_path.exists() else 0.0
sc1.metric("Metadata Database", f"{db_size:.1f} KB", "SQLite File")

# Size of uploads
uploads_dir = settings.upload_dir
uploads_size = sum(f.stat().st_size for f in uploads_dir.glob("*") if f.is_file()) / (1024 * 1024) if uploads_dir.exists() else 0.0
sc2.metric("Source File Store", f"{uploads_size:.2f} MB", f"{len(list(uploads_dir.glob('*')))} files")

# Size of Page image cache
img_dir = settings.page_image_dir
img_count = sum(1 for _ in img_dir.glob("**/*.png")) if img_dir.exists() else 0
sc3.metric("OCR Page Cache", f"{img_count} images", "Saved Pixmaps")
