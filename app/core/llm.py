from __future__ import annotations

from app.core.config import settings
from app.core.schemas import SourceEvidence

SYSTEM = """You are a scientific research assistant. Answer only using the supplied evidence.
Rules:
- Cite evidence inline as [source p.page].
- If evidence is insufficient, say what is missing.
- Be precise, technical, and avoid unsupported claims.
- Prefer equations, variables, methods, datasets, results, limitations, figure/table findings, and future work when available.
- Do not invent paper details that are not present in the evidence.
- Treat OCR/image-derived evidence as useful but potentially noisy; mention uncertainty when text appears incomplete.
"""


def _clean_key(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    return value or None


def active_provider() -> str:
    if _clean_key(settings.gemini_api_key):
        return f"Gemini ({settings.gemini_model})"
    return "Offline extractive mode"


def _evidence_block(evidence: list[SourceEvidence]) -> str:
    return "\n\n".join(
        f"[{i + 1}] Source: {e.source}, page {e.page}, score {e.score:.3f}\n{e.text}"
        for i, e in enumerate(evidence)
    )


def offline_answer(question: str, evidence: list[SourceEvidence]) -> str:
    if not evidence:
        return "I could not find relevant evidence in the indexed documents."

    bullets = []
    for ev in evidence[:6]:
        snippet = ev.text[:650].strip()
        if len(ev.text) > 650:
            snippet += "..."
        bullets.append(f"- {snippet} [{ev.source} p.{ev.page}]")

    return (
        "No Gemini key was found, so I am using extractive evidence mode.\n\n"
        f"Question: {question}\n\nMost relevant evidence:\n" + "\n".join(bullets)
    )


def _prompt(question: str, evidence: list[SourceEvidence]) -> str:
    return f"""
Question:
{question}

Evidence:
{_evidence_block(evidence)}

Write a research-grade answer using only the evidence above.
Use clear section headings when useful.
Every important factual claim must have an inline citation like [filename.pdf p.3].
If evidence comes from OCR or figure/table text, use it carefully and say when details are incomplete.
If the answer requires information missing from the evidence, say exactly what is missing.
""".strip()


def _generate_with_gemini(question: str, evidence: list[SourceEvidence]) -> str:
    from google import genai

    api_key = _clean_key(settings.gemini_api_key)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is empty")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=f"{SYSTEM}\n\n{_prompt(question, evidence)}",
    )
    return response.text or ""


def generate_answer(question: str, evidence: list[SourceEvidence]) -> tuple[str, bool, list[str]]:
    warnings: list[str] = []

    if not evidence:
        return (
            "I could not find relevant evidence in the indexed documents.",
            False,
            ["No evidence retrieved."],
        )

    if _clean_key(settings.gemini_api_key):
        try:
            return _generate_with_gemini(question, evidence), True, warnings
        except Exception as exc:
            warnings.append(f"Gemini call failed; used extractive fallback. Error: {exc}")

    warnings.append("No GEMINI_API_KEY set; used extractive fallback.")
    return offline_answer(question, evidence), False, warnings
