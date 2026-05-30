from __future__ import annotations

from app.core.llm import generate_answer
from app.core.retriever import HybridRetriever
from app.core.schemas import RAGAnswer


class ResearchAgent:
    def __init__(self, retriever: HybridRetriever | None = None):
        self.retriever = retriever or HybridRetriever()

    def ask(self, question: str, top_k: int | None = None) -> RAGAnswer:
        evidence = self.retriever.search(question, top_k=top_k)
        answer, used_llm, warnings = generate_answer(question, evidence)
        confidence = "high" if evidence and evidence[0].score > 0.55 else "medium" if evidence else "low"
        return RAGAnswer(
            question=question,
            answer=answer,
            confidence=confidence,
            citations=evidence,
            used_llm=used_llm,
            warnings=warnings,
        )

    def summarize(self) -> RAGAnswer:
        return self.ask(
            "Create a structured research brief with: research problem, core method, dataset/simulation, "
            "main results, limitations, and future work. Include citations for each claim.",
            top_k=12,
        )

    def compare_methods(self) -> RAGAnswer:
        return self.ask(
            "Compare the main methods or approaches discussed in the documents. Include assumptions, "
            "strengths, weaknesses, evaluation metrics, and limitations.",
            top_k=12,
        )

    def extract_contributions(self) -> RAGAnswer:
        return self.ask(
            "Extract the paper's key contributions as bullet points. For each contribution, include the "
            "supporting evidence and any stated limitation.",
            top_k=10,
        )

    def find_limitations(self) -> RAGAnswer:
        return self.ask(
            "Identify limitations, assumptions, failure modes, simplified settings, missing experiments, "
            "and future-work items mentioned in the documents.",
            top_k=12,
        )

    def extract_methodology(self) -> RAGAnswer:
        return self.ask(
            "Extract the methodology as a reproducible pipeline: inputs, preprocessing, model/algorithm, "
            "training or analysis procedure, evaluation metrics, baselines, and implementation details.",
            top_k=14,
        )

    def extract_results(self) -> RAGAnswer:
        return self.ask(
            "Extract all reported results from text, tables, figures, captions, and OCR evidence. Include "
            "metrics, numerical values, dataset names, figure/table references, and stated comparisons.",
            top_k=14,
        )

    def reproducibility_checklist(self) -> RAGAnswer:
        return self.ask(
            "Create a reproducibility checklist for this paper: available data, code, model details, "
            "hyperparameters, hardware, random seeds, metrics, baselines, missing details, and likely blockers.",
            top_k=14,
        )

    def research_gap_analysis(self) -> RAGAnswer:
        return self.ask(
            "Find research gaps and possible next experiments based only on stated limitations, simplified "
            "assumptions, future work, missing datasets, missing comparisons, and weak evidence in the document.",
            top_k=14,
        )

    def claim_checker(self) -> RAGAnswer:
        return self.ask(
            "List the strongest technical claims in the document and map each claim to supporting evidence. "
            "Flag claims that appear weak, unsupported, only partially supported, or dependent on OCR/noisy evidence.",
            top_k=14,
        )
