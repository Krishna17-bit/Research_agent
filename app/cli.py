from __future__ import annotations

from pathlib import Path
import typer
from rich import print
from rich.panel import Panel
from rich.table import Table

from app.core.agent import ResearchAgent
from app.core.retriever import HybridRetriever
from app.core import database
from app.core.config import settings

app = typer.Typer(help="Research PDF RAG Agent CLI")


@app.command()
def index(paths: list[Path]):
    """Index one or more PDF/TXT/MD documents into the local library."""
    print("[bold blue]Starting document ingestion pipeline...[/bold blue]")
    count = HybridRetriever().build_from_paths(paths)
    print(f"[green]Successfully cataloged and indexed {count} chunks.[/green]")


@app.command()
def ask(question: str, top_k: int = 7):
    """Ask a grounded question against the current index."""
    print(f"Querying active LLM provider (mock={settings.mock_mode})...")
    result = ResearchAgent().ask(question, top_k=top_k)
    
    print(Panel(result.answer, title=f"Answer | confidence={result.confidence.upper()}"))
    
    if result.warnings:
        print("[yellow]Warnings:[/yellow]")
        for w in result.warnings:
            print(f"- [yellow]{w}[/yellow]")
            
    print("\n[bold green]Retrieved Evidence:[/bold green]")
    for ev in result.citations:
        print(f"[bold]{ev.source} p.{ev.page}[/bold] score={ev.score:.3f}")
        print(f"[dim]{ev.text[:220]}...[/dim]\n")


@app.command("list-docs")
def list_docs():
    """List all ingested documents in the local SQLite database."""
    docs = database.get_all_documents()
    if not docs:
        print("[yellow]No documents found in library. Use 'rag-agent index' to add files.[/yellow]")
        return
        
    table = Table(title="Document Library Catalog")
    table.add_column("Doc ID", style="cyan")
    table.add_column("File Name", style="magenta")
    table.add_column("Title", style="green")
    table.add_column("Year", style="yellow")
    table.add_column("Pages", style="blue")
    table.add_column("Chunks", style="blue")
    
    for d in docs:
        table.add_row(
            d["id"], 
            d["file_name"], 
            d["title"] or "N/A", 
            d["year"] or "N/A", 
            str(d["page_count"]), 
            str(d["chunk_count"])
        )
    print(table)


@app.command("compare")
def compare_docs(doc_ids: list[str]):
    """Compare multiple documents side-by-side."""
    print(f"Comparing {len(doc_ids)} documents...")
    result = ResearchAgent().compare_methods(doc_ids=doc_ids)
    print(Panel(result.answer, title="Comparative Matrix"))


@app.command("list-notes")
def list_notes():
    """List all saved research notes."""
    notes = database.get_notes()
    if not notes:
        print("[yellow]No notes found in database.[/yellow]")
        return
        
    for n in notes:
        print(Panel(n["content"], title=f"Note: {n['title']} | Type: {n['note_type'].upper()}"))


@app.command("run-eval")
def run_eval():
    """Execute RAG diagnostic metrics from evals/eval_questions.json."""
    import json
    EVAL_FILE = Path("app/evals/eval_questions.json")
    if not EVAL_FILE.exists():
        print("[red]Evaluation questions file not found.[/red]")
        return
        
    eval_dataset = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(eval_dataset)} evaluation questions.")
    
    agent = ResearchAgent()
    
    table = Table(title="Evaluation Suite Results")
    table.add_column("Question", style="cyan")
    table.add_column("Term Coverage", style="magenta")
    table.add_column("Grounding Score", style="green")
    table.add_column("Status", style="yellow")
    
    for item in eval_dataset:
        res = agent.ask(item["question"])
        
        # calculate term hits
        answer_lower = res.answer.lower()
        hits = sum(1 for term in item["expected_terms"] if term.lower() in answer_lower)
        term_cov = hits / len(item["expected_terms"])
        
        # calculate citations grounding
        from app.core.verifier import verify_citations
        verify_res = verify_citations(res.answer, res.citations)
        g_score = verify_res["grounding_score"]
        
        status = "[green]PASS[/green]" if term_cov >= 0.5 and g_score >= 0.7 else "[red]FAIL[/red]"
        table.add_row(
            item["question"][:50] + "...", 
            f"{term_cov:.0%}", 
            f"{g_score:.0%}", 
            status
        )
    print(table)


if __name__ == "__main__":
    app()
