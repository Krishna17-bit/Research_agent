from __future__ import annotations

import re
from app.core.schemas import SourceEvidence


def clean_source_name(name: str) -> str:
    """Standardize source names for matching (lowercase, no extensions, no spaces)."""
    name = name.lower().strip()
    for ext in (".pdf", ".txt", ".md", ".docx", ".html"):
        if name.endswith(ext):
            name = name[:-len(ext)]
    return re.sub(r"[^a-z0-9]", "", name)


def verify_citations(answer: str, evidence: list[SourceEvidence]) -> dict:
    """
    Parse inline citations like [filename.pdf p.3] or [filename p.3] or [filename page 3] from the answer.
    Validate them against the retrieved evidence chunks.
    
    Returns a dictionary with:
    - verified: list of verified citation references
    - unverified: list of citations that could not be matched
    - grounding_score: float (0.0 to 1.0)
    - details: detailed analysis of each citation
    - warnings: general warning messages
    """
    # Regex to find citations in format [name p.X] or [name pX] or [name page X]
    # Example: [scientific_rag_demo_paper.txt p.1]
    pattern = r"\[([^\]]+?)\s+(?:p\.?|page)\s*(\d+)\]"
    matches = re.finditer(pattern, answer)

    verified = []
    unverified = []
    details = []
    warnings = []

    # Map retrieved evidence by document name and page
    evidence_map = {}
    for ev in evidence:
        cleaned_src = clean_source_name(ev.source)
        evidence_map.setdefault(cleaned_src, {}).setdefault(ev.page, []).append(ev)

    total_citations = 0

    for match in matches:
        total_citations += 1
        full_cite = match.group(0)
        doc_ref = match.group(1).strip()
        page_ref = int(match.group(2).strip())

        # Clean document name for search
        cleaned_ref = clean_source_name(doc_ref)

        # Get context around citation in the answer
        start_idx = max(0, match.start() - 120)
        end_idx = min(len(answer), match.end() + 120)
        claim_context = answer[start_idx:end_idx].strip()

        # Find matching evidence
        matched_chunks = []
        # Try exact cleaned match, or substring match
        matched_src_key = None
        if cleaned_ref in evidence_map:
            matched_src_key = cleaned_ref
        else:
            # Try fuzzy substring matching
            for key in evidence_map:
                if key in cleaned_ref or cleaned_ref in key:
                    matched_src_key = key
                    break

        if matched_src_key and page_ref in evidence_map[matched_src_key]:
            matched_chunks = evidence_map[matched_src_key][page_ref]

        if matched_chunks:
            # We found a matching page in retrieved evidence! Now verify text overlap
            highest_overlap = 0.0
            best_chunk_id = None
            claim_words = set(re.findall(r"\w+", claim_context.lower()))

            for chunk in matched_chunks:
                chunk_words = set(re.findall(r"\w+", chunk.text.lower()))
                if claim_words:
                    intersection = claim_words.intersection(chunk_words)
                    overlap = len(intersection) / len(claim_words)
                else:
                    overlap = 0.0

                if overlap > highest_overlap:
                    highest_overlap = overlap
                    best_chunk_id = chunk.chunk_id

            overlap_status = "high" if highest_overlap > 0.18 else "medium" if highest_overlap > 0.06 else "low"

            verified.append(full_cite)
            details.append({
                "citation": full_cite,
                "document": doc_ref,
                "page": page_ref,
                "status": "verified",
                "text_overlap": float(highest_overlap),
                "overlap_status": overlap_status,
                "context": claim_context,
                "chunk_id": best_chunk_id
            })
        else:
            # No matching document/page in retrieved evidence
            unverified.append(full_cite)
            details.append({
                "citation": full_cite,
                "document": doc_ref,
                "page": page_ref,
                "status": "unverified",
                "text_overlap": 0.0,
                "overlap_status": "none",
                "context": claim_context,
                "chunk_id": None
            })

    # If the LLM didn't generate any citation but evidence was used
    if total_citations == 0 and len(evidence) > 0:
        # Check if the answer itself has overlaps with the evidence chunks
        # This is a general grounding check
        has_overlap = False
        answer_words = set(re.findall(r"\w+", answer.lower()))
        for ev in evidence[:3]:
            ev_words = set(re.findall(r"\w+", ev.text.lower()))
            if answer_words:
                inter = answer_words.intersection(ev_words)
                if len(inter) / len(answer_words) > 0.15:
                    has_overlap = True
                    break
        if not has_overlap:
            warnings.append("No inline citations found and answer text shows low overlap with retrieved context.")
        else:
            warnings.append("Answer uses text from evidence but lacks explicit inline page-level citations.")

    grounding_score = 1.0
    if total_citations > 0:
        grounding_score = len(verified) / total_citations

    if unverified:
        warnings.append(f"Answer contains {len(unverified)} citations pointing to sources/pages not in the retrieved context.")
    if grounding_score < 0.7 and total_citations > 0:
        warnings.append("Grounding is weak. Some claims might be hallucinated or extrapolated.")

    return {
        "verified": verified,
        "unverified": unverified,
        "grounding_score": grounding_score,
        "details": details,
        "warnings": warnings,
        "total_citations": total_citations
    }
