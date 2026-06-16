from __future__ import annotations

import time
from app.core.llm import generate_answer, active_provider
from app.core.retriever import HybridRetriever
from app.core.schemas import RAGAnswer
from app.core.verifier import verify_citations
from app.core import database
from app.core.config import settings


class ResearchAgent:
    def __init__(self, retriever: HybridRetriever | None = None):
        self.retriever = retriever or HybridRetriever()

    def ask(self, question: str, top_k: int | None = None, doc_ids: list[str] | None = None) -> RAGAnswer:
        start_time = time.time()
        
        # 1. Retrieve context
        evidence = self.retriever.search(question, top_k=top_k, doc_ids=doc_ids)
        
        # 2. Generate answer
        answer, used_llm, warnings = generate_answer(question, evidence)
        latency = time.time() - start_time

        # 3. Verify citations
        if evidence:
            verify_res = verify_citations(answer, evidence)
            grounding_score = verify_res["grounding_score"]
            # Append verification warnings to warnings list
            warnings.extend(verify_res["warnings"])
            citation_quality = f"Grounding rate: {grounding_score:.1%}"
        else:
            citation_quality = "No evidence retrieved"
            grounding_score = 0.0

        confidence = "high" if evidence and evidence[0].score > 0.55 and grounding_score >= 0.8 else "medium" if evidence and grounding_score >= 0.5 else "low"

        # 4. Estimate token costs (approximate heuristics)
        word_count = len(answer.split()) + sum(len(ev.text.split()) for ev in evidence)
        estimated_tokens = int(word_count * 1.3)
        estimated_cost = 0.0
        
        if used_llm and not settings.mock_mode:
            prov = settings.llm_provider.lower().strip()
            if "openai" in prov:
                estimated_cost = (estimated_tokens / 1_000_000) * 0.15 # gpt-4o-mini scale
            elif "gemini" in prov:
                estimated_cost = (estimated_tokens / 1_000_000) * 0.075 # gemini flash scale
            elif "anthropic" in prov:
                estimated_cost = (estimated_tokens / 1_000_000) * 3.00 # claude sonnet scale

        # 5. Log run history in SQLite
        citations_data = [
            {"source": ev.source, "page": ev.page, "score": ev.score, "text": ev.text[:200]}
            for ev in evidence
        ]
        active_prov = active_provider()
        model_name = getattr(settings, f"{settings.llm_provider}_model", "default") if not settings.mock_mode else "mock"
        
        database.add_run(
            question=question,
            answer=answer,
            confidence=confidence,
            latency=latency,
            tokens=estimated_tokens,
            cost=estimated_cost,
            provider=active_prov,
            model=str(model_name),
            feedback=None,
            citation_quality=citation_quality,
            citations=citations_data
        )

        return RAGAnswer(
            question=question,
            answer=answer,
            confidence=confidence,
            citations=evidence,
            used_llm=used_llm,
            warnings=warnings,
        )

    def summarize(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Create a structured research brief with: research problem, core method, dataset/simulation, "
            "main results, limitations, and future work. Include citations for each claim.",
            top_k=12,
            doc_ids=doc_ids
        )

    def compare_methods(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Compare the main methods or approaches discussed in the documents. Include assumptions, "
            "strengths, weaknesses, evaluation metrics, and limitations.",
            top_k=12,
            doc_ids=doc_ids
        )

    def extract_contributions(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Extract the paper's key contributions as bullet points. For each contribution, include the "
            "supporting evidence and any stated limitation.",
            top_k=10,
            doc_ids=doc_ids
        )

    def find_limitations(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Identify limitations, assumptions, failure modes, simplified settings, missing experiments, "
            "and future-work items mentioned in the documents.",
            top_k=12,
            doc_ids=doc_ids
        )

    def extract_methodology(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Extract the methodology as a reproducible pipeline: inputs, preprocessing, model/algorithm, "
            "training or analysis procedure, evaluation metrics, baselines, and implementation details.",
            top_k=14,
            doc_ids=doc_ids
        )

    def extract_results(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Extract all reported results from text, tables, figures, captions, and OCR evidence. Include "
            "metrics, numerical values, dataset names, figure/table references, and stated comparisons.",
            top_k=14,
            doc_ids=doc_ids
        )

    def reproducibility_checklist(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Create a reproducibility checklist for this paper: available data, code, model details, "
            "hyperparameters, hardware, random seeds, metrics, baselines, missing details, and likely blockers.",
            top_k=14,
            doc_ids=doc_ids
        )

    def research_gap_analysis(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "Find research gaps and possible next experiments based only on stated limitations, simplified "
            "assumptions, future work, missing datasets, missing comparisons, and weak evidence in the document.",
            top_k=14,
            doc_ids=doc_ids
        )

    def claim_checker(self, doc_ids: list[str] | None = None) -> RAGAnswer:
        return self.ask(
            "List the strongest technical claims in the document and map each claim to supporting evidence. "
            "Flag claims that appear weak, unsupported, only partially supported, or dependent on OCR/noisy evidence.",
            top_k=14,
            doc_ids=doc_ids
        )
