from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import uuid
from datetime import datetime

from app.core.config import settings

DB_FILE = settings.resolve_path(Path("app/storage/research_agent.db"))
DB_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                year TEXT,
                doc_type TEXT,
                tags TEXT,
                page_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                upload_date TEXT,
                notes TEXT,
                bibtex TEXT,
                doi TEXT
            )
        """)

        # Alter table to add columns if updating existing DB
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN bibtex TEXT")
        except sqlite3.OperationalError:
            pass # column already exists
            
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN doi TEXT")
        except sqlite3.OperationalError:
            pass # column already exists

        # Workspaces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT
            )
        """)

        # Workspace Documents junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workspace_documents (
                workspace_id TEXT,
                document_id TEXT,
                PRIMARY KEY (workspace_id, document_id),
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                workspace_id TEXT,
                page_number INTEGER,
                note_type TEXT,
                title TEXT,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
        """)

        # Run history table for RAG queries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                confidence TEXT,
                latency REAL,
                tokens INTEGER,
                cost REAL,
                provider TEXT,
                model TEXT,
                timestamp TEXT,
                feedback TEXT,
                citation_quality TEXT,
                citations_json TEXT
            )
        """)

        # Evaluation runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                dataset TEXT,
                provider TEXT,
                model TEXT,
                score REAL,
                pass_count INTEGER,
                fail_count INTEGER,
                results_json TEXT
            )
        """)

        # Insert default workspace if none exists
        cursor.execute("SELECT COUNT(*) FROM workspaces")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO workspaces (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                ("default", "Default Workspace", "Your main personal research workspace.", datetime.now().isoformat())
            )

        conn.commit()


# Run initialization on import
init_db()


# --- CRUD Helpers for Documents ---

def add_document(doc_id: str, file_name: str, file_path: str, title: str | None = None,
                 authors: str | None = None, year: str | None = None, doc_type: str = "paper",
                 tags: str | None = None, page_count: int = 0, chunk_count: int = 0,
                 status: str = "pending", notes: str | None = None, bibtex: str | None = None,
                 doi: str | None = None) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents 
            (id, file_name, file_path, title, authors, year, doc_type, tags, page_count, chunk_count, status, upload_date, notes, bibtex, doi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, file_name, file_path, title, authors, year, doc_type, tags, page_count, chunk_count, status, datetime.now().isoformat(), notes, bibtex, doi)
        )
        conn.commit()


def get_document(doc_id: str) -> sqlite3.Row | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        return cursor.fetchone()


def get_all_documents() -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY upload_date DESC")
        return cursor.fetchall()


def delete_document(doc_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.execute("DELETE FROM workspace_documents WHERE document_id = ?", (doc_id,))
        conn.commit()


def update_document_metadata(doc_id: str, title: str | None = None, authors: str | None = None,
                             year: str | None = None, doc_type: str | None = None,
                             tags: str | None = None, notes: str | None = None,
                             status: str | None = None, chunk_count: int | None = None,
                             page_count: int | None = None, bibtex: str | None = None,
                             doi: str | None = None) -> None:
    with get_db_connection() as conn:
        fields = []
        params = []
        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if authors is not None:
            fields.append("authors = ?")
            params.append(authors)
        if year is not None:
            fields.append("year = ?")
            params.append(year)
        if doc_type is not None:
            fields.append("doc_type = ?")
            params.append(doc_type)
        if tags is not None:
            fields.append("tags = ?")
            params.append(tags)
        if notes is not None:
            fields.append("notes = ?")
            params.append(notes)
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if chunk_count is not None:
            fields.append("chunk_count = ?")
            params.append(chunk_count)
        if page_count is not None:
            fields.append("page_count = ?")
            params.append(page_count)
        if bibtex is not None:
            fields.append("bibtex = ?")
            params.append(bibtex)
        if doi is not None:
            fields.append("doi = ?")
            params.append(doi)

        if fields:
            params.append(doc_id)
            query = f"UPDATE documents SET {', '.join(fields)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()


# --- CRUD Helpers for Workspaces ---

def create_workspace(name: str, description: str | None = None) -> str:
    ws_id = str(uuid.uuid4())[:8]
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO workspaces (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (ws_id, name, description, datetime.now().isoformat())
        )
        conn.commit()
    return ws_id


def get_workspaces() -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workspaces ORDER BY created_at DESC")
        return cursor.fetchall()


def delete_workspace(ws_id: str) -> None:
    if ws_id == "default":
        return  # prevent deleting default
    with get_db_connection() as conn:
        conn.execute("DELETE FROM workspaces WHERE id = ?", (ws_id,))
        conn.execute("DELETE FROM workspace_documents WHERE workspace_id = ?", (ws_id,))
        conn.commit()


def add_document_to_workspace(ws_id: str, doc_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO workspace_documents (workspace_id, document_id) VALUES (?, ?)",
            (ws_id, doc_id)
        )
        conn.commit()


def remove_document_from_workspace(ws_id: str, doc_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM workspace_documents WHERE workspace_id = ? AND document_id = ?",
            (ws_id, doc_id)
        )
        conn.commit()


def get_workspace_documents(ws_id: str) -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.* FROM documents d
            JOIN workspace_documents wd ON d.id = wd.document_id
            WHERE wd.workspace_id = ?
            ORDER BY d.upload_date DESC
            """,
            (ws_id,)
        )
        return cursor.fetchall()


