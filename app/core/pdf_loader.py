from __future__ import annotations

import hashlib
from pathlib import Path
import re
import fitz

from app.core.schemas import DocumentChunk
from app.core.config import settings


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    # clean common OCR/page header noise lightly without destroying equations
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    return text


def _doc_id(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.name.encode("utf-8"))
    h.update(str(path.stat().st_size).encode("utf-8"))
    return h.hexdigest()[:16]


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    text = _clean(text)
    if len(text) <= size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        candidate = text[start:end]
        last_sentence = max(candidate.rfind(". "), candidate.rfind("; "), candidate.rfind("\n"))
        if last_sentence > size * 0.55 and end != len(text):
            end = start + last_sentence + 1
            candidate = text[start:end]
        chunks.append(candidate.strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if len(c) > 30]


def _ensure_tesseract_configured() -> None:
    if settings.tesseract_cmd:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _ocr_page(page: fitz.Page, doc_id: str, source: str, page_number: int) -> str:
    """Render a PDF page and OCR it. Returns empty string if OCR is unavailable."""
    try:
        _ensure_tesseract_configured()
        import pytesseract
        from PIL import Image

        zoom = settings.ocr_dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        if settings.save_page_images:
            image_dir = settings.page_image_dir / doc_id
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{source}_page_{page_number:04d}.png"
            pix.save(str(image_path))

        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(image)
        return _clean(text)
    except Exception as exc:
        return f"[OCR unavailable or failed on page {page_number}: {exc}]"


def _extract_figure_table_blocks(page: fitz.Page) -> str:
    """Extract likely figure/table captions from selectable text blocks."""
    captions: list[str] = []
    try:
        blocks = page.get_text("blocks")
        for block in blocks:
            text = _clean(block[4] if len(block) > 4 else "")
            lower = text.lower()
            if lower.startswith(("figure ", "fig. ", "fig ", "table ", "tab. ")) or " figure " in lower[:80] or " table " in lower[:80]:
                captions.append(text)
    except Exception:
        pass
    return "\n".join(dict.fromkeys(captions))


def load_pdf(path: Path) -> list[DocumentChunk]:
    doc = fitz.open(path)
    doc_id = _doc_id(path)
    chunks: list[DocumentChunk] = []
    mode = (settings.ocr_mode or "auto").lower().strip()

    for i, page in enumerate(doc, start=1):
        native_text = _clean(page.get_text("text"))
        captions = _extract_figure_table_blocks(page)

        page_parts: list[tuple[str, str]] = []
        if native_text:
            page_parts.append(("text", native_text))
        if captions:
            page_parts.append(("figure/table captions", captions))

        should_ocr = mode == "force" or (mode == "auto" and len(native_text) < settings.ocr_min_text_chars)
        if mode != "off" and should_ocr:
            ocr_text = _ocr_page(page, doc_id=doc_id, source=path.name, page_number=i)
            if ocr_text and not ocr_text.startswith("[OCR unavailable"):
                page_parts.append(("ocr/image text", ocr_text))
            elif ocr_text:
                page_parts.append(("ocr warning", ocr_text))

        if not page_parts:
            continue

        combined = "\n\n".join(f"[{label}]\n{text}" for label, text in page_parts if text)
        for j, piece in enumerate(chunk_text(combined)):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_id}:p{i}:c{j}",
                    doc_id=doc_id,
                    source=path.name,
                    page=i,
                    text=piece,
                    section_hint=None,
                )
            )
    return chunks


def load_text_file(path: Path) -> list[DocumentChunk]:
    doc_id = _doc_id(path)
    raw = path.read_text(encoding="utf-8")
    chunks = []
    for j, piece in enumerate(chunk_text(_clean(raw))):
        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc_id}:txt:c{j}",
                doc_id=doc_id,
                source=path.name,
                page=1,
                text=piece,
            )
        )
    return chunks


def load_document(path: Path) -> list[DocumentChunk]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix in {".txt", ".md"}:
        return load_text_file(path)
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF, TXT, or MD.")


def extract_metadata(path: Path) -> dict:
    """Extract metadata (title, author, year, doc_type) from a PDF or text file."""
    import datetime
    meta = {
        "title": path.stem.replace("_", " ").replace("-", " ").title(),
        "authors": "Unknown",
        "year": str(datetime.datetime.now().year),
        "doc_type": "paper",
        "tags": "imported",
        "page_count": 1
    }
    
    if path.suffix.lower() == ".pdf":
        try:
            doc = fitz.open(path)
            meta["page_count"] = len(doc)
            title = doc.metadata.get("title")
            if title and len(title.strip()) > 3:
                meta["title"] = title.strip()
            authors = doc.metadata.get("author")
            if authors and len(authors.strip()) > 3:
                meta["authors"] = authors.strip()
            
            creation_date = doc.metadata.get("creationDate")
            if creation_date and len(creation_date) > 4:
                match = re.search(r"\d{4}", creation_date)
                if match:
                    meta["year"] = match.group(0)
            
            if len(doc) > 0:
                first_page = doc[0].get_text("text")[:2000].lower()
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", first_page)
                if year_match:
                    meta["year"] = year_match.group(0)
                
                if "thesis" in first_page or "dissertation" in first_page:
                    meta["doc_type"] = "thesis"
                elif "user manual" in first_page or "instruction manual" in first_page or "reference guide" in first_page:
                    meta["doc_type"] = "manual"
                elif "patent" in first_page:
                    meta["doc_type"] = "patent"
                elif "whitepaper" in first_page or "white paper" in first_page:
                    meta["doc_type"] = "whitepaper"
                elif "report" in first_page:
                    meta["doc_type"] = "report"
                
                if not title or len(title.strip()) < 5:
                    lines = [l.strip() for l in doc[0].get_text("text").split("\n") if l.strip()]
                    if lines:
                        meta["title"] = lines[0][:150]
        except Exception:
            pass
    return meta

