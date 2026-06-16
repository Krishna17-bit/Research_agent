# Research PDF RAG Agent — Testing & Diagnostics Manual

This document details the testing architecture, validation suites, and diagnostic benchmarks available in the Research PDF RAG Agent.

---

## 🧪 Running the Unit & Integration Tests

The project includes unit tests covering:
1. **SQLite Database Operations** (`tests/test_database.py`): Document inserts, updates, workspace junction links, notes CRUD, and cascade deletes.
2. **Text Chunking** (`tests/test_chunking.py`): Sentence alignment, character limits, overlap limits.
3. **Retrieval Tokens** (`tests/test_retriever_tokenize.py`): Tokenizer regex parsing scientific words and lowercase rules.
4. **Citation Grounding** (`tests/test_verifier.py`): Regex matches for brackets, cleaning source file strings, calculating word intersection counts, and outputting warning lists.

To run the complete test suite locally:
```bash
pytest
```

---

## 🔬 Running RAG Evaluation Lab (Benchmarks)

The **Evaluation Lab** provides a framework to monitor quality over iterations. The benchmark questions are defined in:
```text
app/evals/eval_questions.json
```
Each entry contains a test question and a list of expected scientific terms.

### Running Evaluations via CLI
To calculate term coverage, retrieval scores, and grounding accuracy across the active LLM provider configuration:
```bash
python -m scripts.run_eval
# Or using the agent CLI:
python app/cli.py run-eval
```

### Running Evaluations via UI
1. Navigate to the **RAG Evaluation Lab** tab in the sidebar.
2. Click **Execute Evaluation Runs**.
3. View the generated charts, pass/fail results, and comparison logs against historic runs.
4. Past runs are saved in SQLite and can be retrieved to track how changing models (e.g. Gemini 1.5 Flash vs GPT-4o-mini) affects hallucination rates and grounding metrics.