# --- CRUD Helpers for Notes ---

def add_note(document_id: str | None = None, workspace_id: str | None = None,
             page_number: int | None = None, note_type: str = "user note",
             title: str | None = None, content: str = "", tags: str | None = None) -> str:
    note_id = str(uuid.uuid4())[:10]
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO notes (id, document_id, workspace_id, page_number, note_type, title, content, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (note_id, document_id, workspace_id, page_number, note_type, title, content, tags, datetime.now().isoformat())
        )
        conn.commit()
    return note_id


def get_notes(document_id: str | None = None, workspace_id: str | None = None) -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if document_id:
            cursor.execute("SELECT * FROM notes WHERE document_id = ? ORDER BY created_at DESC", (document_id,))
        elif workspace_id:
            cursor.execute("SELECT * FROM notes WHERE workspace_id = ? ORDER BY created_at DESC", (workspace_id,))
        else:
            cursor.execute("SELECT * FROM notes ORDER BY created_at DESC")
        return cursor.fetchall()


def delete_note(note_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()


# --- CRUD Helpers for History ---

def add_run(question: str, answer: str, confidence: str, latency: float, tokens: int,
            cost: float, provider: str, model: str, feedback: str | None = None,
            citation_quality: str | None = None, citations: list | None = None) -> str:
    run_id = str(uuid.uuid4())[:8]
    citations_str = json.dumps(citations) if citations else "[]"
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO run_history 
            (id, question, answer, confidence, latency, tokens, cost, provider, model, timestamp, feedback, citation_quality, citations_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, question, answer, confidence, latency, tokens, cost, provider, model, datetime.now().isoformat(), feedback, citation_quality, citations_str)
        )
        conn.commit()
    return run_id


def get_runs() -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM run_history ORDER BY timestamp DESC")
        return cursor.fetchall()


def update_run_feedback(run_id: str, feedback: str) -> None:
    with get_db_connection() as conn:
        conn.execute("UPDATE run_history SET feedback = ? WHERE id = ?", (feedback, run_id))
        conn.commit()


# --- CRUD Helpers for Evaluation ---

def add_eval_run(timestamp: str, dataset: str, provider: str, model: str, score: float,
                 pass_count: int, fail_count: int, results: list) -> str:
    eval_id = str(uuid.uuid4())[:8]
    results_str = json.dumps(results)
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO eval_runs (id, timestamp, dataset, provider, model, score, pass_count, fail_count, results_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eval_id, timestamp, dataset, provider, model, score, pass_count, fail_count, results_str)
        )
        conn.commit()
    return eval_id


def get_eval_runs() -> list[sqlite3.Row]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM eval_runs ORDER BY timestamp DESC")
        return cursor.fetchall()
