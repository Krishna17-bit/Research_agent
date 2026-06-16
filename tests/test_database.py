from pathlib import Path
from datetime import datetime

from app.core import database


def test_database_initialization():
    # Verify DB tables exist and can connect
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    
    assert "documents" in tables
    assert "workspaces" in tables
    assert "workspace_documents" in tables
    assert "notes" in tables
    assert "run_history" in tables
    assert "eval_runs" in tables
    conn.close()


def test_document_and_workspace_ops():
    # Insert doc
    doc_id = "test_doc_123"
    database.add_document(
        doc_id=doc_id,
        file_name="test_paper.pdf",
        file_path="/path/test_paper.pdf",
        title="Test Scientific Paper",
        authors="Dr. Tester",
        year="2026",
        doc_type="paper"
    )
    
    # Retrieve doc
    doc = database.get_document(doc_id)
    assert doc is not None
    assert doc["title"] == "Test Scientific Paper"
    assert doc["authors"] == "Dr. Tester"

    # Workspace operations
    ws_id = database.create_workspace("Custom Test WS", "Workspace description")
    database.add_document_to_workspace(ws_id, doc_id)
    
    ws_docs = database.get_workspace_documents(ws_id)
    assert len(ws_docs) == 1
    assert ws_docs[0]["id"] == doc_id
    
    # Remove from workspace
    database.remove_document_from_workspace(ws_id, doc_id)
    ws_docs = database.get_workspace_documents(ws_id)
    assert len(ws_docs) == 0
    
    # Update metadata
    database.update_document_metadata(doc_id, title="Updated Title")
    doc = database.get_document(doc_id)
    assert doc["title"] == "Updated Title"
    
    # Delete doc
    database.delete_document(doc_id)
    doc = database.get_document(doc_id)
    assert doc is None
    
    database.delete_workspace(ws_id)
