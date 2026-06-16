from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

from app.core.config import settings
from app.core.schemas import SourceEvidence


def _send_post_request(url: str, headers: dict[str, str], data: dict) -> str:
    """Send a HTTP POST request and return the string response."""
    json_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_content = e.read().decode("utf-8")
        try:
            err_json = json.loads(error_content)
            error_msg = err_json.get("error", {}).get("message", error_content)
        except Exception:
            error_msg = error_content
        raise RuntimeError(f"API HTTP Error {e.code}: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to API: {e}")


def call_openai(system_prompt: str, prompt: str) -> str:
    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    res_str = _send_post_request(url, headers, data)
    res_json = json.loads(res_str)
    return res_json["choices"][0]["message"]["content"]


def call_anthropic(system_prompt: str, prompt: str) -> str:
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    data = {
        "model": settings.anthropic_model,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4000,
        "temperature": 0.1
    }
    res_str = _send_post_request(url, headers, data)
    res_json = json.loads(res_str)
    return res_json["content"][0]["text"]


def call_groq(system_prompt: str, prompt: str) -> str:
    api_key = settings.groq_api_key
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    res_str = _send_post_request(url, headers, data)
    res_json = json.loads(res_str)
    return res_json["choices"][0]["message"]["content"]


def call_mistral(system_prompt: str, prompt: str) -> str:
    api_key = settings.mistral_api_key
    if not api_key:
        raise ValueError("MISTRAL_API_KEY is not set.")
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": settings.mistral_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    res_str = _send_post_request(url, headers, data)
    res_json = json.loads(res_str)
    return res_json["choices"][0]["message"]["content"]


def call_ollama(system_prompt: str, prompt: str) -> str:
    url = f"{settings.ollama_base_url}/api/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    res_str = _send_post_request(url, headers, data)
    res_json = json.loads(res_str)
    return res_json["message"]["content"]


def call_custom_openai(system_prompt: str, prompt: str) -> str:
    base_url = settings.custom_openai_base_url
    api_key = settings.custom_openai_api_key or "no-key"
    model = settings.custom_openai_model or "custom-model"
    if not base_url:
        raise ValueError("CUSTOM_OPENAI_BASE_URL is not set.")
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    res_str = _send_post_request(url, headers, data)
    res_json = json.loads(res_str)
    return res_json["choices"][0]["message"]["content"]


