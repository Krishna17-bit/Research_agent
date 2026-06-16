import streamlit as st
from pathlib import Path

from app.core.config import settings
from app.core.retriever import HybridRetriever
from app.core.pdf_loader import download_paper_from_url

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>📤 Document Upload & Ingestion Pipeline</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Upload PDFs, text, or markdown. Import directly from arXiv or web URLs to trigger dynamic indexing and CrossRef metadata lookups.
        </p>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 Source Documents")
    st.info("Maximum file size: 20MB. Supported types: PDF, TXT, MD.")
    
    uploaded_files = st.file_uploader(
        "Select research papers or manuals",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True
    )
    
    import_url = st.text_input("🔗 Or Import from arXiv / PDF URL", placeholder="e.g. https://arxiv.org/abs/1706.03762")
    
    rebuild_btn = st.button("🚀 Ingest & Index Documents", type="primary")

with col2:
    st.subheader("⚙️ Processing Settings")
    ocr_mode = st.selectbox(
        "OCR Extraction Mode",
        options=["auto", "force", "off"],
        index=["auto", "force", "off"].index(settings.ocr_mode),
        help="auto: runs OCR only on low-text pages. force: runs OCR on every page (slower). off: disables OCR."
    )
    settings.ocr_mode = ocr_mode

    st.write("**Ingestion Pipeline Flow:**")
    st.markdown("""
    1. **File Validation**: File integrity scan & size enforcement
    2. **Auto-Reference Cataloging**: Extract DOIs and query CrossRef API
    3. **Page Map Extraction**: Page-by-page text parsing
    4. **Image & OCR Rendering**: Generates page images & runs Tesseract (if required)
    5. **Chunk & Indexing**: Generates overlapping chunks & caches SentenceTransformer vectors
    """)

if rebuild_btn:
    if not uploaded_files and not import_url.strip():
        st.warning("Please upload a document or provide an arXiv/PDF URL first.")
    else:
        st.subheader("📊 Ingestion Pipeline Logs")
        
        saved_paths = []
        logs_box = st.empty()
        log_msgs = []
        
        def add_log(msg: str, is_success: bool = True):
            prefix = "🟢" if is_success else "🔴"
            log_msgs.append(f"{prefix} {msg}")
            logs_box.code("\n".join(log_msgs))

        valid = True
        
        # 1. Handle URL Import
        if import_url.strip():
            try:
                add_log(f"Downloading paper from URL: {import_url}...")
                dl_path = download_paper_from_url(import_url.strip())
                saved_paths.append(dl_path)
                add_log(f"Successfully downloaded paper and saved to: {dl_path.name}")
            except Exception as e:
                add_log(f"Failed to import URL: {e}", is_success=False)
                valid = False

        # 2. Handle Uploaded Files
        if valid and uploaded_files:
            add_log("Starting validation of uploaded files...")
            for file in uploaded_files:
                file_bytes = file.read()
                size_mb = len(file_bytes) / (1024 * 1024)
                if size_mb > 20.0:
                    add_log(f"File {file.name} exceeds size limit (20MB). Aborting.", is_success=False)
                    valid = False
                    break
                    
                if file.name.lower().endswith(".pdf"):
                    if not file_bytes.startswith(b"%PDF"):
                        add_log(f"File {file.name} is not a valid PDF document. Aborting.", is_success=False)
                        valid = False
                        break
                
                out_path = settings.upload_dir / file.name
                with out_path.open("wb") as f:
                    f.write(file_bytes)
                saved_paths.append(out_path)
                add_log(f"Validated and saved: {file.name} ({size_mb:.2f} MB)")
            
        # 3. Process and Index
        if valid and saved_paths:
            add_log("Executing ingestion pipeline (extracting text + metadata + optional OCR)...")
            
            try:
                with st.spinner("Extracting contents and generating dynamic indexes..."):
                    retriever = HybridRetriever()
                    count = retriever.build_from_paths(saved_paths)
                
                add_log(f"Ingestion complete: Indexed {count} chunks across {len(saved_paths)} document(s)!")
                st.success(f"Successfully loaded and cached {len(saved_paths)} documents.")
            except Exception as e:
                add_log(f"Pipeline execution failed: {e}", is_success=False)
                st.error(f"Error during document indexing: {e}")
