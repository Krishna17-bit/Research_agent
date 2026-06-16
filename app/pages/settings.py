import streamlit as st
from pathlib import Path

from app.core.config import settings
from app.core.llm import active_provider, generate_answer
from app.core.schemas import SourceEvidence

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>⚙️ Provider & LLM Service Configuration</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Configure generative LLM provider credentials, adjust vector chunk boundaries, toggle mock settings, and audit API health.
        </p>
    </div>
""", unsafe_allow_html=True)


def persist_env_file():
    """Save active settings configuration to the project .env file."""
    lines = [
        f"# Automatically generated environment settings - {active_provider()}",
        f"LLM_PROVIDER={settings.llm_provider}",
        f"MOCK_MODE={'true' if settings.mock_mode else 'false'}",
        f"GEMINI_API_KEY={settings.gemini_api_key or ''}",
        f"GEMINI_MODEL={settings.gemini_model}",
        f"OPENAI_API_KEY={settings.openai_api_key or ''}",
        f"OPENAI_MODEL={settings.openai_model}",
        f"ANTHROPIC_API_KEY={settings.anthropic_api_key or ''}",
        f"ANTHROPIC_MODEL={settings.anthropic_model}",
        f"GROQ_API_KEY={settings.groq_api_key or ''}",
        f"GROQ_MODEL={settings.groq_model}",
        f"MISTRAL_API_KEY={settings.mistral_api_key or ''}",
        f"MISTRAL_MODEL={settings.mistral_model}",
        f"OLLAMA_BASE_URL={settings.ollama_base_url}",
        f"OLLAMA_MODEL={settings.ollama_model}",
        f"CUSTOM_OPENAI_BASE_URL={settings.custom_openai_base_url or ''}",
        f"CUSTOM_OPENAI_API_KEY={settings.custom_openai_api_key or ''}",
        f"CUSTOM_OPENAI_MODEL={settings.custom_openai_model or ''}",
        f"EMBEDDING_PROVIDER={settings.embedding_provider}",
        f"EMBEDDING_MODEL={settings.embedding_model}",
        f"VECTOR_STORE={settings.vector_store}",
        f"TOP_K={settings.top_k}",
        f"CHUNK_SIZE={settings.chunk_size}",
        f"CHUNK_OVERLAP={settings.chunk_overlap}",
        f"SIMILARITY_THRESHOLD={settings.similarity_threshold}",
        f"RERANKER_ENABLED={'true' if settings.reranker_enabled else 'false'}",
        f"OCR_MODE={settings.ocr_mode}",
        f"OCR_DPI={settings.ocr_dpi}",
        f"OCR_MIN_TEXT_CHARS={settings.ocr_min_text_chars}",
        f"TESSERACT_CMD={settings.tesseract_cmd or ''}",
        f"SAVE_PAGE_IMAGES={'true' if settings.save_page_images else 'false'}"
    ]
    env_path = settings.resolve_path(Path(".env"))
    try:
        env_path.write_text("\n".join(lines), encoding="utf-8")
        st.success("Configuration successfully written to local .env file!")
    except Exception as e:
        st.error(f"Failed to write to .env file: {e}")


# Tab configuration
tab_gen, tab_rag, tab_ocr = st.tabs(["💡 Generative LLM Services", "🗂️ Embeddings & RAG Settings", "📸 OCR Configuration"])

with tab_gen:
    st.subheader("🤖 Choose Active LLM Provider")
    
    mock_mode = st.checkbox(
        "Enable Demonstration Mock Mode (Zero-Cost, No API Keys Required)", 
        value=settings.mock_mode,
        help="Simulates grounded research summary, methodology extraction, and Q&A answers without billing model APIs."
    )
    
    llm_provider = st.selectbox(
        "Active LLM Service Provider",
        options=["gemini", "openai", "anthropic", "groq", "mistral", "ollama", "custom"],
        index=["gemini", "openai", "anthropic", "groq", "mistral", "ollama", "custom"].index(settings.llm_provider.lower().strip())
    )
    
    st.write("---")
    st.subheader("🔑 Provider API Credentials")
    
    # Render API credentials inputs
    col1, col2 = st.columns(2)
    with col1:
        gemini_api_key = st.text_input("Gemini API Key", value=settings.gemini_api_key or "", type="password")
        gemini_model = st.text_input("Gemini Model Name", value=settings.gemini_model)
        
        openai_api_key = st.text_input("OpenAI API Key", value=settings.openai_api_key or "", type="password")
        openai_model = st.text_input("OpenAI Model Name", value=settings.openai_model)
        
        anthropic_api_key = st.text_input("Anthropic API Key", value=settings.anthropic_api_key or "", type="password")
        anthropic_model = st.text_input("Anthropic Model Name", value=settings.anthropic_model)
        
        groq_api_key = st.text_input("Groq API Key", value=settings.groq_api_key or "", type="password")
        groq_model = st.text_input("Groq Model Name", value=settings.groq_model)
        
    with col2:
        mistral_api_key = st.text_input("Mistral API Key", value=settings.mistral_api_key or "", type="password")
        mistral_model = st.text_input("Mistral Model Name", value=settings.mistral_model)
        
        ollama_base_url = st.text_input("Ollama Local Base URL", value=settings.ollama_base_url)
        ollama_model = st.text_input("Ollama Model Name", value=settings.ollama_model)
        
        st.write("**Custom OpenAI-Compatible Endpoint:**")
        custom_base = st.text_input("Custom Endpoint Base URL", value=settings.custom_openai_base_url or "")
        custom_key = st.text_input("Custom Endpoint API Key", value=settings.custom_openai_api_key or "", type="password")
        custom_model = st.text_input("Custom Endpoint Model Name", value=settings.custom_openai_model or "")

    st.write("---")
    
    # Test Connection
    test_btn = st.button("🧪 Connection Health Check Diagnostic")
    if test_btn:
        # Temporarily apply values to settings for testing
        settings.mock_mode = mock_mode
        settings.llm_provider = llm_provider
        settings.gemini_api_key = gemini_api_key if gemini_api_key else None
        settings.gemini_model = gemini_model
        settings.openai_api_key = openai_api_key if openai_api_key else None
        settings.openai_model = openai_model
        settings.anthropic_api_key = anthropic_api_key if anthropic_api_key else None
        settings.anthropic_model = anthropic_model
        settings.groq_api_key = groq_api_key if groq_api_key else None
        settings.groq_model = groq_model
        settings.mistral_api_key = mistral_api_key if mistral_api_key else None
        settings.mistral_model = mistral_model
        settings.ollama_base_url = ollama_base_url
        settings.ollama_model = ollama_model
        settings.custom_openai_base_url = custom_base if custom_base else None
        settings.custom_openai_api_key = custom_key if custom_key else None
        settings.custom_openai_model = custom_model if custom_model else None
        
        st.info(f"Pinging active provider connection: **{active_provider()}**...")
        test_evidence = [SourceEvidence(chunk_id="test", source="health_check.pdf", page=1, score=1.0, text="System is fully operational.")]
        
        try:
            ans, used, warns = generate_answer("Hello connection health check diagnostic", test_evidence)
            st.success(f"Connection Diagnostic Pass! Result: {ans[:200]}")
            if warns:
                st.warning(f"Connection warnings reported: {warns}")
        except Exception as e:
            st.error(f"Connection Health Check Failed: {e}")

    # Save button
    if st.button("💾 Save Settings to local .env", type="primary"):
        settings.mock_mode = mock_mode
        settings.llm_provider = llm_provider
        settings.gemini_api_key = gemini_api_key if gemini_api_key else None
        settings.gemini_model = gemini_model
        settings.openai_api_key = openai_api_key if openai_api_key else None
        settings.openai_model = openai_model
        settings.anthropic_api_key = anthropic_api_key if anthropic_api_key else None
        settings.anthropic_model = anthropic_model
        settings.groq_api_key = groq_api_key if groq_api_key else None
        settings.groq_model = groq_model
        settings.mistral_api_key = mistral_api_key if mistral_api_key else None
        settings.mistral_model = mistral_model
        settings.ollama_base_url = ollama_base_url
        settings.ollama_model = ollama_model
        settings.custom_openai_base_url = custom_base if custom_base else None
        settings.custom_openai_api_key = custom_key if custom_key else None
        settings.custom_openai_model = custom_model if custom_model else None
        persist_env_file()

with tab_rag:
    st.subheader("📚 Retriever Parameters")
    emb_model = st.text_input("HuggingFace Embedding Model", value=settings.embedding_model)
    vec_store = st.selectbox("Vector Store Type", options=["faiss", "lancedb", "chroma", "in_memory_numpy"], index=["faiss", "lancedb", "chroma", "in_memory_numpy"].index(settings.vector_store))
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        chunk_size = st.number_input("Text Chunk Size (chars)", min_value=100, max_value=5000, value=settings.chunk_size)
    with col_c2:
        chunk_overlap = st.number_input("Chunk Overlap (chars)", min_value=0, max_value=1000, value=settings.chunk_overlap)
        
    st.write("---")
    st.write("**Advanced Retrieval Enhancements:**")
    reranker_enabled = st.checkbox("Enable Cross-Encoder Reranking", value=settings.reranker_enabled)
    reranker_model = st.text_input("Cross-Encoder Reranker Model", value=settings.reranker_model)
    hyde_enabled = st.checkbox("Enable HyDE (Hypothetical Document Embeddings)", value=settings.hyde_enabled)
        
    if st.button("Save RAG Configuration", type="primary"):
        settings.embedding_model = emb_model
        settings.vector_store = vec_store
        settings.chunk_size = chunk_size
        settings.chunk_overlap = chunk_overlap
        settings.reranker_enabled = reranker_enabled
        settings.reranker_model = reranker_model
        settings.hyde_enabled = hyde_enabled
        persist_env_file()


with tab_ocr:
    st.subheader("📸 Multi-Modal & Tesseract OCR Parameters")
    tess_mode = st.selectbox("OCR mode", ["auto", "force", "off"], index=["auto", "force", "off"].index(settings.ocr_mode))
    tess_dpi = st.number_input("Render DPI for OCR parsing", min_value=72, max_value=600, value=settings.ocr_dpi)
    tess_limit = st.number_input("Minimum Text Threshold characters", min_value=10, max_value=1000, value=settings.ocr_min_text_chars)
    tess_cmd = st.text_input("Tesseract OCR Binary Path (Required on Windows if not in PATH)", value=settings.tesseract_cmd or "", placeholder="e.g. C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
    
    if st.button("Save OCR Configuration", type="primary"):
        settings.ocr_mode = tess_mode
        settings.ocr_dpi = tess_dpi
        settings.ocr_min_text_chars = tess_limit
        settings.tesseract_cmd = tess_cmd if tess_cmd else None
        persist_env_file()