def call_mock(prompt: str, evidence: list[SourceEvidence]) -> str:
    """Generate a high-quality mock response summarizing or detailing findings based on actual evidence chunks."""
    if not evidence:
        return "I could not find relevant evidence in the indexed documents."

    doc_refs = list(dict.fromkeys(f"[{e.source} p.{e.page}]" for e in evidence))
    docs_list = list(dict.fromkeys(e.source for e in evidence))

    # Determine type of request from prompt
    prompt_lower = prompt.lower()

    if "reproducibility checklist" in prompt_lower:
        title = "Mock Reproducibility Checklist"
        content = f"""### 🔬 Reproducibility Checklist & Verification Summary

Based on {', '.join(docs_list)}, here is the extracted reproducibility outline:

1. **Available Data & Source Material**:
   - Core findings and text data are verified from {doc_refs[0]} and {doc_refs[-1]}.
   - High data integrity check is established from {evidence[0].source} page {evidence[0].page}.
2. **Methodological Setup**:
   - Preprocessing variables and model parameter outlines are details in {doc_refs[0]}.
3. **Execution Blockers & Gaps**:
   - Stated limits, constraints, and hardware restrictions were noted in {doc_refs[-1]}.
   - Figure/table descriptions from {evidence[0].source} were parsed using visual/OCR methods.

*Warning: This is generated in Mock Demonstration Mode.*
"""
    elif "methodology" in prompt_lower or "method" in prompt_lower:
        content = f"""### 🧪 Extracted Methodology & Execution Pipeline

The core methodology detailed in the retrieved documents consists of the following pipeline stages:

1. **System Ingestion & Setup**:
   - The primary research objective is detailed in the abstract and introduction of {doc_refs[0]}.
   - The authors formulate the core equation and setup criteria on {evidence[0].source} p.{evidence[0].page}.
2. **Pre-processing and Semantic Indexing**:
   - Splitting of structural text chunks is detailed on page {evidence[0].page} of {evidence[0].source}.
   - Multi-modal aspects (OCR captions, plot labels) are captured as described in {doc_refs[-1]}.
3. **Evaluation baselines**:
   - Baseline metrics (Lexical overlap, cosine similarity bounds) are compared in {doc_refs[-1]}.

**Verifiable Evidence Block**:
> "{evidence[0].text[:220]}..." ({evidence[0].source} p.{evidence[0].page})
"""
    elif "research gaps" in prompt_lower or "limitations" in prompt_lower:
        content = f"""### 🔍 Research Gaps & Stated Limitations

An audit of the limitations and future work sections in the active workspace files reveals:

1. **OCR & Table Parsing Noise**:
   - The authors explicit mention that complex table formatting is not perfectly captured, necessitating human verification {doc_refs[-1]}.
2. **Missing Evaluations**:
   - Stated future experiments include multi-modal image evaluation and scaling tests on high-performance vector indexes {doc_refs[0]}.
3. **Unresolved Assumptions**:
   - Assumptions regarding local resource availability are documented in {doc_refs[0]}.

**Identified Research Question**:
- *How can we scale local-first hybrid vector search engines to multi-gigabyte corpora without introducing retrieval delays?* Stated clues are retrieved from {doc_refs[-1]}.
"""
    elif "compare" in prompt_lower:
        content = f"""### ⚖️ Cross-Paper Methodology Comparison

Based on the files active in the workspace ({', '.join(docs_list)}), the following comparative analysis was generated:

| Aspect / Metric | {docs_list[0]} | {docs_list[1] if len(docs_list) > 1 else 'Baseline (Standard RAG)'} | Supporting Evidence |
| :--- | :--- | :--- | :--- |
| **Primary Method** | Hybrid lexical + semantic embedding alignment | Extractive keyword or semantic-only parsing | {doc_refs[0]} |
| **Metadata Tracking** | Dynamic page-aware indexing | Global chunk mapping | {doc_refs[0]} |
| **Limitations** | Scanning & OCR noise on formulas | Hallucination rates, weak citations | {doc_refs[-1]} |
| **Grounded Answering** | Inline citations with page numbers | Answer summary without grounding | {doc_refs[-1]} |
"""
    elif "results" in prompt_lower or "figures" in prompt_lower or "tables" in prompt_lower:
        content = f"""### 📊 Extracted Results, Figure & Table Summaries

The following key results and figures are extracted from the retrieved segments:

1. **Experimental Findings**:
   - Key contribution and evaluation scores are detailed in {doc_refs[0]}.
   - Quantitative evaluation highlights performance metrics as stated in {evidence[0].source} p.{evidence[0].page}.
2. **Figure & Table Captions**:
   - Selected captions matching tables/figures are indexed.
   - Text details: *"{evidence[-1].text[:180]}..."* ({evidence[-1].source} p.{evidence[-1].page}).

*Confidence rate is high based on matching terms in the active vector space.*
"""
    else:
        # Standard Q&A prompt mock response
        content = f"""### 💬 Grounded Research Answer

Based on your question and the retrieved evidence from the active library, here is the verified analysis:

The primary concept discussed in the context refers to **Citation-Grounded Q&A** and RAG systems. As stated on page {evidence[0].page} of {evidence[0].source}, the system splits text into overlapping page-aware chunks and computes semantic embeddings.

Additionally, exact acronyms and dataset identifiers are preserved using a lexical BM25 fallback, as highlighted in {doc_refs[-1]}.

**Key Extracted Points**:
- The hybrid search score is evaluated as: `0.62 * Semantic + 0.38 * BM25` {doc_refs[0]}.
- Source verification is essential for compliance and legal analysis {doc_refs[-1]}.

**Evidence Context**:
- *"{evidence[0].text[:300]}..."* ({evidence[0].source} p.{evidence[0].page})
"""

    return content
