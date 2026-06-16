from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from the project-root .env file."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Active Provider configuration
    llm_provider: str = "gemini"
    mock_mode: bool = True

    # Gemini configuration
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"  # Use flash by default as it's fast and cheap

    # OpenAI configuration
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Anthropic configuration
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Groq configuration
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-70b-versatile"

    # Mistral configuration
    mistral_api_key: str | None = None
    mistral_model: str = "mistral-large-latest"

    # Ollama configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Custom OpenAI-compatible configuration
    custom_openai_base_url: str | None = None
    custom_openai_api_key: str | None = None
    custom_openai_model: str | None = None

    # Embedding and Vector store configuration
    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store: str = "faiss"
    top_k: int = 7
    chunk_size: int = 900
    chunk_overlap: int = 150
    upload_dir: Path = Path("app/storage/uploads")
    index_dir: Path = Path("app/storage/vector_index")
    similarity_threshold: float = 0.20
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    hyde_enabled: bool = False



    # OCR/image extraction controls.
    # off  = never run OCR
    # auto = OCR only pages with little/no selectable text
    # force = OCR every PDF page and merge with normal text
    ocr_mode: str = "auto"
    ocr_dpi: int = 220
    ocr_min_text_chars: int = 120
    tesseract_cmd: str | None = None
    save_page_images: bool = True
    page_image_dir: Path = Path("app/storage/page_images")

    def resolve_path(self, path: Path) -> Path:
        return path if path.is_absolute() else PROJECT_ROOT / path


settings = Settings()
settings.upload_dir = settings.resolve_path(settings.upload_dir)
settings.index_dir = settings.resolve_path(settings.index_dir)
settings.page_image_dir = settings.resolve_path(settings.page_image_dir)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.index_dir.mkdir(parents=True, exist_ok=True)
settings.page_image_dir.mkdir(parents=True, exist_ok=True)
