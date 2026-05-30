from __future__ import annotations

from pathlib import Path
import typer
from rich import print
from rich.panel import Panel

from app.core.agent import ResearchAgent
from app.core.retriever import HybridRetriever

app = typer.Typer(help="Scientific PDF RAG + Research Agent CLI")


@app.command()
def index(paths: list[Path]):
    """Index one or more PDF/TXT/MD documents."""
    count = HybridRetriever().build_from_paths(paths)
    print(f"[green]Indexed {count} chunks.[/green]")


@app.command()
def ask(question: str, top_k: int = 7):
    """Ask a question against the current index."""
    result = ResearchAgent().ask(question, top_k=top_k)
    print(Panel(result.answer, title=f"Answer | confidence={result.confidence}"))
    for ev in result.citations:
        print(f"[bold]{ev.source} p.{ev.page}[/bold] score={ev.score:.3f}\n{ev.text[:400]}...\n")


if __name__ == "__main__":
    app()
