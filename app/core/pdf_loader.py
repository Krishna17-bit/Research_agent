from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
import datetime
import fitz

from app.core.schemas import DocumentChunk
from app.core.config import settings


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
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
            image_path = image_dir / f"page_{page_number:04d}.png"
            pix.save(str(image_path))

        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(image)
        return _clean(text)
    except Exception as exc:
        return f"[OCR unavailable or failed on page {page_number}: {exc}]"


def render_page_image(page: fitz.Page, doc_id: str, page_number: int) -> Path | None:
    """Render a PDF page to a PNG image for UI rendering."""
    try:
        image_dir = settings.page_image_dir / doc_id
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / f"page_{page_number:04d}.png"
        
        # Render page to pixmap (approx 150 DPI for rapid render & low memory footprint)
        zoom = 150 / 72
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(str(image_path))
        return image_path
    except Exception:
        return None


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

        # Cache page image for visual citations
        if settings.save_page_images:
            render_page_image(page, doc_id, i)

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


# --- Advanced Features: URL Importing & DOI Metadata Search ---

def download_paper_from_url(url: str) -> Path:
    """Download a paper from arXiv or any direct PDF URL and save it locally."""
    url = url.strip()
    headers = {"User-Agent": "ResearchAgent/1.0 (mailto:agent@researchrag.local)"}
    
    # Detect arXiv links
    # e.g., https://arxiv.org/abs/1706.03762 or https://arxiv.org/pdf/1706.03762.pdf
    arxiv_match = re.search(r"arxiv\.org/(abs|pdf)/(\d+\.\d+)", url)
    if arxiv_match:
        arxiv_id = arxiv_match.group(2)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        file_name = f"arxiv_{arxiv_id}.pdf"
    else:
        # Resolve normal URL file name
        path_segments = urllib.parse.urlparse(url).path.split("/")
        file_name = path_segments[-1] if path_segments[-1].lower().endswith((".pdf", ".txt", ".md")) else "downloaded_paper.pdf"

    out_path = settings.upload_dir / file_name
    
    # Download file using request urlopen
    req = urllib.request.Request(pdf_url if arxiv_match else url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        with open(out_path, "wb") as f:
            f.write(response.read())
            
    return out_path


def find_doi(text: str) -> str | None:
    """Scan text for DOI patterns."""
    pattern = r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def fetch_crossref_metadata(doi: str) -> dict | None:
    """Fetch structured metadata and format BibTeX from CrossRef API."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "ResearchAgent/1.0 (mailto:agent@researchrag.local)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            item = data.get("message", {})
            
            title = item.get("title", [""])[0]
            
            # Form authors string
            authors_list = []
            for auth in item.get("author", []):
                authors_list.append(f"{auth.get('given', '')} {auth.get('family', '')}".strip())
            authors = ", ".join(authors_list) if authors_list else "Unknown"
            
            # Form year
            pub_date = item.get("published-print") or item.get("published-online") or {}
            date_parts = pub_date.get("date-parts", [[str(datetime.datetime.now().year)]])
            year = str(date_parts[0][0])
            
            # Document Type mapping
            doc_type = "paper"
            work_type = item.get("type", "").lower()
            if "dissertation" in work_type or "thesis" in work_type:
                doc_type = "thesis"
            elif "report" in work_type:
                doc_type = "report"
            elif "book" in work_type:
                doc_type = "book"
                
            # Generate BibTeX
            primary_author = re.sub(r"\W+", "", authors_list[0].split()[-1] if authors_list else "author")
            bib_key = f"{primary_author.lower()}{year}"
            
            bibtex = f"""@article{{{bib_key},
  title = {{{title}}},
  author = {{{' and '.join(authors_list) if authors_list else 'Unknown'}}},
  year = {{{year}}},
  journal = {{{item.get('container-title', [''])[0]}}},
  doi = {{{doi}}},
  url = {{https://doi.org/{doi}}}
}}"""
            
            return {
                "title": title,
                "authors": authors,
                "year": year,
                "doc_type": doc_type,
                "bibtex": bibtex,
                "doi": doi
            }
    except Exception:
        return None


def search_crossref_by_title(title: str) -> dict | None:
    """Fuzzy search CrossRef by document title to find a matching DOI metadata entry."""
    query = urllib.parse.quote_plus(title)
    url = f"https://api.crossref.org/works?query={query}&rows=1"
    headers = {"User-Agent": "ResearchAgent/1.0 (mailto:agent@researchrag.local)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("message", {}).get("items", [])
            if items:
                item = items[0]
                doi = item.get("DOI")
                if doi:
                    return fetch_crossref_metadata(doi)
    except Exception:
        pass
    return None


def extract_metadata(path: Path) -> dict:
    """Extract metadata from PDF text and refine it using CrossRef lookup."""
    meta = {
        "title": path.stem.replace("_", " ").replace("-", " ").title(),
        "authors": "Unknown",
        "year": str(datetime.datetime.now().year),
        "doc_type": "paper",
        "tags": "imported",
        "page_count": 1,
        "bibtex": "",
        "doi": ""
    }
    
    first_page_text = ""
    if path.suffix.lower() == ".pdf":
        try:
            doc = fitz.open(path)
            meta["page_count"] = len(doc)
            if len(doc) > 0:
                first_page_text = doc[0].get_text("text")[:2000]
        except Exception:
            pass
            
    # Try finding DOI in first page text
    doi = find_doi(first_page_text)
    if doi:
        cr_meta = fetch_crossref_metadata(doi)
        if cr_meta:
            meta.update(cr_meta)
            return meta

    # If no DOI found, try searching CrossRef using filename title heuristic
    cr_meta = search_crossref_by_title(meta["title"])
    if cr_meta:
        meta.update(cr_meta)
        return meta

    # Fallback to local regex heuristics if API query fails
    if path.suffix.lower() == ".pdf":
        try:
            doc = fitz.open(path)
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
            
            if first_page_text:
                lower_text = first_page_text.lower()
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", lower_text)
                if year_match:
                    meta["year"] = year_match.group(0)
                
                if "thesis" in lower_text or "dissertation" in lower_text:
                    meta["doc_type"] = "thesis"
                elif "user manual" in lower_text or "instruction manual" in lower_text or "reference guide" in lower_text:
                    meta["doc_type"] = "manual"
                elif "patent" in lower_text:
                    meta["doc_type"] = "patent"
                elif "whitepaper" in lower_text or "white paper" in lower_text:
                    meta["doc_type"] = "whitepaper"
                elif "report" in lower_text:
                    meta["doc_type"] = "report"
                
                if not title or len(title.strip()) < 5:
                    lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
                    if lines:
                        meta["title"] = lines[0][:150]
        except Exception:
            pass
            
    # Generate generic BibTeX fallback
    primary_author_fallback = "author"
    bib_key = f"{primary_author_fallback}{meta['year']}"
    meta["bibtex"] = f"""@article{{{bib_key},
  title = {{{meta['title']}}},
  author = {{{meta['authors']}}},
  year = {{{meta['year']}}},
  journal = {{Scientific Archive}}
}}"""
    return meta
